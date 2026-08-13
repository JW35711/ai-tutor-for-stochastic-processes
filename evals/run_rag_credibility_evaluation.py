#!/usr/bin/env python3
"""Run the deterministic RAG credibility checkpoint.

The report keeps structured coverage, natural/hard questions, oracle routing,
real routing, answerability and feature A/B observations separate.  It never
requires a provider key and does not alter production retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.credibility_metrics import answerability_metrics, failure_counts, first_gold_rank, ir_metrics, rank_distribution  # noqa: E402
from evals.run_course_coverage_evaluation import OfflineLLM, _corpus_has_gold, _one_case, _real_candidate_pool, _routing_ok, _sources  # noqa: E402
from src.agent import StochasticTutorAgent  # noqa: E402
from src.knowledge import KnowledgeBase  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402

STRUCTURED = ROOT / "evals" / "course_coverage_cases.json"
HARD = ROOT / "evals" / "course_hard_cases.json"
HOLDOUT = ROOT / "evals" / "course_holdout_cases.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "rag_credibility_report.json"


def _load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text("utf-8"))


def _grounded(case: dict[str, Any]) -> bool:
    return bool(case.get("module_id") or case.get("concept_id") or case.get("gold_source_locators"))


def _abstention(row: dict[str, Any]) -> bool:
    return row["actual_status"] in {"PARTIAL", "NONE", "CONFLICT", "OUT_OF_SCOPE"}


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return round(ordered[index], 3)


def _routing_taxonomy(row: dict[str, Any]) -> str:
    question = str(row.get("question") or "").casefold()
    language = str(row.get("language") or "en")
    if language != "en":
        return "MULTILINGUAL"
    if row.get("related_module_ids") or row.get("related_concept_ids") or row.get("question_type") == "comparison":
        return "MULTI_CONCEPT"
    if any(marker in question for marker in ("compare", "difference", " versus ", " vs ", "what changes between")):
        return "COMPARISON"
    if any(marker in question for marker in ("π", "pi p", "λ", "lambda", "n(t)", "b(t)", "q =", "q=")):
        return "NOTATION"
    if row.get("question_type") in {"conditions", "derivation"} or any(marker in question for marker in ("starting", "initial", "boundary", "rate", "parameter")):
        return "CONDITION_OR_PARAMETER"
    if row.get("question_type") == "follow_up" or any(marker in question for marker in ("after changing", "what changed", "again")):
        return "FOLLOW_UP_CONTEXT"
    if row.get("question_type") in {"why", "example", "hint"}:
        return "IMPLICIT_CONCEPT"
    return "PARAPHRASE"


def _failure_stage(row: dict[str, Any], case: dict[str, Any]) -> str:
    """Use explicit names so status matching and pipeline success cannot blur."""

    if row["overall_case_success"] and (not _grounded(case) or row["routing_ok"]):
        return "PASS"
    if not row["routing_ok"]:
        return "ROUTING_FAILURE"
    if row["expected_status"] == "SUPPORTED" and row["actual_status"] in {
        "PARTIAL", "NONE", "CONFLICT", "OUT_OF_SCOPE",
    }:
        return "ANSWERABILITY_FALSE_ABSTENTION"
    if row["expected_status"] != "SUPPORTED" and row["actual_status"] == "SUPPORTED":
        return "ANSWERABILITY_UNSAFE_SUPPORT"
    if _grounded(case) and row["current_rank"] is None:
        return "RETRIEVAL_RECALL_FAILURE"
    return "GENERATION_FAILURE"


def _false_abstention_cause(row: dict[str, Any]) -> str:
    if row["routing_ok"] is False:
        return "routing_wrong"
    if row.get("missing_requirements"):
        return "requirements_inferred_or_missing"
    if row.get("retrieval_rounds", 0) <= 1:
        return "supplementary_retrieval_not_triggered"
    return "other"


def _run_hard(cases: list[dict[str, Any]], knowledge: KnowledgeBase, agent: StochasticTutorAgent) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    current_retrieval_latencies: list[float] = []
    base_retrieval_latencies: list[float] = []
    rerank_retrieval_latencies: list[float] = []
    base_ranks: list[int | None] = []
    rerank_ranks: list[int | None] = []
    current_ranks: list[int | None] = []
    scoped_ranks: list[int | None] = []
    for case in cases:
        question = str(case["question"])
        started = time.perf_counter()
        response = agent.answer(question, session_id=f"credibility-{case['case_id']}")
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        latencies.append(latency_ms)
        final = _sources(response)
        expected_status = str(case.get("expected_status", "SUPPORTED"))
        actual_status = str(response.get("answerability_status") or "NONE")
        retrieval_started = time.perf_counter()
        base = knowledge.retrieve(question, limit=3)
        base_retrieval_latencies.append((time.perf_counter() - retrieval_started) * 1000)
        base_rank = first_gold_rank(base, case)
        base_ranks.append(base_rank)
        routed_module = response.get("module_id")
        routed_concept = response.get("concept_id")
        retrieval_started = time.perf_counter()
        ab = knowledge.retrieve_ab(
            question,
            module_id=str(routed_module) if routed_module else None,
            concept_id=str(routed_concept) if routed_concept else None,
            limit=3,
        )
        rerank_retrieval_latencies.append((time.perf_counter() - retrieval_started) * 1000)
        rerank_rank = first_gold_rank(ab["deterministic_rerank"], case)
        rerank_ranks.append(rerank_rank)
        current_rank = first_gold_rank(final, case)
        current_ranks.append(current_rank)
        retrieval_started = time.perf_counter()
        scoped_results = knowledge.retrieve(
            question,
            module_id=str(routed_module) if routed_module else None,
            concept_id=str(routed_concept) if routed_concept else None,
            limit=3,
        )
        current_retrieval_latencies.append((time.perf_counter() - retrieval_started) * 1000)
        scoped_rank = first_gold_rank(scoped_results, case)
        scoped_ranks.append(scoped_rank)
        expected_modules = {item for item in [case.get("module_id")] if item}
        expected_concepts = {item for item in [case.get("concept_id")] if item}
        routing_ok = _routing_ok(case, response)
        answer_present = bool(str(response.get("answer") or "").strip())
        observability = response.get("observability") if isinstance(response.get("observability"), dict) else {}
        stage_timings = observability.get("stage_timings", {}) if isinstance(observability, dict) else {}
        rows.append({
            "case_id": case["case_id"],
            "question": question,
            "language": case.get("language", "en"),
            "expected_module_id": case.get("module_id"),
            "expected_concept_id": case.get("concept_id"),
            "expected_status": expected_status,
            "actual_status": actual_status,
            "routed_module_id": routed_module,
            "routed_concept_id": routed_concept,
            "related_module_ids": response.get("related_module_ids", []),
            "related_concept_ids": response.get("related_concept_ids", []),
            "routing_ok": routing_ok,
            "overall_case_success": actual_status == expected_status,
            "retrieval_stage_pass": bool(routing_ok and current_rank is not None),
            "final_pipeline_pass": bool(actual_status == expected_status and (not _grounded(case) or routing_ok)),
            "current_rank": current_rank,
            "real_full_rank": first_gold_rank(
                _real_candidate_pool(knowledge, question, response), case
            ),
            "scoped_rank": scoped_rank,
            "base_unscoped_rank": base_rank,
            "reranked_rank": rerank_rank,
            "retrieval_rounds": int(response.get("retrieval_rounds") or 0),
            "latency_ms": latency_ms,
            "tool_called": bool(response.get("tool_called")),
            "sources": [str(item.get("source")) for item in final],
            "answer": str(response.get("answer") or ""),
            "answer_present": answer_present,
            "corpus_has_gold": _corpus_has_gold(knowledge, case),
            "llm_applied": bool(response.get("llm_applied")),
            "missing_requirements": response.get("missing_requirements", []),
            "routing_strategy": observability.get("routing_strategy"),
            "routing_candidates": observability.get("routing_candidates", []),
            "routing_confidence": observability.get("routing_confidence"),
            "selected_routing_reason": observability.get("selected_routing_reason", ""),
            "retrieval_query": response.get("retrieval_query"),
            "stage_timings": stage_timings,
        })
    grounded_rows = [row for row in rows if row["expected_module_id"] or row["expected_concept_id"]]
    answer_metrics = answerability_metrics(
        {"expected_status": row["expected_status"], "actual_status": row["actual_status"]}
        for row in rows
    )
    current_metrics = ir_metrics(row["current_rank"] for row in grounded_rows)
    base_metrics = ir_metrics(row["base_unscoped_rank"] for row in grounded_rows)
    rerank_metrics = ir_metrics(row["reranked_rank"] for row in grounded_rows)
    scoped_metrics = ir_metrics(row["scoped_rank"] for row in grounded_rows)
    expected_supported = [row for row in rows if row["expected_status"] == "SUPPORTED"]
    def _feature_ab_metrics(rank_key: str, feature_latencies: list[float]) -> dict[str, Any]:
        metrics = ir_metrics(row[rank_key] for row in grounded_rows)
        metrics["false_abstention_rate"] = round(
            sum(_abstention(row) for row in expected_supported) / len(expected_supported), 4
        ) if expected_supported else 0.0
        feature_sorted = sorted(feature_latencies)
        metrics["mean_retrieval_latency_ms"] = round(statistics.fmean(feature_latencies), 3) if feature_latencies else 0.0
        metrics["p95_retrieval_latency_ms"] = round(feature_sorted[max(0, int(0.95 * len(feature_sorted)) - 1)], 3) if feature_sorted else 0.0
        return metrics
    sorted_latencies = sorted(latencies)
    supplementary_rows = [row for row in rows if row["retrieval_rounds"] > 1]
    process = {
        "mean_total_latency_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "p95_total_latency_ms": round(sorted_latencies[max(0, int(0.95 * len(sorted_latencies)) - 1)], 3) if sorted_latencies else 0.0,
        "mean_retrieval_latency_ms": round(statistics.fmean(current_retrieval_latencies), 3) if current_retrieval_latencies else 0.0,
        "p95_retrieval_latency_ms": round(sorted(current_retrieval_latencies)[max(0, int(0.95 * len(current_retrieval_latencies)) - 1)], 3) if current_retrieval_latencies else 0.0,
        "average_retrieval_rounds": round(statistics.fmean(row["retrieval_rounds"] for row in rows), 3) if rows else 0.0,
        "max_retrieval_rounds": max((row["retrieval_rounds"] for row in rows), default=0),
        "average_final_evidence_chunks": round(statistics.fmean(len(row["sources"]) for row in rows), 3) if rows else 0.0,
        "initial_retrieval_success_rate": round(sum(row["base_unscoped_rank"] is not None for row in grounded_rows) / len(grounded_rows), 4) if grounded_rows else 0.0,
        "supplementary_retrieval_trigger_rate": round(sum(row["retrieval_rounds"] > 1 for row in rows) / len(rows), 4) if rows else 0.0,
        "supplementary_retrieval_success_rate": round(sum(row["actual_status"] == "SUPPORTED" for row in supplementary_rows) / len(supplementary_rows), 4) if supplementary_rows else None,
        "supplementary_retrieval_observed": bool(supplementary_rows),
    }
    # Stage timings are taken from the same API response as total latency.  A
    # stage is a child interval in the graph trace; it is not an extra KB call.
    timing_values = {
        "routing_ms": [float(row.get("stage_timings", {}).get("routing_ms", 0.0)) for row in rows],
        "retrieval_ms": [float(row.get("stage_timings", {}).get("retrieval_ms", 0.0)) for row in rows],
        "answerability_ms": [float(row.get("stage_timings", {}).get("answerability_ms", 0.0)) for row in rows],
        "generation_or_fallback_ms": [float(row.get("stage_timings", {}).get("generation_or_fallback_ms", 0.0)) for row in rows],
        "total_pipeline_ms": [float(row["latency_ms"]) for row in rows],
    }
    process["latency_ms"] = {
        name: {
            "mean": round(statistics.fmean(values), 3) if values else 0.0,
            "p50": _percentile(values, 0.50) or 0.0,
            "p95": _percentile(values, 0.95) or 0.0,
            "definition": (
                "same-request graph stage duration" if name != "total_pipeline_ms"
                else "wall-clock from agent.answer entry to finalized response"
            ),
        }
        for name, values in timing_values.items()
    }
    routing_failures = [row for row in rows if not row["routing_ok"]]
    false_abstentions = [
        row for row in rows
        if row["expected_status"] == "SUPPORTED" and row["actual_status"] in {"PARTIAL", "NONE", "CONFLICT", "OUT_OF_SCOPE"}
    ]
    taxonomy = {}
    for row in routing_failures:
        category = _routing_taxonomy(row)
        taxonomy.setdefault(category, {"count": 0, "examples": []})
        taxonomy[category]["count"] += 1
        if len(taxonomy[category]["examples"]) < 3:
            taxonomy[category]["examples"].append({"case_id": row["case_id"], "question": row["question"]})
    feature_ab = {
        "current_pipeline_with_routing_and_context": _feature_ab_metrics("current_rank", current_retrieval_latencies),
        "scoped_concept_aliases": _feature_ab_metrics("scoped_rank", current_retrieval_latencies),
        "parent_neighbor_context": {
            "with_context": _feature_ab_metrics("current_rank", current_retrieval_latencies),
            "without_context": scoped_metrics,
            "note": "Production context expansion remains unchanged; this is a bounded observational comparison.",
        },
        "hybrid_sparse_dense": _feature_ab_metrics("scoped_rank", current_retrieval_latencies),
        "raw_unscoped_baseline": _feature_ab_metrics("base_unscoped_rank", base_retrieval_latencies),
        "deterministic_rerank_ab": _feature_ab_metrics("reranked_rank", rerank_retrieval_latencies),
        "supplementary_retrieval": {
            "hit_at_1": None,
            "hit_at_3": None,
            "mrr": None,
            "false_abstention_rate": None,
            "mean_retrieval_latency_ms": None,
            "p95_retrieval_latency_ms": None,
            "status": "not_triggered_by_hard_set; see supplementary_retrieval_control",
        },
        "note": "These are bounded observational A/B runs; no causal claim is made and production retrieval is unchanged.",
    }
    return rows, {
        "total": len(rows),
        "overall_case_success": sum(row["overall_case_success"] for row in rows),
        "retrieval_stage_pass": sum(row["retrieval_stage_pass"] for row in rows),
        "final_pipeline_pass": sum(row["final_pipeline_pass"] for row in rows),
        # Kept as an alias for old report consumers; it is explicitly the
        # answerability status-match count, not the final pipeline count.
        "passed": sum(row["overall_case_success"] for row in rows),
        "kp_coverage_rate": round(len({row["expected_concept_id"] for row in grounded_rows}) / 40, 4),
        "answerability": answer_metrics,
        "real_routing": {
            "module_accuracy": round(sum(row["expected_module_id"] is None or row["expected_module_id"] in {row["routed_module_id"], *row["related_module_ids"]} for row in grounded_rows) / len(grounded_rows), 4) if grounded_rows else 0.0,
            "concept_accuracy": round(sum(row["expected_concept_id"] is None or row["expected_concept_id"] in {row["routed_concept_id"], *row["related_concept_ids"]} for row in grounded_rows) / len(grounded_rows), 4) if grounded_rows else 0.0,
            **current_metrics,
        },
        "retrieval_process": process,
        "first_relevant_rank_distribution": {
            "real_full_pool": rank_distribution(row["real_full_rank"] for row in grounded_rows),
            "current_top3": rank_distribution(row["current_rank"] for row in grounded_rows),
            "denominator": len(grounded_rows),
        },
        "routing_failure_taxonomy": dict(sorted(taxonomy.items(), key=lambda item: (-item[1]["count"], item[0]))),
        "routing_failure_cases": [
            {
                key: row.get(key)
                for key in (
                    "case_id", "question", "language", "expected_module_id", "expected_concept_id",
                    "routed_module_id", "routed_concept_id", "routing_candidates", "retrieval_query",
                    "sources", "actual_status", "routing_strategy", "routing_confidence", "selected_routing_reason",
                )
            }
            | {"primary_failure_category": _routing_taxonomy(row)}
            for row in routing_failures
        ],
        "false_abstention_audit": {
            "total": len(false_abstentions),
            "by_cause": dict(__import__("collections").Counter(_false_abstention_cause(row) for row in false_abstentions)),
            "cases": [
                {"case_id": row["case_id"], "question": row["question"], "actual_status": row["actual_status"], "cause": _false_abstention_cause(row)}
                for row in false_abstentions
            ],
        },
        "feature_ab": feature_ab,
        "failure_distribution": failure_counts(
            {"failure_stage": _failure_stage(row, case)}
            for row, case in zip(rows, cases, strict=True)
        ),
    }


def run() -> dict[str, Any]:
    structured = _load(STRUCTURED)
    hard = _load(HARD)
    knowledge = KnowledgeBase()
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    agent.llm = OfflineLLM()  # type: ignore[assignment]
    holdout_rows: list[dict[str, Any]] = []
    try:
        # The structured suite itself owns the historical 120-case report;
        # reusing its evaluator here avoids silently changing that benchmark.
        from evals.run_course_coverage_evaluation import evaluate as evaluate_structured

        structured_report = evaluate_structured(STRUCTURED)
        hard_rows, hard_report = _run_hard(hard, knowledge, agent)
        holdout_rows = [_one_case(knowledge, agent, case) for case in _load(HOLDOUT)]
    finally:
        memory.close()
    # The existing answerability suite contains a deterministic synthetic
    # first-round-incomplete case.  Include it as a separate supplementary
    # retrieval control so a zero natural trigger rate is not misreported as
    # a perfect success rate.
    from evals.run_answerability_evaluation import run as run_answerability
    answerability_control = run_answerability()
    holdout_grounded = [row for row in holdout_rows if row.get("module_id") or row.get("concept_id")]
    holdout_report = {
        "cases_file": str(HOLDOUT.relative_to(ROOT)),
        "cases_sha256": hashlib.sha256(HOLDOUT.read_bytes()).hexdigest(),
        "total": len(holdout_rows),
        "routing_module_accuracy": round(sum(row["module_id"] is None or row["module_id"] in {row["routed_module_id"], *row["related_module_ids"]} for row in holdout_rows) / len(holdout_rows), 4) if holdout_rows else 0.0,
        "routing_concept_accuracy": round(sum(row["concept_id"] is None or row["concept_id"] in {row["routed_concept_id"], *row["related_concept_ids"]} for row in holdout_rows) / len(holdout_rows), 4) if holdout_rows else 0.0,
        "retrieval": ir_metrics(row["real_rank"] for row in holdout_grounded),
        "answerability": answerability_metrics({"expected_status": row["expected_status"], "actual_status": row["actual_status"]} for row in holdout_rows),
        "routing_pass": sum(
            row["module_id"] is None or row["module_id"] in {row["routed_module_id"], *row["related_module_ids"]}
            for row in holdout_rows
        ),
        "cases": holdout_rows,
    }
    return {
        "report": "rag_credibility",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_sha256": knowledge.corpus_sha256,
        "structured_coverage_set": {
            "cases_file": str(STRUCTURED.relative_to(ROOT)),
            "cases_sha256": hashlib.sha256(STRUCTURED.read_bytes()).hexdigest(),
            "cases": structured_report,
        },
        "hard_natural_set": {
            "cases_file": str(HARD.relative_to(ROOT)),
            "cases_sha256": hashlib.sha256(HARD.read_bytes()).hexdigest(),
            "cases": hard_report,
            "results": hard_rows,
        },
        "holdout_set": holdout_report,
        "supplementary_retrieval_control": {
            "source_suite": "evals/answerability_cases.json",
            "triggered_cases": sum(
                int(item.get("retrieval_rounds", 0)) > 1
                for item in answerability_control.get("cases", [])
            ),
            "success_rate": answerability_control.get("supplementary_retrieval_success_rate"),
            "passed": answerability_control.get("passed"),
            "total": answerability_control.get("total"),
        },
        "baseline_reference": {
            "retrieval": "artifacts/baseline_retrieval.json",
            "course_coverage": "artifacts/baseline_course_coverage.json",
            "answerability": "artifacts/baseline_answerability.json",
            "multilingual": "artifacts/baseline_multilingual.json",
            "pytest": "artifacts/baseline_pytest.txt",
        },
        "evaluation_boundary": "offline deterministic routing/retrieval/answerability; no live LLM key required",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    hard = report["hard_natural_set"]["cases"]
    if args.markdown:
        args.markdown.write_text(
            "# RAG credibility report\n\n"
            f"Corpus SHA: `{report['corpus_sha256']}`\n\n"
            f"Structured cases: {report['structured_coverage_set']['cases']['total']} (oracle pass {report['structured_coverage_set']['cases']['passed']})\n\n"
            f"Hard cases: {hard['total']} (overall status matches {hard['overall_case_success']}; final pipeline pass {hard['final_pipeline_pass']})\n\n"
            f"Real routing: {json.dumps(hard['real_routing'], ensure_ascii=False)}\n\n"
            f"Answerability: {json.dumps(hard['answerability'], ensure_ascii=False)}\n\n"
            f"Failure distribution: {json.dumps(hard['failure_distribution'], ensure_ascii=False)}\n\n"
            "## Metric definitions\n\n"
            "`overall_case_success` counts expected vs observed answerability status matches. `retrieval_stage_pass` requires routing and a gold item in the returned candidate pool. `final_pipeline_pass` requires the status match and correct routing (for grounded cases). Latency stage values come from the same graph trace; `total_pipeline_ms` is wall clock for the same request. Rank distribution uses the first gold evidence rank over the stated denominator.\n",
            "utf-8",
        )
    print(json.dumps({
        "corpus_sha256": report["corpus_sha256"],
        "structured": {key: report["structured_coverage_set"]["cases"].get(key) for key in ("total", "passed", "hit_at_1", "hit_at_3", "mrr")},
        "hard": {key: hard.get(key) for key in ("total", "passed", "kp_coverage_rate", "real_routing", "answerability", "retrieval_process", "feature_ab", "failure_distribution")},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
