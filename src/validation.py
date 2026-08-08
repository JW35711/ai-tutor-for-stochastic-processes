"""Shared input contracts used by the Agent core and HTTP adapter."""

from __future__ import annotations

from .config import env_int


MAX_QUESTION_CHARS = env_int(
    "MAX_QUESTION_CHARS",
    4000,
    minimum=100,
    maximum=100_000,
)


def validate_question(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("question must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("question is required")
    if len(normalized) > MAX_QUESTION_CHARS:
        raise ValueError(f"question exceeds {MAX_QUESTION_CHARS} characters")
    return normalized


def validate_session_id(value: object, *, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            raise ValueError("session_id is required")
        return None
    if not isinstance(value, str):
        raise ValueError("session_id must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > 128 or "/" in normalized or any(
        ord(character) < 32 for character in normalized
    ):
        raise ValueError(
            "session_id must contain 1 to 128 printable characters without a slash"
        )
    return normalized
