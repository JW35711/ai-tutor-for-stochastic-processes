"""One thin execution boundary around the compiled StochLab graph."""

from __future__ import annotations

import time
from typing import Any

from ..graph.response import finalize
from .context import ContextBudget, compact_context
from .observability import build_observability
from .verification import verify_runtime


def registered_tool_policy(agent: Any, tool_key: str | None) -> dict[str, Any]:
    """Describe the existing allow-list without creating an executor."""

    tools = getattr(agent, "tools", {})
    allowed = isinstance(tool_key, str) and tool_key in tools
    return {
        "allowed": allowed,
        "tool_key": tool_key if allowed else None,
        "bounded": allowed,
        "deterministic_owner": "python_tool" if allowed else None,
    }


class TutorHarness:
    """Execute the existing graph with bounded context and safe telemetry.

    This class intentionally does not classify, retrieve, call tools, grade,
    recommend, or call the provider.  Those responsibilities stay with the
    existing domain runtime and agents.
    """

    def __init__(self, agent: Any, *, context_budget: ContextBudget | None = None) -> None:
        self.agent = agent
        self.context_budget = context_budget or ContextBudget()

    def execute(
        self,
        state: Any,
        *,
        started: float | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter() if started is None else started
        before = compact_context(state, self.context_budget)
        graph_result: dict[str, Any] | None = None
        try:
            graph_result = self.agent.workflow.invoke({
                "runtime": state,
                "visited_nodes": [],
                "route_taken": "",
                "supplementary_query": "",
            })
        except Exception as error:
            # Keep the existing exception/API behavior while attaching a safe
            # category for logs and callers that inspect the state.
            state.harness_metadata = {
                "request_id": request_id,
                "failure_category": "TOOL_EXECUTION_FAILED" if getattr(state, "intent", "") == "simulation" else "LLM_PROVIDER_FAILED",
                "failure_reason": type(error).__name__,
                "context": {"before_chars": before.before_chars, "items_dropped": before.items_dropped},
            }
            raise
        completed = graph_result["runtime"]
        after = compact_context(completed, self.context_budget)
        # Omitting unrelated AgentState fields is expected.  Mark context
        # compaction only when the explicit character budget was exceeded.
        verification = verify_runtime(
            completed,
            context_compacted=before.before_chars > self.context_budget.max_chars,
        )
        completed.harness_metadata = build_observability(
            completed,
            graph_result,
            before,
            after,
            verification,
            request_id=request_id,
        )
        completed.harness_metadata["tool_policy"] = registered_tool_policy(
            self.agent, getattr(completed, "tool_key", None)
        )
        response = finalize(self.agent, graph_result, started)
        # Keep the API contract stable; Harness telemetry is nested under the
        # existing observability object and is safe for debug/log consumers.
        if isinstance(response.get("observability"), dict):
            response["observability"]["harness"] = completed.harness_metadata
        return response


__all__ = ["TutorHarness", "registered_tool_policy"]
