"""Run the deterministic routing and tool-use evaluation set."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402


DEFAULT_CASES = Path(__file__).with_name("cases.json")
DEFAULT_CONVERSATIONS = Path(__file__).with_name("conversations.json")
DEFAULT_REPORT = ROOT / "artifacts" / "evaluation_report.json"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    module_ok: bool
    tool_ok: bool
    source_ok: bool
    trace_ok: bool
    actual_module: str | None
    actual_tool: str | None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.module_ok and self.tool_ok and self.source_ok and self.trace_ok


def evaluate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        memory = LearnerMemory(Path(directory) / "eval.sqlite3")
        agent = StochasticTutorAgent(memory=memory)
        results: list[CaseResult] = []
        for case in cases:
            try:
                response = agent.answer(case["question"])
                trace_nodes = [item["node"] for item in response["trace"]]
                results.append(
                    CaseResult(
                        case_id=case["id"],
                        module_ok=response["module_id"] == case["expected_module"],
                        tool_ok=response["tool"] == case["expected_tool"],
                        source_ok=bool(response["sources"])
                        and all(
                            source["module_id"] == case["expected_module"]
                            for source in response["sources"]
                        ),
                        trace_ok=trace_nodes
                        == [
                            "classify",
                            "retrieve",
                            "plan",
                            "tool",
                            "diagnose",
                            "memory",
                            "respond",
                        ],
                        actual_module=response["module_id"],
                        actual_tool=response["tool"],
                    )
                )
            except Exception as error:  # report one bad case without hiding the rest
                results.append(
                    CaseResult(
                        case_id=case["id"],
                        module_ok=False,
                        tool_ok=False,
                        source_ok=False,
                        trace_ok=False,
                        actual_module=None,
                        actual_tool=None,
                        error=str(error),
                    )
                )
        memory.close()

    passed = sum(item.passed for item in results)
    total = len(results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "metrics": {
            "module_accuracy": round(sum(item.module_ok for item in results) / total, 4),
            "tool_accuracy": round(sum(item.tool_ok for item in results) / total, 4),
            "source_accuracy": round(sum(item.source_ok for item in results) / total, 4),
            "trace_accuracy": round(sum(item.trace_ok for item in results) / total, 4),
        },
        "failures": [asdict(item) for item in results if not item.passed],
    }


def evaluate_conversations(cases: list[dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        memory = LearnerMemory(Path(directory) / "conversation-eval.sqlite3")
        agent = StochasticTutorAgent(memory=memory)
        failures: list[dict[str, Any]] = []
        for case in cases:
            session_id = None
            response: dict[str, Any] = {}
            try:
                for question in case["turns"]:
                    response = agent.answer(question, session_id=session_id)
                    session_id = response["session_id"]
                parameter_ok = all(
                    response["parameters"].get(key) == value
                    for key, value in case["expected_parameters"].items()
                )
                passed = (
                    response["module_id"] == case["expected_module"]
                    and response["tool"] == case["expected_tool"]
                    and parameter_ok
                    and response["context"]["module_inherited"]
                )
                if not passed:
                    failures.append(
                        {
                            "case_id": case["id"],
                            "actual_module": response.get("module_id"),
                            "actual_tool": response.get("tool"),
                            "actual_parameters": response.get("parameters"),
                            "context": response.get("context"),
                        }
                    )
            except Exception as error:
                failures.append({"case_id": case["id"], "error": str(error)})
        memory.close()
    total = len(cases)
    passed = total - len(failures)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--conversations", type=Path, default=DEFAULT_CONVERSATIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text("utf-8"))
    report = evaluate(cases)
    conversations = json.loads(args.conversations.read_text("utf-8"))
    report["multi_turn"] = evaluate_conversations(conversations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    complete = (
        report["passed"] == report["total"]
        and report["multi_turn"]["passed"] == report["multi_turn"]["total"]
    )
    raise SystemExit(0 if complete else 1)


if __name__ == "__main__":
    main()
