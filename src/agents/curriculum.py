"""Deterministic, knowledge-point-level curriculum policy."""

from __future__ import annotations

from typing import Any

from .contracts import CurriculumDecision
from ..mastery import LEARNING, MASTERED, NEEDS_REVIEW, NOT_STARTED


class CurriculumAgent:
    """Recommend a catalog-backed next action from assessed KP evidence only."""

    ACTIONS = {
        "LEARN", "CONTINUE", "PRACTICE", "REVIEW", "REVIEW_PREREQUISITE",
        "QUIZ", "SIMULATE", "ADVANCE",
    }

    def __init__(self, curriculum: dict[str, Any]) -> None:
        self.curriculum = curriculum
        self.modules = list(curriculum.get("modules", []))
        self.concepts = {
            point["id"]: {**point, "module_id": module["module_id"]}
            for module in self.modules
            for point in module.get("knowledge_points", [])
        }

    def _mastery(self, profile: dict[str, Any], concept_id: str) -> dict[str, Any]:
        return next(
            (item for item in profile.get("knowledge_points", []) if item.get("concept_id") == concept_id),
            {"concept_id": concept_id, "mastery_score": 0.0, "attempt_count": 0, "correct_count": 0,
             "hint_count": 0, "recent_misconceptions": [], "status": NOT_STARTED},
        )

    @staticmethod
    def _mode(status: str, misconceptions: list[Any], attempts: int) -> str:
        if status == NEEDS_REVIEW or misconceptions:
            return "REVIEW"
        if status == MASTERED:
            return "ADVANCED"
        if status == LEARNING or attempts:
            return "DEVELOPING"
        return "FOUNDATION"

    def decide(
        self,
        *,
        current_module_id: str | None = None,
        current_concept_id: str | None = None,
        requested_topic: str | None = None,
        profile: dict[str, Any] | None = None,
        recent_mistakes: list[dict[str, Any]] | None = None,
        learning_mode: str = "concept",
    ) -> CurriculumDecision:
        profile = profile or {}
        recent_mistakes = recent_mistakes or []
        point = self.concepts.get(current_concept_id or "")
        module = next((item for item in self.modules if item["module_id"] == current_module_id), None)
        if point is None and module:
            first = (module.get("knowledge_points") or [None])[0]
            point = {**first, "module_id": current_module_id} if first else None
        if point is None:
            first_module = module or (self.modules[0] if self.modules else None)
            first = (first_module or {}).get("knowledge_points", [None])[0]
            target = first["id"] if first else None
            return CurriculumDecision(
                target_concept=target, next_concept=target,
                recommended_action="learn" if target else "continue_current_concept",
                decision_type="LEARN", teaching_mode="FOUNDATION",
                decision_reason="No assessed knowledge-point evidence exists yet.",
                reason="Start with the first knowledge point in the backend curriculum." if target else "No curriculum point is available.",
                module_id=(first_module or {}).get("module_id"),
            )

        concept_id = str(point["id"])
        module_id = str(point["module_id"])
        prerequisites = tuple(point.get("prerequisites", []))
        current = self._mastery(profile, concept_id)
        # Compatibility for older callers that only supplied module aggregates;
        # runtime learner profiles always include knowledge_points.
        if not profile.get("knowledge_points"):
            module_evidence = next((item for item in profile.get("modules", []) if item.get("module_id") == module_id), {})
            if recent_mistakes and prerequisites:
                return CurriculumDecision(
                    target_concept=prerequisites[0], prerequisite_concepts=prerequisites,
                    recommended_action="review_prerequisite", reason="Review the prerequisite before returning to the current concept.",
                    next_concept=concept_id, module_id=module_id, decision_type="REVIEW_PREREQUISITE",
                    teaching_mode="REVIEW", decision_reason="Recent assessed evidence needs prerequisite review.",
                )
            if float(module_evidence.get("mastery", 0.0)) >= 0.8:
                ordered = module.get("knowledge_points", []) if module else []
                ids = [item["id"] for item in ordered]
                index = ids.index(concept_id) if concept_id in ids else -1
                next_id = ids[index + 1] if index >= 0 and index + 1 < len(ids) else None
                return CurriculumDecision(
                    target_concept=concept_id, prerequisite_concepts=prerequisites,
                    recommended_action="continue_current_concept", reason="Continue with the selected course concept.",
                    next_concept=next_id, module_id=module_id, decision_type="CONTINUE",
                    teaching_mode="ADVANCED", decision_reason="Legacy module evidence indicates strong progress.",
                )
        status = str(current.get("status") or NOT_STARTED)
        attempts = int(current.get("attempt_count", 0) or 0)
        misconceptions = list(current.get("recent_misconceptions") or [])
        weak_prerequisite = None
        for prerequisite in prerequisites:
            evidence = self._mastery(profile, prerequisite)
            if int(evidence.get("attempt_count", 0) or 0) > 0 and str(evidence.get("status")) in {NEEDS_REVIEW, LEARNING}:
                weak_prerequisite = prerequisite
                break
        mode = self._mode(status, misconceptions, attempts)
        if weak_prerequisite and learning_mode not in {"explicit_question", "concept"}:
            action, decision_type, target = "review_prerequisite", "REVIEW_PREREQUISITE", weak_prerequisite
            reason = "An assessed prerequisite needs review before this knowledge point."
        elif status == NOT_STARTED:
            action, decision_type, target = "learn", "LEARN", concept_id
            reason = "This knowledge point has no assessed evidence yet."
        elif status == NEEDS_REVIEW or recent_mistakes or misconceptions:
            action, decision_type, target = "review_current_concept", "REVIEW", concept_id
            reason = "Recent assessed evidence shows a misconception or a need for review."
        elif status == LEARNING:
            action, decision_type, target = ("quiz", "QUIZ", concept_id) if attempts >= 2 else ("practice", "PRACTICE", concept_id)
            reason = "Build more assessed evidence for this knowledge point."
        else:
            ordered = module.get("knowledge_points", []) if module else []
            ids = [item["id"] for item in ordered]
            index = ids.index(concept_id) if concept_id in ids else -1
            next_id = ids[index + 1] if index >= 0 and index + 1 < len(ids) else None
            action, decision_type, target = ("move_to_next_concept", "ADVANCE", next_id or concept_id)
            reason = "This knowledge point is mastered; continue to the next point." if next_id else "This is the final knowledge point in the module."
            return CurriculumDecision(
                target_concept=target, prerequisite_concepts=prerequisites,
                recommended_action=action, reason=reason, next_concept=next_id,
                module_id=module_id, decision_type=decision_type,
                teaching_mode="ADVANCED", decision_reason=reason,
            )
        return CurriculumDecision(
            target_concept=target, prerequisite_concepts=prerequisites,
            recommended_action=action, reason=reason, next_concept=concept_id,
            module_id=module_id, decision_type=decision_type,
            teaching_mode=mode, decision_reason=reason,
        )

    def recommend(self, profile: dict[str, Any] | None = None) -> CurriculumDecision:
        """Choose the first actionable KP in course order from assessed state."""

        profile = profile or {}
        for module in self.modules:
            for point in module.get("knowledge_points", []):
                evidence = self._mastery(profile, point["id"])
                status = str(evidence.get("status") or NOT_STARTED)
                if status in {NEEDS_REVIEW, NOT_STARTED, LEARNING}:
                    return self.decide(
                        current_module_id=module["module_id"],
                        current_concept_id=point["id"],
                        profile=profile,
                        learning_mode="recommendation",
                    )
        last_module = self.modules[-1] if self.modules else None
        last_point = (last_module or {}).get("knowledge_points", [None])[-1]
        return self.decide(
            current_module_id=(last_module or {}).get("module_id"),
            current_concept_id=(last_point or {}).get("id"),
            profile=profile,
            learning_mode="recommendation",
        )
