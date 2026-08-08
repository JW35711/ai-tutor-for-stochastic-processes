#!/usr/bin/env python3
"""Evaluate bounded-tool, numerical and prompt-injection safety behavior."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402


DEFAULT_CASES = Path(__file__).with_name("safety_cases.json")


def evaluate(cases_path: Path = DEFAULT_CASES) -> dict[str, Any]:
    cases: list[dict[str, Any]] = json.loads(cases_path.read_text("utf-8"))
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as directory:
        memory = LearnerMemory(Path(directory) / "safety.sqlite3")
        agent = StochasticTutorAgent(memory=memory)
        corpus_sha256 = agent.knowledge.corpus_sha256
        try:
            for case in cases:
                failure: dict[str, Any] | None = None
                try:
                    response = agent.answer(case["question"], session_id=case["id"])
                    if "expected_exception" in case:
                        failure = {"reason": "expected exception was not raised"}
                    else:
                        checks = {
                            "module": response["module_id"]
                            == case["expected_module"],
                            "tool": response["tool"] == case["expected_tool"],
                            "verified": response["verified"]
                            is case["expected_verified"],
                            "error": case.get("error_contains", "")
                            in response["result"].get("error", ""),
                            "result": all(
                                response["result"].get(key) == value
                                for key, value in case.get(
                                    "expected_result", {}
                                ).items()
                            ),
                        }
                        if not all(checks.values()):
                            failure = {
                                "reason": "response contract mismatch",
                                "checks": checks,
                                "actual_module": response["module_id"],
                                "actual_tool": response["tool"],
                                "actual_verified": response["verified"],
                                "actual_error": response["result"].get("error"),
                            }
                except ValueError as error:
                    expected = case.get("expected_exception")
                    if not expected or expected not in str(error):
                        failure = {
                            "reason": "unexpected exception",
                            "error": str(error),
                        }
                if failure:
                    failures.append({"id": case["id"], **failure})
        finally:
            memory.close()

    total = len(cases)
    passed = total - len(failures)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_sha256": corpus_sha256,
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.cases)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", "utf-8")
    print(rendered)
    raise SystemExit(0 if not report["failures"] else 1)


if __name__ == "__main__":
    main()
