"""Evaluate experiment selection, follow-ups and renderer execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402
from src.visualization_contracts import project_and_validate  # noqa: E402


CASES = ROOT / "evals" / "experiment_routing_cases.json"


class OfflineLLM:
    enabled = False

    def complete(self, system: str, user: str) -> None:
        return None


def run(cases_path: Path = CASES) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text("utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        memory = LearnerMemory(Path(directory) / "experiment-eval.sqlite3")
        agent = StochasticTutorAgent(memory=memory)
        agent.llm = OfflineLLM()  # type: ignore[assignment]
        results: list[dict[str, Any]] = []
        for case in cases:
            response: dict[str, Any] = {}
            try:
                response = agent.answer(case["question"], session_id=f"experiment-{case['id']}")
                selected = response.get("selected_experiment_id")
                passed = (
                    (response.get("module_id") == case.get("module") or (case.get("expect_unsupported") and response.get("module_id") in {None, "general"}))
                    and (selected == case.get("experiment") if case.get("experiment") else True)
                    and (response.get("tool") == case.get("tool") if case.get("tool") else True)
                    and (not case.get("expect_unsupported") or response.get("intent") == "unsupported")
                    and (not case.get("expect_recommendation") or bool(response.get("experiment_recommendations")))
                )
                results.append({"id": case["id"], "passed": passed, "actual": {"module": response.get("module_id"), "experiment": selected, "tool": response.get("tool"), "intent": response.get("intent"), "tool_called": response.get("tool_called")}})
            except Exception as exc:
                results.append({"id": case["id"], "passed": False, "actual": {"error": f"{type(exc).__name__}: {exc}"}})

        follow_up_results: list[bool] = []
        session = "experiment-follow-up"
        first = agent.answer("Why does lambda affect waiting time?", session_id=session)
        show = agent.answer("Show me.", session_id=session)
        update = agent.answer("Set lambda to 4.", session_id=session)
        changed = agent.answer("What changed?", session_id=session)
        follow_up_results.extend([
            first.get("tool_called") is False and bool(first.get("experiment_recommendations")),
            show.get("selected_experiment_id") == "module01-exp-08" and show.get("tool_called") is True,
            update.get("selected_experiment_id") == "module01-exp-08" and update.get("parameters", {}).get("rate") == 4.0,
            changed.get("tool_called") is False and "latest module01-exp-08 run" in changed.get("answer", ""),
        ])
        special = agent.answer("Show me PageRank.", session_id="experiment-pagerank")
        thinning = agent.answer("Show the thinning process.", session_id="experiment-thinning")
        renderer_results: list[bool] = []
        for response in (show, update, special, thinning):
            result = response.get("result") or {}
            target_id = response.get("selected_visualization_id")
            target = next((item for item in agent.experiments.payload.get("visualizations", []) if item.get("visualization_id") == target_id), None)
            if target is None:
                renderer_results.append(False)
                continue
            _, errors = project_and_validate(target, result)
            renderer_results.append(not errors and response.get("verified") is True)
        memory.close()

    passed = sum(bool(item["passed"]) for item in results)
    follow_up_passed = sum(follow_up_results)
    explicit = [item for item in results if item["id"].startswith("module")]
    return {
        "corpus_sha256": agent.knowledge.corpus_sha256,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "total": len(results) + len(follow_up_results),
        "passed": passed + follow_up_passed,
        "failures": [item for item in results if not item["passed"]],
        "experiment_selection_accuracy": round(sum(item["passed"] for item in explicit) / len(explicit), 4),
        "parameter_extraction_accuracy": round(sum([update.get("parameters", {}).get("rate") == 4.0]) / 1, 4),
        "follow_up_context_accuracy": round(sum(follow_up_results) / len(follow_up_results), 4),
        "execution_success_rate": round(sum(bool(item["actual"].get("tool_called")) for item in results if item["id"].startswith("module")) / len(explicit), 4),
        "renderer_success_rate": round(sum(renderer_results) / len(renderer_results), 4),
        "follow_up_cases": {"passed": follow_up_passed, "total": len(follow_up_results)},
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "experiment_routing_report.json")
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "experiment_selection_accuracy", "parameter_extraction_accuracy", "follow_up_context_accuracy", "execution_success_rate", "renderer_success_rate")}, indent=2))
    return 0 if report["passed"] == report["total"] and report["experiment_selection_accuracy"] == 1.0 and report["parameter_extraction_accuracy"] == 1.0 and report["follow_up_context_accuracy"] == 1.0 and report["execution_success_rate"] == 1.0 and report["renderer_success_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
