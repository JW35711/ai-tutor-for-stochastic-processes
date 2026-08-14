"""Official LangGraph runtime for the conditional StochLab agent handoffs."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from ..workflow import AgentState, NodeOutcome
from ..agents.handoffs import assess, recommend
from .state import TutorState


_LEGACY_TRACE_NAMES = {
    "route": "classify",
    "retrieve": "retrieve",
    "plan": "plan",
    "tool": "tool",
    "diagnose": "diagnose",
    "memory": "memory",
    "respond": "respond",
    "navigation": "respond",
    "out_of_scope": "respond",
}


def _run_node(
    graph_state: TutorState,
    node_name: str,
    handler: Callable[[AgentState], NodeOutcome],
    *,
    trace_name: str | None = None,
) -> dict[str, Any]:
    """Invoke an existing domain node and preserve the legacy trace contract."""

    runtime = graph_state["runtime"]
    visited = [*graph_state.get("visited_nodes", []), node_name]
    route_taken = graph_state.get("route_taken", "")
    public_trace_name = trace_name if trace_name is not None else _LEGACY_TRACE_NAMES.get(node_name)
    started = perf_counter()
    try:
        outcome = handler(runtime)
    except Exception:
        runtime.trace.append(
            {
                "node": public_trace_name or node_name,
                "detail": "failed",
                "status": "error",
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            }
        )
        raise
    if public_trace_name:
        # The old API exposes timings for the seven domain steps. Graph-only
        # routing/evidence nodes remain in visited_nodes instead of changing
        # that backwards-compatible list.
        runtime.trace.append(
            {
                "node": public_trace_name,
                "detail": outcome.detail,
                "status": "ok",
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            }
        )
    return {
        "runtime": runtime,
        "visited_nodes": visited,
        "route_taken": route_taken,
    }


def _route(graph_state: TutorState) -> Literal[
    "curriculum", "concept", "simulation", "practice", "quiz", "respond", "out_of_scope"
]:
    intent = graph_state["runtime"].intent
    if intent == "course_navigation":
        return "curriculum"
    if intent == "concept":
        return "concept"
    if intent == "simulation":
        return "simulation"
    if intent in {"practice", "quiz"}:
        return intent
    # Social and harmless general turns deliberately bypass retrieval,
    # evidence sufficiency, tools, and memory updates.
    if intent in {"social_chat", "general_chat"}:
        return "respond"
    return "out_of_scope"


def _after_evidence(graph_state: TutorState) -> Literal["supplement", "plan", "respond"]:
    runtime = graph_state["runtime"]
    if (
        runtime.intent == "concept"
        and runtime.answerability_status == "PARTIAL"
        and runtime.retrieval_rounds < 3
        and not runtime.question_requirements.get("missing_user_requirements")
        and runtime.retrieval_query != ""
        and runtime.question_requirements
    ):
        supplement = graph_state.get("supplementary_query", "")
        if supplement:
            return "supplement"
    if runtime.intent == "simulation":
        return "plan"
    return "respond"


def _after_curriculum(graph_state: TutorState) -> Literal["navigation", "respond"]:
    if graph_state["runtime"].intent == "course_navigation":
        return "navigation"
    return "respond"


def build_graph(agent: Any):
    """Build and compile the official conditional graph for one tutor service."""

    builder = StateGraph(TutorState)

    def route_node(state: TutorState) -> dict[str, Any]:
        result = _run_node(state, "route", agent._node_classify)
        result["route_taken"] = state["runtime"].intent
        return result

    def retrieve_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "retrieve", agent._node_retrieve)

    def plan_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "plan", agent._node_plan)

    def tool_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "tool", agent._node_tool)

    def diagnose_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "diagnose", agent._node_diagnose)

    def memory_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "memory", agent._node_memory)

    def respond_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "respond", agent._node_respond)

    def navigation_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "navigation", agent._node_respond)

    def out_of_scope_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "out_of_scope", agent._node_respond)

    def curriculum_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "curriculum", lambda runtime: recommend(agent, runtime), trace_name=None)

    def assessment_node(state: TutorState) -> dict[str, Any]:
        return _run_node(state, "assessment", lambda runtime: assess(agent, runtime), trace_name=None)

    def evidence_node(state: TutorState) -> dict[str, Any]:
        # LangGraph state is intentionally simple; the agent is a service
        # dependency captured by this graph builder, not a graph state field.
        runtime = state["runtime"]
        evidence_started = perf_counter()
        agent._update_answerability(runtime)
        supplement = agent._supplementary_query(runtime)
        runtime.stage_timings["answerability"] = round((perf_counter() - evidence_started) * 1000, 3)
        return {
            "runtime": runtime,
            "visited_nodes": [*state.get("visited_nodes", []), "evidence"],
            "route_taken": state.get("route_taken", ""),
            "supplementary_query": supplement,
        }

    def supplement_node(state: TutorState) -> dict[str, Any]:
        runtime = state["runtime"]
        supplement = state.get("supplementary_query", "")
        if supplement and runtime.retrieval_rounds < 3:
            extra = agent._retrieve_for_state(runtime, supplement)
            seen = {str(source.get("source")) for source in runtime.sources}
            for source in extra:
                locator = str(source.get("source"))
                if locator not in seen:
                    runtime.sources.append(source)
                    seen.add(locator)
            limit = 6 if runtime.comparison_module_ids else 4
            runtime.sources = runtime.sources[:limit]
            runtime.retrieval_query = supplement
            runtime.retrieval_rounds += 1
            agent._update_answerability(runtime)
        return {
            "runtime": runtime,
            "visited_nodes": [*state.get("visited_nodes", []), "supplement"],
            "route_taken": state.get("route_taken", ""),
            "supplementary_query": "",
        }

    builder.add_node("route", route_node)
    builder.add_node("curriculum", curriculum_node)
    builder.add_node("navigation", navigation_node)
    builder.add_node("out_of_scope", out_of_scope_node)
    builder.add_node("assessment", assessment_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("evidence", evidence_node)
    builder.add_node("supplement", supplement_node)
    builder.add_node("plan", plan_node)
    builder.add_node("tool", tool_node)
    builder.add_node("diagnose", diagnose_node)
    builder.add_node("memory", memory_node)
    builder.add_node("respond", respond_node)

    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        _route,
        {
            "curriculum": "curriculum",
            "concept": "retrieve",
            "simulation": "retrieve",
            "practice": "assessment",
            "quiz": "assessment",
            "respond": "respond",
            "out_of_scope": "out_of_scope",
        },
    )
    builder.add_edge("navigation", END)
    builder.add_edge("out_of_scope", END)
    builder.add_conditional_edges(
        "curriculum",
        _after_curriculum,
        {"navigation": "navigation", "respond": "respond"},
    )
    builder.add_edge("assessment", "curriculum")
    builder.add_edge("retrieve", "evidence")
    builder.add_conditional_edges(
        "evidence",
        _after_evidence,
        {"supplement": "supplement", "plan": "plan", "respond": "respond"},
    )
    builder.add_edge("supplement", "evidence")
    builder.add_edge("plan", "tool")
    builder.add_edge("tool", "diagnose")
    builder.add_edge("diagnose", "memory")
    builder.add_edge("memory", "respond")
    builder.add_edge("respond", END)
    return builder.compile()


__all__ = ["build_graph"]
