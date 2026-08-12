"""Deterministic assessment agent for quiz and practice evidence."""

from __future__ import annotations

from typing import Any

from .contracts import AssessmentResult


class AssessmentAgent:
    """Estimate understanding; it never writes the final Tutor explanation."""

    # The assessment bank has one reviewed item per module. Keeping this map
    # next to the bank adapter gives the handoff a knowledge-point target
    # without inventing any new curriculum structure.
    QUESTION_CONCEPTS = {
        "q00": "m00-standard-error",
        "q01": "m01-poisson-process",
        "q02": "m02-drift-variance",
        "q03": "m03-continuous-time-path",
        "q04": "m04-terminal-distribution",
        "q05": "m05-stationary-distribution",
        "q06": "m06-holding-times",
        "q07": "m07-mm1-queue",
        "q08": "m08-thinning",
        "q09": "m09-self-avoidance",
        "q10": "m10-coalescence",
    }

    def evaluate(
        self,
        attempt: dict[str, Any],
        *,
        current_concept_id: str | None = None,
        existing_mastery: float = 0.0,
        attempt_count: int = 0,
    ) -> AssessmentResult:
        correct = attempt.get("correct")
        concept_id = (
            attempt.get("concept_id")
            or self.QUESTION_CONCEPTS.get(str(attempt.get("question_id")))
            or current_concept_id
        )
        correctness = bool(correct) if isinstance(correct, bool) else self._grade_free_text(attempt)
        hints_used = int(attempt.get("hints_used", 0) or 0)
        attempt_number = int(attempt.get("attempt_number", attempt_count + 1) or attempt_count + 1)
        if correctness is True:
            confidence = 0.9 if hints_used == 0 else 0.75
            delta = 0.1 if existing_mastery < 1.0 else 0.0
            return AssessmentResult(
                concept_id=concept_id,
                correctness=True,
                confidence=confidence,
                misconception_type=None,
                mastery_delta=delta,
                needs_review=False,
                recommended_difficulty="next",
                question_id=attempt.get("question_id"),
                module_id=attempt.get("module_id"),
                hints_used=hints_used,
                attempt_count=attempt_number,
                evidence="deterministic answer key" if isinstance(correct, bool) else "free-text answer matched the expected concept",
            )
        misconception = "concept_check_incorrect" if correctness is False else "incomplete_attempt"
        summary = "The response does not yet state the defining relationship." if correctness is False else "No assessable answer was provided."
        return AssessmentResult(
            concept_id=concept_id,
            correctness=correctness,
            confidence=0.8 if correctness is False else 0.4,
            misconception_type=misconception,
            mastery_delta=-0.05 if correctness is False else 0.0,
            needs_review=True,
            recommended_difficulty="guided",
            question_id=attempt.get("question_id"),
            module_id=attempt.get("module_id"),
            hints_used=hints_used,
            misconception_summary=summary,
            attempt_count=attempt_number,
            evidence="deterministic answer key" if isinstance(correct, bool) else "free-text response was incomplete or did not match the expected idea",
        )

    @staticmethod
    def _grade_free_text(attempt: dict[str, Any]) -> bool | None:
        answer = str(attempt.get("student_answer") or "").strip().lower()
        expected = str(attempt.get("expected_answer") or "").strip().lower()
        if not answer or not expected:
            return None
        expected_terms = [term for term in expected.replace(",", " ").split() if len(term) > 2]
        return bool(expected_terms) and sum(term in answer for term in expected_terms) >= max(1, len(expected_terms) // 2)
