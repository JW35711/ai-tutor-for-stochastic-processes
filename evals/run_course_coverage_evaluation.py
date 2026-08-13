#!/usr/bin/env python3
"""Evaluate structured course coverage with separate oracle and real routing.

The 120 reviewed cases remain the structured regression set.  ``oracle``
retrieval receives the reviewed module/concept to measure evidence quality;
``real`` starts from the student question and uses the normal Tutor routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.credibility_metrics import (  # noqa: E402
    SUPPORTED_STATUS,
    answerability_metrics,
    classify_failure,
    failure_counts,
    first_gold_rank,
    gold_match,
    ir_metrics,
)
from src.agent import StochasticTutorAgent  # noqa: E402
from src.knowledge import KnowledgeBase  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402

CASES = ROOT / "evals" / "course_coverage_cases.json"


class OfflineLLM:
    enabled = False

    def complete(self, _system: str, _user: str) -> str | None:
        return None


def _contains_gold(result: dict[str, object], case: dict[str, object]) -> bool:
    """Backward-compatible name used by older local evaluation scripts."""

    return gold_match(result, case)


def _sources(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in response.get("sources", []) if isinstance(item, dict)]


def _real_candidate_pool(
    knowledge: KnowledgeBase, question: str, response: dict[str, Any]
) -> list[dict[str, Any]]:
    modules = list(dict.fromkeys(
        ([str(response.get("module_id"))] if response.get("module_id") else [])
        + [str(item) for item in response.get("related_module_ids", []) if item]
    ))
    concepts = list(dict.fromkeys(
        ([str(response.get("concept_id"))] if response.get("concept_id") else [])
        + [str(item) for item in response.get("related_concept_ids", []) if item]
    ))
    if len(modules) <= 1:
        return knowledge.retrieve(
            question,
            module_id=modules[0] if modules else None,
            concept_id=concepts[0] if len(concepts) == 1 else None,
            limit=10,
        )
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for module_id in modules:
        for item in knowledge.retrieve(question, module_id=module_id, limit=10):
            source = str(item.get("source") or "")
            if source not in seen:
                seen.add(source)
                merged.append(item)
    return merged


def _routing_ok(case: dict[str, Any], response: dict[str, Any]) -> bool:
    expected_module = case.get("module_id")
    expected_concept = case.get("concept_id")
    actual_modules = {
        item for item in [response.get("module_id"), *response.get("related_module_ids", [])] if item
    }
    actual_concepts = {
        item for item in [response.get("concept_id"), *response.get("related_concept_ids", [])] if item
    }
    if expected_module is None and expected_concept is None:
        return response.get("intent") == "unsupported" or response.get("answerability_status") == "OUT_OF_SCOPE"
    expected_modules = {item for item in [expected_module, *case.get("related_module_ids", [])] if item}
    expected_concepts = {item for item in [expected_concept, *case.get("related_concept_ids", [])] if item}
    module_ok = not expected_modules or bool(expected_modules & actual_modules)
    concept_ok = not expected_concepts or bool(expected_concepts & actual_concepts)
    return module_ok and concept_ok


def _corpus_has_gold(knowledge: KnowledgeBase, case: dict[str, Any]) -> bool:
    if not case.get("gold_source_locators") and not case.get("gold_evidence_phrases"):
        return True
    return any(gold_match(dict(entry), case) for entry in knowledge.entries)


def _one_case(
    knowledge: KnowledgeBase,
    agent: StochasticTutorAgent,
    case: dict[str, Any],
) -> dict[str, Any]:
    question = str(case["question"])
    expected_status = str(case.get("expected_status", SUPPORTED_STATUS))
    oracle_results, _ = knowledge.retrieve_with_context(
        question,
        module_id=case.get("module_id"),
        concept_id=case.get("concept_id"),
        limit=3,
    ) if case.get("module_id") or case.get("concept_id") else ([], {})
    oracle_pool = knowledge.retrieve(
        question,
        module_id=case.get("module_id"),
        concept_id=case.get("concept_id"),
        limit=10,
    ) if case.get("module_id") or case.get("concept_id") else []

    response = agent.answer(question)
    real_results = _sources(response)
    real_pool = _real_candidate_pool(knowledge, question, response)
    oracle_rank = first_gold_rank(oracle_results, case)
    real_rank = first_gold_rank(real_results, case)
    oracle_candidate_rank = first_gold_rank(oracle_pool, case)
    real_candidate_rank = first_gold_rank(real_pool, case)
    real_full_pool = _real_candidate_pool(knowledge, question, response)
    real_full_rank = first_gold_rank(real_full_pool, case)
    actual_status = str(response.get("answerability_status") or "NONE")
    corpus_has_gold = _corpus_has_gold(knowledge, case)
    answer_present = bool(str(response.get("answer") or "").strip())
    required_claims = [str(item) for item in case.get("required_claims", []) if str(item).strip()]
    answer_text = str(response.get("answer") or "").casefold()
    # The reviewed 120-case file stores claims as corpus-grounding metadata,
    # not exact answer strings.  Only newly authored cases that explicitly opt
    # into ``check_required_claims`` use literal claim checks; otherwise
    # generation quality is assessed by answer presence and answerability.
    claims_present = (
        all(claim.casefold() in answer_text for claim in required_claims)
        if case.get("check_required_claims") and required_claims
        else True
    )

    oracle_stage = classify_failure(
        corpus_has_gold=corpus_has_gold,
        routing_ok=True,
        candidate_rank=oracle_candidate_rank,
        final_rank=oracle_rank,
        expected_status=expected_status,
        actual_status=actual_status,
        answer_present=answer_present,
        required_claims_present=claims_present,
    ) if case.get("module_id") or case.get("concept_id") else (
        "PASS" if expected_status == actual_status else "GENERATION_FAILURE"
    )
    real_stage = classify_failure(
        corpus_has_gold=corpus_has_gold,
        routing_ok=_routing_ok(case, response),
        candidate_rank=real_candidate_rank,
        final_rank=real_rank,
        expected_status=expected_status,
        actual_status=actual_status,
        answer_present=answer_present,
        required_claims_present=claims_present,
    ) if case.get("module_id") or case.get("concept_id") else (
        "PASS" if expected_status == actual_status else "GENERATION_FAILURE"
    )
    return {
        "case_id": case["case_id"],
        "module_id": case.get("module_id"),
        "concept_id": case.get("concept_id"),
        "question": question,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "routed_module_id": response.get("module_id"),
        "routed_concept_id": response.get("concept_id"),
        "related_module_ids": response.get("related_module_ids", []),
        "related_concept_ids": response.get("related_concept_ids", []),
        "oracle_rank": oracle_rank,
        "real_rank": real_rank,
        "real_full_rank": real_full_rank,
        "oracle_candidate_rank": oracle_candidate_rank,
        "real_candidate_rank": real_candidate_rank,
        "oracle_returned_sources": [str(item.get("source")) for item in oracle_results],
        "real_returned_sources": [str(item.get("source")) for item in real_results],
        "failure_stage": real_stage,
        "oracle_failure_stage": oracle_stage,
        "answer_present": answer_present,
        "required_claims_present": claims_present,
        "tool_called": bool(response.get("tool_called")),
        "retrieval_rounds": int(response.get("retrieval_rounds") or 0),
        "answer": str(response.get("answer") or ""),
        "retrieval_query": response.get("retrieval_query"),
        "routing_strategy": response.get("observability", {}).get("routing_strategy"),
        "routing_candidates": response.get("observability", {}).get("routing_candidates", []),
        "routing_confidence": response.get("observability", {}).get("routing_confidence"),
        "selected_routing_reason": response.get("observability", {}).get("selected_routing_reason", ""),
        "stage_timings": response.get("observability", {}).get("stage_timings", {}),
    }


def evaluate(cases_path: Path = CASES) -> dict[str, Any]:
    cases: list[dict[str, Any]] = json.loads(cases_path.read_text("utf-8"))
    knowledge = KnowledgeBase()
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    agent.llm = OfflineLLM()  # type: ignore[assignment]
    rows: list[dict[str, Any]] = []
    try:
        for case in cases:
            rows.append(_one_case(knowledge, agent, case))
    finally:
        memory.close()

    oracle_metrics = ir_metrics(row["oracle_rank"] for row in rows)
    real_metrics = ir_metrics(row["real_rank"] for row in rows)
    total = len(rows)
    real_module_accuracy = sum(
        row["module_id"] is None or row["module_id"] in {row["routed_module_id"], *row["related_module_ids"]}
        for row in rows
    ) / total if total else 0.0
    real_concept_accuracy = sum(
        row["concept_id"] is None or row["concept_id"] in {row["routed_concept_id"], *row["related_concept_ids"]}
        for row in rows
    ) / total if total else 0.0
    answer_rows = [
        {"expected_status": row["expected_status"], "actual_status": row["actual_status"]}
        for row in rows
    ]
    answer_metrics = answerability_metrics(answer_rows)
    oracle_passed = sum(row["oracle_failure_stage"] == "PASS" for row in rows)
    return {
        "suite": "structured_course_coverage",
        "routing_modes": ["ORACLE_ROUTING", "REAL_ROUTING"],
        "corpus_sha256": knowledge.corpus_sha256,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "total": total,
        # ``passed`` remains the reviewed/oracle regression result for CLI and
        # historical tooling.  Real-routing results are reported separately.
        "passed": oracle_passed,
        "kp_coverage_rate": round(len({str(row["concept_id"]) for row in rows if row["concept_id"]}) / 40, 4),
        "hit_at_1": oracle_metrics["hit_at_1"],
        "hit_at_3": oracle_metrics["hit_at_3"],
        "mrr": oracle_metrics["mrr"],
        "oracle_routing": {**oracle_metrics, "passed": oracle_passed},
        "real_routing": {
            "module_accuracy": round(real_module_accuracy, 4),
            "concept_accuracy": round(real_concept_accuracy, 4),
            "hit_at_1": real_metrics["hit_at_1"],
            "hit_at_3": real_metrics["hit_at_3"],
            "mrr": real_metrics["mrr"],
            "passed": sum(row["failure_stage"] == "PASS" for row in rows),
        },
        **answer_metrics,
        "failure_attribution": failure_counts(rows),
        "average_final_evidence_chunks": round(
            sum(len(row["real_returned_sources"]) for row in rows) / total, 3
        ) if total else 0.0,
        "cases": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.cases)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", "utf-8")
    print(json.dumps({
        key: report[key]
        for key in ("total", "passed", "kp_coverage_rate", "hit_at_1", "hit_at_3", "mrr", "real_routing", "failure_attribution")
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
