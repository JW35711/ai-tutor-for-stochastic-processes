"""Typed boundaries between the three educational agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CurriculumDecision:
    """A deterministic recommendation about what the learner should study."""

    target_concept: str | None
    prerequisite_concepts: tuple[str, ...] = ()
    recommended_action: str = "continue_current_concept"
    reason: str = ""
    next_concept: str | None = None
    module_id: str | None = None
    decision_type: str = "CONTINUE"
    teaching_mode: str = "FOUNDATION"
    decision_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prerequisite_concepts"] = list(self.prerequisite_concepts)
        return payload


@dataclass(frozen=True)
class AssessmentResult:
    """Structured evidence about one learner attempt, not a teaching answer."""

    concept_id: str | None
    correctness: bool | None
    confidence: float
    misconception_type: str | None
    mastery_delta: float
    needs_review: bool
    recommended_difficulty: str
    question_id: str | None = None
    module_id: str | None = None
    hints_used: int = 0
    misconception_summary: str | None = None
    attempt_count: int = 1
    evidence: str | None = None
    grading_method: str = "deterministic_keyword_or_relation_check"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TutorContext:
    """Inputs the Tutor Agent may use when choosing how to teach."""

    question: str
    concept_id: str | None = None
    curriculum_decision: dict[str, Any] = field(default_factory=dict)
    assessment: dict[str, Any] = field(default_factory=dict)
    sources: tuple[dict[str, Any], ...] = ()
    answerability_status: str = "NONE"
    sub_intent: str = "definition"
    tool_result: dict[str, Any] = field(default_factory=dict)
    teaching_mode: str = "FOUNDATION"
    mastery_status: str = "NOT_STARTED"
    misconception_focus: str | None = None
