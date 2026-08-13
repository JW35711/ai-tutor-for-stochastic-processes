from __future__ import annotations

import json
from pathlib import Path

from evals.credibility_metrics import (
    answerability_metrics,
    classify_failure,
    first_gold_rank,
    gold_match,
    ir_metrics,
    rank_distribution,
)


ROOT = Path(__file__).resolve().parents[1]


def test_ir_metrics_use_first_gold_rank_not_nonempty_results() -> None:
    assert ir_metrics([1, 3, None, 2]) == {
        "hit_at_1": 0.25,
        "hit_at_3": 0.75,
        "mrr": 0.4583,
    }


def test_rank_distribution_preserves_late_and_missing_ranks() -> None:
    assert rank_distribution([1, 2, 3, 4, 7, None]) == {
        "rank_1": 1,
        "rank_2": 1,
        "rank_3": 1,
        "rank_4_plus": 2,
        "not_found": 1,
    }


def test_gold_matching_accepts_alternative_locators_but_not_aliases() -> None:
    case = {
        "gold_source_locators": ["notes/module.ipynb#cell-3"],
        "acceptable_source_locators": ["lectures/module.pdf#page-12"],
        "gold_evidence_phrases": ["independent increments"],
    }
    assert gold_match({"source": "lectures/module.pdf#page-12", "content": "anything"}, case)
    assert gold_match({"source": "other.txt", "content": "independent increments"}, case)
    assert not gold_match({"source": "other.txt", "content": "module alias independent"}, {"gold_source_locators": ["notes/module.ipynb"]})


def test_first_gold_rank_supports_multiple_valid_items() -> None:
    case = {"gold_source_locators": ["a#page-1", "b#cell-2"]}
    assert first_gold_rank([{"source": "noise"}, {"source": "b#cell-2"}], case) == 2


def test_answerability_metrics_are_outcome_based() -> None:
    rows = [
        {"expected_status": "SUPPORTED", "actual_status": "SUPPORTED", "answer_present": True},
        {"expected_status": "SUPPORTED", "actual_status": "NONE", "answer_present": True},
        {"expected_status": "NONE", "actual_status": "NONE", "answer_present": True},
        {"expected_status": "OUT_OF_SCOPE", "actual_status": "SUPPORTED", "answer_present": True},
    ]
    metrics = answerability_metrics(rows)
    assert metrics["answer_success_rate"] == 0.5
    assert metrics["false_abstention_rate"] == 0.5
    assert metrics["unsupported_answer_rate"] == 0.5
    assert metrics["evidence_sufficiency_accuracy"] == 0.5


def test_failure_attribution_has_one_deterministic_primary_stage() -> None:
    assert classify_failure(
        corpus_has_gold=True,
        routing_ok=False,
        candidate_rank=1,
        final_rank=1,
        expected_status="SUPPORTED",
        actual_status="SUPPORTED",
        answer_present=True,
    ) == "ROUTING_FAILURE"
    assert classify_failure(
        corpus_has_gold=True,
        routing_ok=True,
        candidate_rank=None,
        final_rank=None,
        expected_status="SUPPORTED",
        actual_status="NONE",
        answer_present=True,
    ) == "RETRIEVAL_RECALL_FAILURE"
    assert classify_failure(
        corpus_has_gold=True,
        routing_ok=True,
        candidate_rank=1,
        final_rank=1,
        expected_status="PARTIAL",
        actual_status="SUPPORTED",
        answer_present=True,
    ) == "ANSWERABILITY_UNSAFE_SUPPORT"


def test_hard_set_is_grounded_across_all_40_knowledge_points() -> None:
    cases = json.loads((ROOT / "evals/course_hard_cases.json").read_text("utf-8"))
    concepts = {case["concept_id"] for case in cases if case.get("concept_id")}
    assert len(cases) >= 100
    assert len(concepts) == 40
    assert all(case.get("expected_status") for case in cases)
    assert all("gold_source_locators" in case for case in cases)


def test_holdout_is_new_and_covers_all_modules() -> None:
    cases = json.loads((ROOT / "evals/course_holdout_cases.json").read_text("utf-8"))
    hard = json.loads((ROOT / "evals/course_hard_cases.json").read_text("utf-8"))
    assert len(cases) >= 30
    assert {case["module_id"] for case in cases} == {f"module{index:02d}" for index in range(11)}
    assert not ({case["question"] for case in cases} & {case["question"] for case in hard})


def test_credibility_report_keeps_oracle_and_real_routing_separate() -> None:
    report_path = ROOT / "artifacts/rag_credibility_report.json"
    if not report_path.exists():
        return
    report = json.loads(report_path.read_text("utf-8"))
    structured = report["structured_coverage_set"]["cases"]
    assert "oracle_routing" in structured and "real_routing" in structured
    assert structured["total"] == 120
    assert report["hard_natural_set"]["cases"]["kp_coverage_rate"] == 1.0
