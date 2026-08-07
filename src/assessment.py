"""Concept-check engine for adaptive module assessment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_QUIZ_PATH = Path(__file__).resolve().parent.parent / "data" / "quizzes.json"


class AssessmentEngine:
    def __init__(self, path: Path = DEFAULT_QUIZ_PATH) -> None:
        questions: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
        self.questions = {item["id"]: item for item in questions}
        self.by_module = {item["module_id"]: item for item in questions}

    @staticmethod
    def _public(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "module_id": item["module_id"],
            "question": item["question"],
            "choices": item["choices"],
        }

    def question(self, module_id: str) -> dict[str, Any]:
        if module_id not in self.by_module:
            raise ValueError(f"no assessment for {module_id}")
        return self._public(self.by_module[module_id])

    def grade(self, question_id: str, answer_index: int) -> dict[str, Any]:
        if question_id not in self.questions:
            raise ValueError("unknown question id")
        item = self.questions[question_id]
        if not isinstance(answer_index, int) or not 0 <= answer_index < len(item["choices"]):
            raise ValueError("answer_index is outside the available choices")
        correct = answer_index == item["correct_index"]
        return {
            "question_id": question_id,
            "module_id": item["module_id"],
            "correct": correct,
            "answer_index": answer_index,
            "correct_index": item["correct_index"],
            "explanation": item["explanation"],
        }
