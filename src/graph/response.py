"""API response finalization after a compiled LangGraph run."""

from __future__ import annotations

import time
from typing import Any

from ..teaching_team import build_team_trace


def finalize(agent: Any, graph_result: dict[str, Any], started: float) -> dict[str, Any]:
    """Attach stable API/debug metadata without putting it in graph nodes."""

    completed = graph_result["runtime"]
    graph_visited_nodes = graph_result.get("visited_nodes", [])
    graph_route = graph_result.get("route_taken", completed.intent)
    agents_invoked: list[str] = []
    if "assessment" in graph_visited_nodes:
        agents_invoked.append("assessment")
    if "curriculum" in graph_visited_nodes:
        agents_invoked.append("curriculum")
    if any(node in graph_visited_nodes for node in ("respond", "navigation", "out_of_scope")):
        agents_invoked.append("tutor")
    handoffs = [
        f"{left}→{right}"
        for left, right in zip(graph_visited_nodes, graph_visited_nodes[1:])
    ]
    llm_call_count = int(
        completed.llm_metadata.get("status") not in {"not_called", "disabled"}
    )
    if completed.response:
        completed.response["trace"] = completed.trace
        completed.response["workflow"] = {
            "nodes": [item["node"] for item in completed.trace]
        }
        durations = {
            item["node"]: item.get("duration_ms", 0.0)
            for item in completed.trace
        }
        completed.response["observability"] = {
            "request_id": None,
            "intent": completed.intent,
            "concept_sub_intent": completed.concept_sub_intent,
            "module_id": completed.module_id,
            "concept_id": completed.concept_id,
            "answerability_status": completed.answerability_status,
            "missing_requirements": completed.missing_requirements,
            "supporting_source_locators": completed.supporting_source_locators,
            "conflicting_source_locators": completed.conflicting_source_locators,
            "retrieval_rounds": completed.retrieval_rounds,
            "llm_enabled": agent.llm.enabled,
            "llm_applied": completed.llm_applied,
            "provider": completed.llm_metadata.get("provider"),
            "model": completed.llm_metadata.get("model"),
            "retry_count": completed.llm_metadata.get("retry_count", 0),
            "latency_ms": {
                "routing": durations.get("classify", 0.0),
                "retrieval": durations.get("retrieve", 0.0),
                "llm": completed.llm_metadata.get("latency_ms", 0.0),
                "simulation": durations.get("tool", 0.0),
                "total": round((time.perf_counter() - started) * 1000, 2),
            },
            "input_tokens": completed.llm_metadata.get("input_tokens"),
            "output_tokens": completed.llm_metadata.get("output_tokens"),
            "total_tokens": completed.llm_metadata.get("total_tokens"),
            "tool_called": bool(completed.response.get("tool_called")),
            "source_locators": [
                source.get("source")
                for source in completed.sources
                if source.get("source")
            ],
            "visited_nodes": graph_visited_nodes,
            "route_taken": graph_route,
            "agents_invoked": agents_invoked,
            "handoffs": handoffs,
            "llm_call_count": llm_call_count,
            "curriculum_decision": completed.curriculum_decision,
            "assessment_result": completed.assessment_result,
        }
        completed.response["graph"] = {
            "visited_nodes": graph_visited_nodes,
            "route_taken": graph_route,
        }
    completed.response["teaching_team"] = build_team_trace(completed.trace)
    return completed.response

