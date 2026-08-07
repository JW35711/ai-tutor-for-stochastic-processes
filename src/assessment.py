"""Concept-check engine for adaptive module assessment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_QUIZ_PATH = Path(__file__).resolve().parent.parent / "data" / "quizzes.json"


class AssessmentEngine:
    def __init__(self, path: Path = DEFAULT_QUIZ_PATH) -> None:
        raw = path.read_bytes()
        try:
            questions = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid assessment bank: {error}") from error
        self._validate_bank(questions)
        self.bank_sha256 = hashlib.sha256(raw).hexdigest()
        self.questions = {item["id"]: item for item in questions}
        self.by_module = {item["module_id"]: item for item in questions}

    @staticmethod
    def _validate_bank(questions: object) -> None:
        if not isinstance(questions, list) or not questions:
            raise ValueError("assessment bank must be a non-empty JSON list")

        question_ids: set[str] = set()
        module_ids: set[str] = set()
        required = {
            "id",
            "module_id",
            "question",
            "choices",
            "correct_index",
            "explanation",
        }
        for position, item in enumerate(questions):
            if not isinstance(item, dict) or set(item) != required:
                raise ValueError(
                    f"assessment item {position} must contain exactly {sorted(required)}"
                )
            for field in ("id", "module_id", "question", "explanation"):
                if not isinstance(item[field], str) or not item[field].strip():
                    raise ValueError(
                        f"assessment item {position} has invalid {field}"
                    )
            choices = item["choices"]
            if (
                not isinstance(choices, list)
                or not 2 <= len(choices) <= 8
                or any(
                    not isinstance(choice, str) or not choice.strip()
                    for choice in choices
                )
                or len(set(choices)) != len(choices)
            ):
                raise ValueError(
                    f"assessment item {position} must have 2 to 8 unique choices"
                )
            correct_index = item["correct_index"]
            if type(correct_index) is not int or not 0 <= correct_index < len(choices):
                raise ValueError(
                    f"assessment item {position} has invalid correct_index"
                )
            if item["id"] in question_ids:
                raise ValueError(f"duplicate assessment id: {item['id']}")
            if item["module_id"] in module_ids:
                raise ValueError(
                    f"duplicate assessment module: {item['module_id']}"
                )
            question_ids.add(item["id"])
            module_ids.add(item["module_id"])

    def _public(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "module_id": item["module_id"],
            "question": item["question"],
            "choices": list(item["choices"]),
            "bank_sha256": self.bank_sha256,
        }

    def question(self, module_id: str) -> dict[str, Any]:
        if module_id not in self.by_module:
            raise ValueError(f"no assessment for {module_id}")
        return self._public(self.by_module[module_id])

    def grade(self, question_id: str, answer_index: int) -> dict[str, Any]:
        if question_id not in self.questions:
            raise ValueError("unknown question id")
        item = self.questions[question_id]
        if type(answer_index) is not int or not 0 <= answer_index < len(item["choices"]):
            raise ValueError("answer_index is outside the available choices")
        correct = answer_index == item["correct_index"]
        return {
            "question_id": question_id,
            "module_id": item["module_id"],
            "correct": correct,
            "answer_index": answer_index,
            "correct_index": item["correct_index"],
            "explanation": item["explanation"],
            "bank_sha256": self.bank_sha256,
        }
