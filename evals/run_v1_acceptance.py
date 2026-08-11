"""Run the reusable v1 tutor acceptance set with a mock or a real provider.

CI uses the default offline mock.  Pass ``--real`` only when the local, ignored
``.env`` contains an OpenAI-compatible provider configuration.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Allow both ``python evals/run_v1_acceptance.py`` and module-style runners.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


CASES = ROOT / "evals" / "v1_acceptance.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "v1_acceptance_report.json"


class OfflineLLM:
    enabled = False

    def complete(self, _system: str, _user: str) -> str | None:
        return None


def _quality_issues(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    answer = str(response.get("answer", ""))
    lowered = answer.lower()
    issues: list[str] = []
    if re.search(r"[\u4e00-\u9fff]", answer):
        issues.append("student-facing answer contains Chinese text")
    if len(answer.split()) > 180:
        issues.append("answer exceeds 180 words")
    if any(marker in lowered for marker in ("lectnotes_technmath.pdf", "retrieved evidence", "embedding", "chunk")):
        issues.append("answer exposes retrieval internals or raw PDF locator")
    if answer.count("$") % 2:
        issues.append("unbalanced LaTeX delimiters")
    if any(marker in lowered for marker in ("this module studies", "this module explores", "the module covers")):
        issues.append("generic module-overview filler")
    if case["expected_intent"] == "simulation" and not response.get("tool_called"):
        issues.append("simulation request did not call a tool")
    if case["expected_sub_intent"] == "hint" and "pi p" in lowered:
        issues.append("hint appears to reveal the stationary-distribution solution")
    return issues


def run(*, real: bool = False) -> dict[str, Any]:
    cases = json.loads(CASES.read_text("utf-8"))
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    if not real:
        agent.llm = OfflineLLM()  # type: ignore[assignment]
    elif not agent.llm.enabled:
        memory.close()
        raise RuntimeError("real provider requested but LLM_API_KEY and LLM_MODEL are not configured")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        for case in cases:
            response = agent.answer(case["question"])
            record = {
                "id": case["id"],
                "question": case["question"],
                "intent": response.get("intent"),
                "sub_intent": response.get("concept_sub_intent"),
                "module_id": response.get("module_id"),
                "concept_id": response.get("concept_id"),
                "related_module_ids": response.get("related_module_ids", []),
                "related_concept_ids": response.get("related_concept_ids", []),
                "llm_applied": response.get("llm_applied", False),
                "tool_called": response.get("tool_called", False),
                "tool": response.get("tool"),
                "latency": response.get("observability", {}).get("latency_ms", {}),
                "answer": response.get("answer", ""),
                "sources": [source.get("source") for source in response.get("sources", [])],
            }
            mismatches: list[str] = []
            for field, expected_key in (
                ("intent", "expected_intent"),
                ("sub_intent", "expected_sub_intent"),
                ("module_id", "expected_module"),
                ("tool_called", "tool_called"),
            ):
                if field == "module_id" and case.get("expected_related_modules"):
                    continue
                if record[field] != case.get(expected_key):
                    mismatches.append(f"{field}: expected {case.get(expected_key)!r}, got {record[field]!r}")
            if case.get("expected_tool") and record["tool"] != case["expected_tool"]:
                mismatches.append(f"tool: expected {case['expected_tool']!r}, got {record['tool']!r}")
            if case.get("expected_related_modules") and not set(case["expected_related_modules"]).issubset(record["related_module_ids"]):
                mismatches.append("related modules do not cover the expected comparison")
            issues = mismatches + _quality_issues(case, response)
            record["passed"] = not issues
            record["issues"] = issues
            results.append(record)
            if issues:
                failures.append(record)
    finally:
        memory.close()
    return {
        "mode": "real" if real else "mock",
        "total": len(results),
        "passed": len(results) - len(failures),
        "pass_rate": round((len(results) - len(failures)) / len(results), 4) if results else 0.0,
        "failures": failures,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true", help="use the provider configured in local .env")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(real=args.real)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("mode", "total", "passed", "pass_rate", "failures")}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not report["failures"] else 1)


if __name__ == "__main__":
    main()
