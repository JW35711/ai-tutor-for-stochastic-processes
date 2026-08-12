"""Tutor Agent policy: choose how to teach after evidence and assessment."""

from __future__ import annotations

from typing import Any, Callable

from .contracts import TutorContext


class TutorAgent:
    """Own answerability-aware teaching policy, not retrieval or computation."""

    def answer_concept(
        self,
        context: TutorContext,
        *,
        synthesise: Callable[[], str],
        partial: Callable[[], str],
        conflict: Callable[[], str],
        none: Callable[[], str],
        fallback: Callable[[], str],
    ) -> str:
        """Select a response policy before invoking the synthesis callback."""

        if context.answerability_status == "CONFLICT":
            return conflict()
        if context.answerability_status == "PARTIAL":
            return partial()
        if context.answerability_status == "NONE":
            return none()
        if context.sources:
            return synthesise()
        return fallback()

    def assessment_feedback(
        self,
        result: dict[str, Any],
        decision: dict[str, Any],
    ) -> str:
        """Turn an assessment result into concise feedback, without rescoring it."""

        if result.get("correct") is True:
            next_concept = decision.get("next_concept")
            if next_concept:
                return (
                    "Correct. You can now move toward the next knowledge point "
                    f"({next_concept})."
                )
            return "Correct. Keep the same reasoning and try a nearby application."
        explanation = str(result.get("explanation") or "Review the worked concept and try again.")
        return (
            "This answer needs review. "
            f"{explanation} "
            "Start with the recommended prerequisite before attempting a harder question."
        )

    def simulation_feedback(
        self,
        *,
        verified: bool,
        result_summary: str,
        module_label: str,
        guiding_question: str,
        error: str | None = None,
        corrections: list[str] | None = None,
    ) -> str:
        """Explain immutable Python output without recalculating its numbers."""

        if verified:
            answer = (
                f"## Result\n{result_summary}\n\n"
                f"## What it means\nThis experiment illustrates {module_label.lower()} "
                "and compares empirical output with the corresponding theoretical reference.\n\n"
                f"## Try next\n{guiding_question}"
            )
        else:
            answer = (
                f"The parameters were not valid: {error or 'the tool rejected the request'}. "
                "Please adjust them and try again."
            )
        if corrections:
            answer += "\n\n## Check this idea\n" + "\n".join(
                f"- {item}" for item in corrections
            )
        return answer

    def scope_response(
        self,
        *,
        is_general: bool,
        general: Callable[[], str],
        out_of_scope: Callable[[], str],
    ) -> str:
        """Keep casual and out-of-course responses in the Tutor boundary."""

        return general() if is_general else out_of_scope()
