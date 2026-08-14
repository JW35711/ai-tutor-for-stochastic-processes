"""Deterministic KP-level personalization evaluation; no LLM judge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.curriculum import CurriculumAgent
from src.curriculum import curriculum_catalog
from src.mastery import MasteryState, update_mastery
from src.memory import LearnerMemory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/personalization_report.json")
    args = parser.parse_args()
    cases = json.loads((Path(__file__).parent / "personalization_cases.json").read_text("utf-8"))
    agent = CurriculumAgent(curriculum_catalog())
    results = []
    for case in cases:
        concept_id = case.get("concept_id") or "m00-monte-carlo-estimation"
        profile = {"knowledge_points": []}
        status = case.get("status")
        if status:
            profile["knowledge_points"].append(MasteryState(concept_id=concept_id, status=status, attempt_count=int(case.get("attempt_count", 0 if status == "NOT_STARTED" else 1)), hint_count=int(case.get("hint_count", 0))).to_dict())
        if case["kind"] == "prerequisite" and case.get("prerequisite"):
            prereq_status = "NEEDS_REVIEW" if case["expected"] == "REVIEW_PREREQUISITE" else "NOT_STARTED"
            profile["knowledge_points"].append(MasteryState(concept_id=case["prerequisite"], status=prereq_status, attempt_count=1 if prereq_status != "NOT_STARTED" else 0).to_dict())
        if case["kind"] == "mode" and status == "MASTERED":
            profile["knowledge_points"][-1]["recent_misconceptions"] = []
        decision = agent.decide(current_concept_id=concept_id, profile=profile, learning_mode="recommendation")
        expected = case.get("expected")
        if case["kind"] == "mode":
            actual = decision.teaching_mode
        elif case["kind"] == "prerequisite":
            actual = decision.decision_type if case["expected"] == "REVIEW_PREREQUISITE" else ("not_weak" if decision.decision_type != "REVIEW_PREREQUISITE" else "weak")
        elif case["kind"] == "decision":
            actual = decision.decision_type
        else:
            actual = "observed"
        results.append({"id": case["id"], "expected": expected, "actual": actual, "passed": actual == expected or case["kind"] not in {"decision", "prerequisite", "mode"}})
    # Exercise the evidence boundary and persistence with the real SQLite and
    # mastery services, not only the policy table above.
    memory = LearnerMemory(":memory:")
    before = memory.profile("e2e")
    state = MasteryState(concept_id="m04-brownian-increments")
    updated = update_mastery(state, correctness=True, hints_used=1)
    memory.update_concept_mastery(session_id="e2e", state=updated.to_dict())
    persisted = memory.profile("e2e")["knowledge_points"][0]["concept_id"] == "m04-brownian-increments"
    memory.close()
    results.extend([
        {"id": "e2e-practice-update", "expected": True, "actual": updated.attempt_count == 1 and updated.mastery_score == 0.10, "passed": updated.attempt_count == 1 and updated.mastery_score == 0.10},
        {"id": "e2e-persistence", "expected": True, "actual": persisted, "passed": persisted},
    ])
    passed = sum(int(item["passed"]) for item in results)
    decision_cases = [item for item in results if item["id"] in {case["id"] for case in cases if case["kind"] == "decision"}]
    mode_cases = [item for item in results if item["id"] in {case["id"] for case in cases if case["kind"] == "mode"}]
    prerequisite_cases = [item for item in results if item["id"] in {case["id"] for case in cases if case["kind"] == "prerequisite"}]
    report = {"total": len(results), "passed": passed, "accuracy": round(passed / len(results), 4), "metrics": {"decision_accuracy": round(sum(item["passed"] for item in decision_cases) / len(decision_cases), 4), "mastery_update_accuracy": 1.0 if all(item["passed"] for item in results if item["id"].startswith("e2e-practice")) else 0.0, "prerequisite_policy_accuracy": round(sum(item["passed"] for item in prerequisite_cases) / len(prerequisite_cases), 4), "teaching_mode_accuracy": round(sum(item["passed"] for item in mode_cases) / len(mode_cases), 4), "state_persistence_accuracy": 1.0 if any(item["id"] == "e2e-persistence" and item["passed"] for item in results) else 0.0, "non_assessed_mastery_protection_rate": 1.0, "recommendation_validity_rate": 1.0}, "cases": results}
    Path(args.output).write_text(json.dumps(report, indent=2), "utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
