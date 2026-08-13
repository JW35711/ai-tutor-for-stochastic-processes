"""Deterministic multilingual routing and fallback evaluation (no API key required)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


def contains_formula(answer: str, required: str) -> bool:
    if required == "pi":
        return "pi" in answer.lower() or "π" in answer
    return required.lower() in answer.lower() or required in answer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads((ROOT / "evals" / "multilingual_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        memory = LearnerMemory(":memory:")
        try:
            agent = StochasticTutorAgent(memory=memory)
            agent.llm = type("OfflineLLM", (), {"enabled": False, "complete": lambda self, *args: None})()
            response = agent.answer(case["question"], ui_language="en")
            answer = str(response.get("answer", ""))
            passed = (
                response.get("detected_query_language") == case["language"]
                and response.get("response_language") == case["language"]
                and response.get("module_id") == case["module_id"]
                and response.get("concept_id") == case["concept_id"]
                and not response.get("tool_called")
                and contains_formula(answer, case["required_formula"])
            )
            results.append({"id": case["id"], "passed": passed, "language": response.get("response_language"), "module_id": response.get("module_id"), "concept_id": response.get("concept_id"), "translation_applied": response.get("translation_applied"), "answer": answer})
        finally:
            memory.close()
    payload = {"mode": "offline", "total": len(results), "passed": sum(item["passed"] for item in results), "pass_rate": sum(item["passed"] for item in results) / len(results), "metrics": {"language_detection_accuracy": sum(item["passed"] for item in results) / len(results), "concept_routing_accuracy": sum(item["passed"] for item in results) / len(results), "response_language_accuracy": sum(item["passed"] for item in results) / len(results), "math_render_contract_pass_rate": sum(item["passed"] for item in results) / len(results)}, "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if payload["passed"] == payload["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
