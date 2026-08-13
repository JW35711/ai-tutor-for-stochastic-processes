"""Deterministic multilingual routing evaluation; no provider key required."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads((ROOT / "evals" / "multilingual_cases.json").read_text(encoding="utf-8"))
    results = []
    memories = {}
    agents = {}
    flow_state = {}
    for case in cases:
        flow_id = case.get("flow_id")
        memory_key = flow_id or case["id"]
        if memory_key not in agents:
            memories[memory_key] = LearnerMemory(":memory:")
            agents[memory_key] = StochasticTutorAgent(memory=memories[memory_key])
            agents[memory_key].llm = type("OfflineLLM", (), {"enabled": False, "complete": lambda self, *args: None})()
        memory = memories[memory_key]
        try:
            agent = agents[memory_key]
            response = agent.answer(case["question"], session_id=flow_id, ui_language=case.get("ui_language", "en"))
            expected_module = case["module_id"]
            related_modules = set(response.get("related_module_ids") or [])
            module_ok = expected_module is None or response.get("module_id") == expected_module or expected_module in related_modules
            language_ok = response.get("response_language") == case["language"] and response.get("detected_query_language") == case["language"]
            intent_ok = response.get("intent") == case["intent"]
            tool_ok = (case["intent"] == "simulation") == bool(response.get("tool_called"))
            parameter_ok = not case.get("parameter_key") or response.get("parameters", {}).get(case["parameter_key"]) == case.get("parameter_value")
            context_ok = not flow_id or (response.get("response_language") == case["language"] and (not case["id"].endswith("show") or bool(response.get("active_experiment_id"))))
            passed = module_ok and language_ok and intent_ok and tool_ok and parameter_ok and context_ok
            results.append({"id": case["id"], "passed": passed, "module_ok": module_ok, "language_ok": language_ok, "intent_ok": intent_ok, "tool_ok": tool_ok, "parameter_ok": parameter_ok, "context_ok": context_ok, "module_id": response.get("module_id"), "response_language": response.get("response_language"), "detected_query_language": response.get("detected_query_language"), "intent": response.get("intent"), "tool_called": response.get("tool_called")})
        finally:
            pass
    for memory in memories.values():
        memory.close()
    total = len(results)
    passed = sum(item["passed"] for item in results)
    payload = {
        "mode": "offline",
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "metrics": {
            "language_detection_accuracy": sum(item["language_ok"] for item in results) / total if total else 0.0,
            "response_language_accuracy": sum(item["language_ok"] for item in results) / total if total else 0.0,
            "concept_routing_accuracy": sum(item["module_ok"] for item in results) / total if total else 0.0,
            "follow_up_context_accuracy": sum(item["context_ok"] and item["parameter_ok"] for item in results) / total if total else 0.0,
        },
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
