"""Small explicit state graph used by the teaching Agent.

The graph is deliberately dependency-free so the offline demo keeps working.
Its node and state contracts mirror production graph orchestrators: every node
receives one typed state object, mutates only its owned fields, and returns a
human-readable trace detail.  A LangGraph adapter can therefore be added
without rewriting numerical tools or API responses.
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
    module_from_context: bool = False

    retrieval_query: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)

    tool_key: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    inherited_parameters: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    misconceptions: list[dict[str, str]] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    learning_note: str = ""
    recommendation: dict[str, str] = field(default_factory=dict)
    answer: str = ""
    response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeOutcome:
    detail: str


NodeHandler = Callable[[AgentState], NodeOutcome]


@dataclass(frozen=True)
class WorkflowNode:
    name: str
    handler: NodeHandler


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
