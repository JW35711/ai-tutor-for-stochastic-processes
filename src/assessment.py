"""Concept-check engine for adaptive module assessment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_QUIZ_PATH = Path(__file__).resolve().parent.parent / "data" / "quizzes.json"
DEFAULT_CURRICULUM_PATH = Path(__file__).resolve().parent.parent / "data" / "curriculum.json"


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
        self.by_module = {}
        for item in questions:
            self.by_module.setdefault(item["module_id"], item)
        curriculum = json.loads(DEFAULT_CURRICULUM_PATH.read_text("utf-8"))
        self.concepts = {
            point["id"]: {**point, "module_id": module["module_id"]}
            for module in curriculum["modules"]
            for point in module["knowledge_points"]
        }
        generated: list[dict[str, Any]] = []
        for concept_id, point in self.concepts.items():
            if concept_id in {item.get("concept_id") for item in questions}:
                continue
            generated.append(
                {
                    "id": f"kp-{concept_id}",
                    "module_id": point["module_id"],
                    "concept_id": concept_id,
                    "question_type": "free_text",
                    "difficulty": "core",
                    "hint_levels": [f"Focus on the defining relationship in {point['title']}."],
                    "question": point["practice_prompt"],
                    "expected_answer": point["summary"],
                    "choices": [],
                    "correct_index": 0,
                    "explanation": point["summary"],
                }
            )
        self.questions.update({item["id"]: item for item in generated})
        # The hash remains the reviewed source-bank hash; generated KP prompts
        # are deterministic projections of curriculum.json and are not hidden
        # content versions.
        self.by_concept = {item["concept_id"]: item for item in self.questions.values() if item.get("concept_id")}

    @staticmethod
    def _validate_bank(questions: object) -> None:
        if not isinstance(questions, list) or not questions:
            raise ValueError("assessment bank must be a non-empty JSON list")

        question_ids: set[str] = set()
        module_ids: set[str] = set()
        curriculum_path = Path(__file__).resolve().parent.parent / "data" / "curriculum.json"
        curriculum = json.loads(curriculum_path.read_text("utf-8"))
        concept_modules = {
            point["id"]: module["module_id"]
            for module in curriculum["modules"]
            for point in module["knowledge_points"]
        }
        required = {
            "id",
            "module_id",
            "question",
            "choices",
            "correct_index",
            "explanation",
        }
        for position, item in enumerate(questions):
            if not isinstance(item, dict) or not required.issubset(item):
                raise ValueError(
                    f"assessment item {position} must contain {sorted(required)}"
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
            if item["module_id"] not in {f"module{i:02d}" for i in range(11)}:
                raise ValueError(f"invalid assessment module: {item['module_id']}")
            if item.get("concept_id") is not None and item["concept_id"] not in concept_modules:
                raise ValueError(f"assessment item {position} has orphan concept_id")
            if item.get("concept_id") is not None and concept_modules[item["concept_id"]] != item["module_id"]:
                raise ValueError(f"assessment item {position} concept/module mismatch")
            question_ids.add(item["id"])
            if item["module_id"] in module_ids:
                raise ValueError(f"duplicate assessment module: {item['module_id']}")
            module_ids.add(item["module_id"])

    def _public(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "module_id": item["module_id"],
            "concept_id": item.get("concept_id"),
            "question": item["question"],
            "choices": list(item["choices"]),
            "question_type": item.get("question_type", "multiple_choice"),
            "difficulty": item.get("difficulty", "core"),
            "hint_levels": list(item.get("hint_levels", [])),
            "bank_sha256": self.bank_sha256,
        }

    def question(self, module_id: str) -> dict[str, Any]:
        if module_id not in self.by_module:
            raise ValueError(f"no assessment for {module_id}")
        return self._public(self.by_module[module_id])

    def question_for_concept(self, concept_id: str) -> dict[str, Any]:
        item = self.by_concept.get(concept_id)
        if item is None:
            raise ValueError(f"no assessment for {concept_id}")
        return self._public(item)

    def hint(self, *, concept_id: str, question_id: str | None = None, hint_level: int = 1) -> dict[str, Any]:
        item = self.questions.get(question_id or "") or self.by_concept.get(concept_id)
        if item is None or item.get("concept_id") != concept_id:
            raise ValueError("unknown concept assessment")
        levels = list(item.get("hint_levels", []))
        if not levels:
            raise ValueError("no hint is available for this assessment")
        level = max(1, min(int(hint_level), len(levels)))
        return {"question_id": item["id"], "concept_id": concept_id, "hint_level": level, "hint": levels[level - 1]}

    def grade_free_text(self, question_id: str, student_answer: str) -> dict[str, Any]:
        item = self.questions.get(question_id)
        if item is None:
            raise ValueError("unknown question id")
        answer = str(student_answer or "").strip().lower()
        expected = str(item.get("expected_answer") or item["choices"][item["correct_index"]]).strip().lower()
        tokens = [token for token in expected.replace(".", " ").split() if len(token) > 1]
        correct = bool(answer) and (expected in answer or sum(token in answer for token in tokens) >= max(1, len(tokens) // 2))
        return {"question_id": item["id"], "module_id": item["module_id"], "concept_id": item.get("concept_id"), "correct": correct, "student_answer": student_answer, "expected_answer": expected, "explanation": item["explanation"], "bank_sha256": self.bank_sha256}

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
            "concept_id": item.get("concept_id"),
            "correct": correct,
            "answer_index": answer_index,
            "correct_index": item["correct_index"],
            "explanation": item["explanation"],
            "bank_sha256": self.bank_sha256,
        }
