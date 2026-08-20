"""Safe, stable Harness telemetry assembled after graph execution."""

from __future__ import annotations

import uuid
from typing import Any

from .context import ContextSnapshot
from .verification import VerificationResult


def build_observability(
    runtime: Any,
    graph_result: dict[str, Any],
    before: ContextSnapshot,
    after: ContextSnapshot,
    verification: VerificationResult,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return identifiers, policy decisions and timings only; never prompts."""

    visited = list(graph_result.get("visited_nodes", []))
    trace = list(getattr(runtime, "trace", []) or [])
    durations = {item.get("node"): item.get("duration_ms", 0.0) for item in trace if isinstance(item, dict)}
    llm = getattr(runtime, "llm_metadata", {}) or {}
    return {
        "request_id": request_id or str(uuid.uuid4()),
        "intent": getattr(runtime, "intent", None),
        "concept_sub_intent": getattr(runtime, "concept_sub_intent", None),
        "module_id": getattr(runtime, "module_id", None),
        "concept_id": getattr(runtime, "concept_id", None),
        "answerability_status": getattr(runtime, "answerability_status", None),
        "missing_requirements": list(getattr(runtime, "missing_requirements", []) or []),
        "supporting_source_locators": list(getattr(runtime, "supporting_source_locators", []) or []),
        "conflicting_source_locators": list(getattr(runtime, "conflicting_source_locators", []) or []),
        "retrieval_rounds": getattr(runtime, "retrieval_rounds", 0),
        "tool_called": bool(getattr(runtime, "tool_key", None) and getattr(runtime, "verified", False)),
        "tool": getattr(runtime, "tool_key", None) if getattr(runtime, "verified", False) else None,
        "visited_nodes": visited,
        "agents_invoked": [
            name for name, node in (("assessment", "assessment"), ("curriculum", "curriculum"), ("tutor", "respond"))
            if node in visited or (name == "tutor" and any(item in visited for item in ("navigation", "out_of_scope")))
        ],
        "handoffs": [f"{left}→{right}" for left, right in zip(visited, visited[1:])],
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "retry_count": llm.get("retry_count", 0),
        "llm_enabled": bool(llm.get("model")),
        "llm_applied": bool(getattr(runtime, "llm_applied", False)),
        "latency_ms": {
            "routing": durations.get("classify", 0.0),
            "retrieval": durations.get("retrieve", 0.0),
            "llm": llm.get("latency_ms", 0.0),
            "simulation": durations.get("tool", 0.0),
            "total": round(sum(float(item or 0.0) for item in durations.values()), 3),
        },
        "timings": dict(getattr(runtime, "stage_timings", {}) or {}),
        "input_tokens": llm.get("input_tokens"),
        "output_tokens": llm.get("output_tokens"),
        "total_tokens": llm.get("total_tokens"),
        "failure_category": verification.failure_category,
        "failure_reason": verification.reason,
        "context": {
            "before_chars": before.before_chars,
            "after_chars": after.after_chars,
            "before_items_dropped": before.items_dropped,
            "after_items_dropped": after.items_dropped,
            "items_dropped": before.items_dropped + after.items_dropped,
            "recent_turn_count": len(after.recent_turns),
            "evidence_ref_count": len(after.evidence_refs),
        },
    }


__all__ = ["build_observability"]
