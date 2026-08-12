"""Deterministic, explainable knowledge-point mastery updates.

The service is deliberately independent of the Tutor and Curriculum agents:
only assessed learner evidence can change a concept state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


NOT_STARTED = "NOT_STARTED"
LEARNING = "LEARNING"
NEEDS_REVIEW = "NEEDS_REVIEW"
MASTERED = "MASTERED"


@dataclass(frozen=True)
class MasteryState:
    concept_id: str
    mastery_score: float = 0.0
    attempt_count: int = 0
    correct_count: int = 0
    hint_count: int = 0
    recent_misconceptions: tuple[dict[str, Any], ...] = ()
    last_practiced_at: str | None = None
    status: str = NOT_STARTED

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["recent_misconceptions"] = list(self.recent_misconceptions)
        return payload


def _status(score: float, attempts: int, correctness: bool | None, recent: list[dict[str, Any]]) -> str:
    if attempts == 0:
        return NOT_STARTED
    if correctness is False or recent:
        return NEEDS_REVIEW if score < 0.75 else LEARNING
    if attempts >= 3 and score >= 0.55:
        return MASTERED
    return LEARNING


def update_mastery(
    existing: MasteryState,
    *,
    correctness: bool | None,
    hints_used: int = 0,
    misconception: dict[str, Any] | None = None,
) -> MasteryState:
    """Apply one bounded learner-evidence update.

    A correct answer without hints adds 0.19; a correct answer after hints
    adds 0.10. Incorrect evidence subtracts 0.12. Scores are clamped to
    ``[0, 1]`` and repeated evidence remains deterministic and auditable.
    """

    hints = max(0, int(hints_used or 0))
    attempts = existing.attempt_count + 1
    correct_count = existing.correct_count + int(correctness is True)
    if correctness is True:
        delta = 0.10 if hints else 0.19
    elif correctness is False:
        delta = -0.12
    else:
        delta = 0.0
    score = round(max(0.0, min(1.0, existing.mastery_score + delta)), 2)
    recent = list(existing.recent_misconceptions)
    if misconception:
        recent = [misconception, *recent[:2]]
    elif correctness is True:
        recent = []
    return MasteryState(
        concept_id=existing.concept_id,
        mastery_score=score,
        attempt_count=attempts,
        correct_count=correct_count,
        hint_count=existing.hint_count + hints,
        recent_misconceptions=tuple(recent),
        last_practiced_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=_status(score, attempts, correctness, recent),
    )


__all__ = [
    "LEARNING",
    "MASTERED",
    "NEEDS_REVIEW",
    "NOT_STARTED",
    "MasteryState",
    "update_mastery",
]
