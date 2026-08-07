#!/usr/bin/env python3
"""Evaluate transparent misconception handling and teaching-answer structure."""

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


DEFAULT_CASES = ROOT / "evals" / "pedagogy_cases.json"


def evaluate(cases_path: Path = DEFAULT_CASES) -> dict[str, Any]:
    cases: list[dict[str, Any]] = json.loads(cases_path.read_text("utf-8"))
    failures: list[dict[str, Any]] = []
    structured_verified = 0
    verified_count = 0
    with tempfile.TemporaryDirectory() as directory:
        agent = StochasticTutorAgent(
            memory=LearnerMemory(Path(directory) / "pedagogy.sqlite3")
        )
        corpus_sha256 = agent.knowledge.corpus_sha256
        for case in cases:
            response = agent.answer(case["question"], session_id=case["id"])
            actual_codes = [item["code"] for item in response["misconceptions"]]
            corrections_present = all(
                item["correction"] in response["answer"]
                for item in response["misconceptions"]
            )
            module_ok = response["module_id"] == case["expected_module"]
            codes_ok = actual_codes == case["expected_codes"]
            if "error" not in response["result"]:
                verified_count += 1
                required_sections = (
                    "### 先看实验结果",
                    "### 如何理解",
                    "### 给你的思考题",
                    "来源：",
                )
                structured = all(
                    section in response["answer"] for section in required_sections
                )
                structured_verified += int(structured)
            else:
                structured = True
            if not (module_ok and codes_ok and corrections_present and structured):
                failures.append(
                    {
                        "id": case["id"],
                        "module_ok": module_ok,
                        "expected_codes": case["expected_codes"],
                        "actual_codes": actual_codes,
                        "corrections_present": corrections_present,
                        "teaching_structure": structured,
                    }
                )
    total = len(cases)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_sha256": corpus_sha256,
        "total": total,
        "passed": total - len(failures),
        "pass_rate": round((total - len(failures)) / total, 4) if total else 0.0,
        "structured_answer_rate": round(
            structured_verified / verified_count, 4
        ) if verified_count else 0.0,
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
