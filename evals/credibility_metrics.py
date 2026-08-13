"""Shared, conservative metrics for course-RAG credibility evaluations.

This module intentionally contains no retrieval logic.  It only defines what
counts as a gold evidence match and how to calculate standard IR and
answerability metrics so separate evaluation suites cannot silently drift.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable


FAILURE_STAGES = (
    "PASS",
    "CORPUS_COVERAGE_FAILURE",
    "CHUNKING_CONTEXT_FAILURE",
    "ROUTING_FAILURE",
    "RETRIEVAL_RECALL_FAILURE",
    "RANKING_FAILURE",
    "ANSWERABILITY_FALSE_ABSTENTION",
    "ANSWERABILITY_UNSAFE_SUPPORT",
    "GENERATION_FAILURE",
)
ABSTENTION_STATUSES = frozenset({"PARTIAL", "NONE", "CONFLICT", "OUT_OF_SCOPE"})
SUPPORTED_STATUS = "SUPPORTED"


def _locator_matches(source: str, locator: str) -> bool:
    """Match exact/chunk/page locators, including a stable notebook basename."""

    source = source.strip()
    locator = locator.strip()
    if not source or not locator:
        return False
    if source == locator or source.startswith(locator + "#"):
        return True
    # Existing structured cases use a reviewed path while the indexed source
    # may omit ``reference/``.  A basename match is intentionally limited to
    # the same source file, never to an alias or a query term.
    return Path(source.split("#", 1)[0]).name == Path(locator.split("#", 1)[0]).name


def gold_match(item: dict[str, Any], case: dict[str, Any]) -> bool:
    """Return whether an evidence item is one of the case's valid gold items.

    A locator or an evidence phrase is sufficient.  Alternative locators and
    phrases are accepted because adjacent textbook/notebook chunks can carry
    the same claim.  Query aliases are never consulted here.
    """

    source = str(item.get("source") or "")
    locators = [
        *case.get("gold_source_locators", []),
        *case.get("acceptable_source_locators", []),
        *case.get("acceptable_alternative_source_locators", []),
    ]
    if any(_locator_matches(source, str(locator)) for locator in locators):
        return True
    haystack = " ".join(
        str(item.get(field) or "") for field in ("title", "content", "claim", "summary", "source")
    ).casefold()
    phrases = [
        *case.get("gold_evidence_phrases", []),
        *case.get("acceptable_evidence_phrases", []),
    ]
    return any(str(phrase).casefold() in haystack for phrase in phrases if str(phrase).strip())


def first_gold_rank(results: Iterable[dict[str, Any]], case: dict[str, Any]) -> int | None:
    for rank, item in enumerate(results, start=1):
        if gold_match(item, case):
            return rank
    return None


def ir_metrics(ranks: Iterable[int | None]) -> dict[str, float]:
    values = list(ranks)
    total = len(values)
    if not total:
        return {"hit_at_1": 0.0, "hit_at_3": 0.0, "mrr": 0.0}
    return {
        "hit_at_1": round(sum(rank == 1 for rank in values) / total, 4),
        "hit_at_3": round(sum(rank is not None and rank <= 3 for rank in values) / total, 4),
        "mrr": round(sum((1.0 / rank) if rank else 0.0 for rank in values) / total, 4),
    }


def rank_distribution(ranks: Iterable[int | None]) -> dict[str, int]:
    """Count the first relevant result position without collapsing ranks."""

    counts = {"rank_1": 0, "rank_2": 0, "rank_3": 0, "rank_4_plus": 0, "not_found": 0}
    for rank in ranks:
        if rank == 1:
            counts["rank_1"] += 1
        elif rank == 2:
            counts["rank_2"] += 1
        elif rank == 3:
            counts["rank_3"] += 1
        elif isinstance(rank, int) and rank >= 4:
            counts["rank_4_plus"] += 1
        else:
            counts["not_found"] += 1
    return counts


def answerability_metrics(results: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Calculate status metrics from expected and observed case outcomes."""

    rows = list(results)
    total = len(rows)
    if not total:
        return {
            "answer_success_rate": 0.0,
            "false_abstention_rate": 0.0,
            "unsupported_answer_rate": 0.0,
            "abstention_precision": 0.0,
            "evidence_sufficiency_accuracy": 0.0,
        }
    expected_supported = [row for row in rows if row.get("expected_status", SUPPORTED_STATUS) == SUPPORTED_STATUS]
    expected_unsupported = [row for row in rows if row.get("expected_status", SUPPORTED_STATUS) != SUPPORTED_STATUS]
    observed_abstentions = [row for row in rows if row.get("actual_status") in ABSTENTION_STATUSES]
    correct = [
        row for row in rows
        if row.get("actual_status") == row.get("expected_status", SUPPORTED_STATUS)
    ]
    false_abstentions = [
        row for row in expected_supported if row.get("actual_status") in ABSTENTION_STATUSES
    ]
    unsupported = [
        row for row in expected_unsupported if row.get("actual_status") == SUPPORTED_STATUS
    ]
    return {
        "answer_success_rate": round(len(correct) / total, 4),
        "false_abstention_rate": round(len(false_abstentions) / len(expected_supported), 4) if expected_supported else 0.0,
        "unsupported_answer_rate": round(len(unsupported) / len(expected_unsupported), 4) if expected_unsupported else 0.0,
        "abstention_precision": round(
            sum(row in expected_unsupported for row in observed_abstentions) / len(observed_abstentions), 4
        ) if observed_abstentions else 1.0,
        "evidence_sufficiency_accuracy": round(len(correct) / total, 4),
    }


def classify_failure(
    *,
    corpus_has_gold: bool,
    routing_ok: bool,
    candidate_rank: int | None,
    final_rank: int | None,
    expected_status: str,
    actual_status: str | None,
    answer_present: bool,
    required_claims_present: bool = True,
    chunk_context_available: bool = True,
) -> str:
    """Assign exactly one deterministic primary failure stage."""

    if not corpus_has_gold:
        return "CORPUS_COVERAGE_FAILURE"
    if not chunk_context_available:
        return "CHUNKING_CONTEXT_FAILURE"
    if not routing_ok:
        return "ROUTING_FAILURE"
    if candidate_rank is None:
        return "RETRIEVAL_RECALL_FAILURE"
    if final_rank is None:
        return "RANKING_FAILURE"
    if expected_status == SUPPORTED_STATUS and actual_status in ABSTENTION_STATUSES:
        return "ANSWERABILITY_FALSE_ABSTENTION"
    if expected_status != SUPPORTED_STATUS and actual_status == SUPPORTED_STATUS:
        return "ANSWERABILITY_UNSAFE_SUPPORT"
    if expected_status == SUPPORTED_STATUS and (not answer_present or not required_claims_present):
        return "GENERATION_FAILURE"
    return "PASS"


def failure_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("failure_stage")) for row in rows)
    return {stage: int(counts.get(stage, 0)) for stage in FAILURE_STAGES if counts.get(stage, 0)}
