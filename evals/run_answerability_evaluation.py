"""Evaluate evidence sufficiency separately from retrieval relevance."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Support direct invocation from the repository root and from any shell cwd.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.workflow import AgentState
from evals.credibility_metrics import answerability_metrics


CASES = ROOT / "evals" / "answerability_cases.json"


def _agent() -> tuple[StochasticTutorAgent, LearnerMemory]:
    memory = LearnerMemory(":memory:")
    return StochasticTutorAgent(memory=memory), memory


def run() -> dict[str, object]:
    cases = json.loads(CASES.read_text("utf-8"))
    agent, memory = _agent()
    corpus_sha256 = agent.knowledge.corpus_sha256
    results: list[dict[str, object]] = []
    try:
        for case in cases:
            mode = case.get("mode")
            if mode == "synthetic_conflict":
                state = AgentState(
                    question=case["question"],
                    session_id=f"answerability-{case['id']}",
                )
                state.intent = "concept"
                state.question_requirements = agent._analyze_question_requirements(
                    state.question
                )
                state.sources = [
                    {
                        "source": "synthetic-positive",
                        "content": "The distribution is memoryless.",
                        "claim_key": "memoryless",
                        "claim_polarity": "positive",
                    },
                    {
                        "source": "synthetic-negative",
                        "content": "The distribution is not memoryless.",
                        "claim_key": "memoryless",
                        "claim_polarity": "negative",
                    },
                ]
                state.retrieval_rounds = 1
                agent._update_answerability(state)
                actual = state.answerability_status
                retrieval_rounds = state.retrieval_rounds
                tool_called = False
            elif mode == "synthetic_supplement":
                first = [{
                    "source": "synthetic-poisson-overview",
                    "title": "Poisson process",
                    "content": "A Poisson process counts arrivals with independent increments.",
                    "module_id": "module01",
                    "concept_id": "m01-poisson-process",
                    "retrieval_mode": "hybrid",
                }]
                second = [{
                    "source": "synthetic-exponential-waiting",
                    "title": "Exponential waiting time",
                    "content": "The waiting time to the next arrival is exponential.",
                    "module_id": "module01",
                    "concept_id": "m01-poisson-process",
                    "retrieval_mode": "hybrid",
                }]
                with patch.object(agent.knowledge, "retrieve", side_effect=[first, second]):
                    response = agent.answer(case["question"])
                actual = response["answerability_status"]
                retrieval_rounds = response["retrieval_rounds"]
                tool_called = bool(response["tool_called"])
            else:
                response = agent.answer(case["question"])
                actual = response["answerability_status"]
                retrieval_rounds = response["retrieval_rounds"]
                tool_called = bool(response["tool_called"])
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected": case["expected"],
                    "actual": actual,
                    "retrieval_rounds": retrieval_rounds,
                    "tool_called": tool_called,
                    "passed": actual == case["expected"]
                    and retrieval_rounds >= int(case.get("expected_rounds_min", 0)),
                }
            )
    finally:
        memory.close()

    expected_unsupported = {"PARTIAL", "NONE", "CONFLICT", "OUT_OF_SCOPE"}
    correct = sum(bool(item["passed"]) for item in results)
    predicted_abstentions = [item for item in results if item["actual"] in expected_unsupported]
    expected_abstentions = [item for item in results if item["expected"] in expected_unsupported]
    abstention_precision = (
        sum(item["expected"] in expected_unsupported for item in predicted_abstentions) / len(predicted_abstentions)
        if predicted_abstentions else 1.0
    )
    supplementary_cases = [item for item in results if item["id"] == "supplementary_waiting_evidence"]
    conflict_cases = [item for item in results if item["id"] == "conflicting_memoryless_claims"]
    outcome_metrics = answerability_metrics(
        {
            "expected_status": item["expected"],
            "actual_status": item["actual"],
        }
        for item in results
    )
    return {
        "corpus_sha256": corpus_sha256,
        "total": len(results),
        "passed": correct,
        "answerability_accuracy": round(correct / len(results), 4),
        "answer_success_rate": outcome_metrics["answer_success_rate"],
        "false_abstention_rate": outcome_metrics["false_abstention_rate"],
        "evidence_sufficiency_accuracy": outcome_metrics["evidence_sufficiency_accuracy"],
        "unsupported_answer_rate": round(
            sum(item["actual"] == "SUPPORTED" and item["expected"] in expected_unsupported for item in results)
            / len(expected_abstentions),
            4,
        ) if expected_abstentions else 0.0,
        "abstention_precision": round(abstention_precision, 4),
        "supplementary_retrieval_success_rate": round(
            sum(
                item["actual"] == "SUPPORTED" and item["retrieval_rounds"] > 1
                for item in supplementary_cases
            ) / len(supplementary_cases),
            4,
        ) if supplementary_cases else 1.0,
        "conflict_detection_accuracy": round(
            sum(item["actual"] == "CONFLICT" for item in conflict_cases)
            / len(conflict_cases),
            4,
        ) if conflict_cases else 1.0,
        "cases": results,
    }


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
