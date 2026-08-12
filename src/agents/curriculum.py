"""Deterministic curriculum progression agent."""

from __future__ import annotations

from typing import Any

from .contracts import CurriculumDecision


class CurriculumAgent:
    """Decide what to study next using only the backend curriculum and mastery."""

    def __init__(self, curriculum: dict[str, Any]) -> None:
        self.curriculum = curriculum
        self.modules = list(curriculum.get("modules", []))
        self.concepts = {
            point["id"]: {**point, "module_id": module["module_id"]}
            for module in self.modules
            for point in module.get("knowledge_points", [])
        }

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
        """Return a bounded recommendation; never invent a course concept."""

        profile = profile or {}
        recent_mistakes = recent_mistakes or []
        point = self.concepts.get(current_concept_id or "")
        module = next(
            (item for item in self.modules if item["module_id"] == current_module_id),
            None,
        )
        if point is None and module is not None:
            point = module.get("knowledge_points", [None])[0]
            if point is not None:
                point = {**point, "module_id": current_module_id}

        if point is not None:
            prerequisites = tuple(point.get("prerequisites", []))
            module_id = str(point["module_id"])
            module_profile = next(
                (
                    item
                    for item in profile.get("modules", [])
                    if item.get("module_id") == module_id
                ),
                {},
            )
            weak = float(module_profile.get("mastery", 0.0)) < 0.55
            if recent_mistakes or learning_mode in {"hint", "review", "practice"} or weak:
                target = prerequisites[0] if recent_mistakes and prerequisites else point["id"]
                action = "review_prerequisite" if target != point["id"] else "review_current_concept"
                reason = (
                    "Review the prerequisite before returning to the current concept."
                    if target != point["id"]
                    else "Practice evidence is still limited for the current concept."
                )
                return CurriculumDecision(
                    target_concept=target,
                    prerequisite_concepts=prerequisites,
                    recommended_action=action,
                    reason=reason,
                    next_concept=point["id"],
                    module_id=module_id,
                )

            ordered = module.get("knowledge_points", []) if module else []
            ids = [item["id"] for item in ordered]
            try:
                next_index = ids.index(point["id"]) + 1
            except ValueError:
                next_index = len(ids)
            next_id = ids[next_index] if next_index < len(ids) else None
            return CurriculumDecision(
                target_concept=point["id"],
                prerequisite_concepts=prerequisites,
                recommended_action="continue_current_concept",
                reason="Continue with the selected course concept.",
                next_concept=next_id,
                module_id=module_id,
            )

        first_module = module or (self.modules[0] if self.modules else None)
        first_point = (first_module or {}).get("knowledge_points", [None])[0]
        target = first_point["id"] if first_point else None
        return CurriculumDecision(
            target_concept=target,
            recommended_action="move_to_next_concept" if target else "continue_current_concept",
            reason=(
                "Start with the first knowledge point in the backend curriculum."
                if target
                else "No curriculum point is available for this request."
            ),
            next_concept=target,
            module_id=(first_module or {}).get("module_id"),
        )

