"""Typed state shared by the official LangGraph workflow.

The domain state remains an ``AgentState`` for compatibility with the service
and tests.  LangGraph carries that one domain object together with graph-only
observability fields; tools, retrieval, memory and API contracts stay outside
the graph runtime.
"""

from __future__ import annotations

from typing import TypedDict

from ..workflow import AgentState


class TutorState(TypedDict, total=False):
    """The small shared state contract used by the compiled tutor graph."""

    runtime: AgentState
    visited_nodes: list[str]
    route_taken: str
    supplementary_query: str


__all__ = ["TutorState"]
