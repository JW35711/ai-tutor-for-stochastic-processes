"""Compatibility domain-state contracts for the teaching Agent.

The runtime graph now lives in :mod:`src.graph.workflow` and is compiled with
the official LangGraph ``StateGraph``.  These dataclasses remain public so
service code and older integrations can still construct and inspect a domain
state without depending on LangGraph internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable


@dataclass
class AgentState:
    """State passed through classify → retrieve → plan → tool → teaching."""

    question: str
    session_id: str
    previous_turn: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)

    module_id: str | None = None
    module: Any = None
    topic: str | None = None
    intent: str = "unsupported"
    concept_sub_intent: str = "definition"
    follow_up_kind: str | None = None
    concept_id: str | None = None
    comparison_module_ids: list[str] = field(default_factory=list)
    comparison_concept_ids: list[str] = field(default_factory=list)
    module_from_context: bool = False
    curriculum_decision: dict[str, Any] = field(default_factory=dict)
    assessment_input: dict[str, Any] = field(default_factory=dict)
    assessment_result: dict[str, Any] = field(default_factory=dict)

    retrieval_query: str = ""
    detected_query_language: str = "en"
    ui_language: str = "en"
    response_language: str = "en"
    translation_applied: bool = False
    retrieval_query_en: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    question_requirements: dict[str, Any] = field(default_factory=dict)
    answerability_status: str = "NONE"
    missing_requirements: list[str] = field(default_factory=list)
    supporting_source_locators: list[str] = field(default_factory=list)
    conflicting_source_locators: list[str] = field(default_factory=list)
    retrieval_rounds: int = 0

    tool_key: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    inherited_parameters: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    misconceptions: list[dict[str, str]] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    learning_note: str = ""
    recommendation: dict[str, str] = field(default_factory=dict)
    teaching_mode: str = "FOUNDATION"
    current_concept_mastery: dict[str, Any] = field(default_factory=dict)
    prerequisite_mastery: dict[str, dict[str, Any]] = field(default_factory=dict)
    answer: str = ""
    llm_applied: bool = False
    llm_metadata: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)

    # Notebook-derived experiment context.  Only identifiers and compact
    # parameters are carried; raw simulation arrays remain in the result.
    active_experiment_id: str | None = None
    active_visualization_id: str | None = None
    active_parameters: dict[str, Any] = field(default_factory=dict)
    latest_result_reference: str | None = None
    latest_result_summary: str | None = None
    experiment_id: str | None = None
    visualization_id: str | None = None
    experiment_recommendations: list[dict[str, Any]] = field(default_factory=list)
    action_type: str | None = None
    requested_concept_id: str | None = None
    requested_experiment_id: str | None = None

    # Routing diagnostics are internal metadata; they do not affect the
    # student-facing answer contract.
    routing_strategy: str = "UNSET"
    routing_candidates: list[dict[str, Any]] = field(default_factory=list)
    routing_confidence: float | None = None
    selected_routing_reason: str = ""
    stage_timings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeOutcome:
    detail: str


NodeHandler = Callable[[AgentState], NodeOutcome]


@dataclass(frozen=True)
class WorkflowNode:
    name: str
    handler: NodeHandler
    enabled: Callable[[AgentState], bool] | None = None


class StateGraph:
    """Execute named nodes in a declared order and expose the full trace."""

    def __init__(self, nodes: list[WorkflowNode]) -> None:
        if not nodes:
            raise ValueError("a state graph needs at least one node")
        names = [node.name for node in nodes]
        if len(names) != len(set(names)):
            raise ValueError("state graph node names must be unique")
        self.nodes = tuple(nodes)

    @property
    def node_names(self) -> tuple[str, ...]:
        return tuple(node.name for node in self.nodes)

    def invoke(self, state: AgentState) -> AgentState:
        for node in self.nodes:
            if node.enabled is not None and not node.enabled(state):
                continue
            started = perf_counter()
            try:
                outcome = node.handler(state)
            except Exception as error:
                state.trace.append(
                    {
                        "node": node.name,
                        "detail": f"failed: {type(error).__name__}",
                        "status": "error",
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                    }
                )
                raise
            state.trace.append(
                {
                    "node": node.name,
                    "detail": outcome.detail,
                    "status": "ok",
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
        return state
