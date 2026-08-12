"""Validated, backend-owned curriculum metadata for the Tutor Lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .module_registry import MODULE_BY_ID
from .experiments import ExperimentRegistry


ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = ROOT / "data" / "curriculum.json"
SIMULATION_TOOLS = frozenset(
    {
        "monte_carlo",
        "bernoulli",
        "poisson",
        "random_walk",
        "continuous_random_walk",
        "brownian_motion",
        "markov_chain",
        "ctmc",
        "birth_death",
        "reliability",
        "buffer",
        "mm1_queue",
        "nhpp",
        "self_avoiding_walk",
        "coalescing_particles",
    }
)


def load_curriculum(path: Path = CURRICULUM_PATH) -> dict[str, Any]:
    """Load curriculum data and reject incomplete or dangling references."""

    payload = json.loads(path.read_text("utf-8"))
    if payload.get("course_title") is not None and not isinstance(payload["course_title"], str):
        raise ValueError("curriculum course_title must be a string")
    modules = payload.get("modules")
    if not isinstance(modules, list):
        raise ValueError("curriculum modules must be a list")
    module_ids = [item.get("module_id") for item in modules if isinstance(item, dict)]
    if set(module_ids) != set(MODULE_BY_ID) or len(module_ids) != len(MODULE_BY_ID):
        raise ValueError("curriculum must cover module00 through module10 exactly once")

    concepts: dict[str, dict[str, Any]] = {}
    for module in modules:
        if not isinstance(module, dict):
            raise ValueError("each curriculum module must be an object")
        if module.get("purpose") is not None and not isinstance(module["purpose"], str):
            raise ValueError(f"{module['module_id']} purpose must be a string")
        objectives = module.get("learning_objectives", [])
        if objectives and (
            not isinstance(objectives, list)
            or not 2 <= len(objectives) <= 4
            or not all(isinstance(item, str) and item.strip() for item in objectives)
        ):
            raise ValueError(f"{module['module_id']} learning_objectives must contain 2 to 4 strings")
        points = module.get("knowledge_points")
        if not isinstance(points, list) or not 3 <= len(points) <= 8:
            raise ValueError(f"{module['module_id']} must contain 3 to 8 knowledge points")
        for point in points:
            if not isinstance(point, dict) or not isinstance(point.get("id"), str):
                raise ValueError("each knowledge point needs a string id")
            concept_id = point["id"]
            if concept_id in concepts:
                raise ValueError(f"duplicate knowledge point id: {concept_id}")
            for required in ("title", "summary", "practice_prompt", "source_refs"):
                if not point.get(required):
                    raise ValueError(f"{concept_id} is missing {required}")
            tool = point.get("simulation_tool")
            if tool is not None:
                if tool not in SIMULATION_TOOLS or not point.get("simulation_prompt"):
                    raise ValueError(f"{concept_id} has an invalid simulation mapping")
            concepts[concept_id] = point

    for concept_id, point in concepts.items():
        prerequisites = point.get("prerequisites", [])
        if not isinstance(prerequisites, list) or not all(
            item in concepts for item in prerequisites
        ):
            raise ValueError(f"{concept_id} has an invalid prerequisite")
    return payload


def curriculum_catalog() -> dict[str, Any]:
    """Return a fresh JSON-safe curriculum payload for the public API."""

    payload = json.loads(json.dumps(load_curriculum()))
    experiment_registry = ExperimentRegistry()
    payload["course_title"] = payload.get(
        "course_title", "Introduction to Stochastic Processes with Applications"
    )
    for module in payload["modules"]:
        spec = MODULE_BY_ID[module["module_id"]]
        purpose = module.get("purpose") or (
            f"Explore {spec.label.lower()} through definitions, practice questions, "
            "and verified simulations."
        )
        module["number"] = spec.number
        module["label"] = spec.label
        # ``summary`` remains for backward compatibility with older clients;
        # new student screens should prefer the explicit purpose field.
        module["purpose"] = purpose
        module["summary"] = purpose
        module["learning_objectives"] = module.get("learning_objectives") or [
            f"Explain {point['title'].lower()} in the context of this module."
            for point in module["knowledge_points"][:3]
        ]
        for point in module["knowledge_points"]:
            # Existing summaries are already concise student descriptions.
            point["description"] = point.get("description") or point["summary"]
            point["experiments"] = [
                {
                    "experiment_id": item["experiment_id"],
                    "title": experiment_registry._clean_title(str(item.get("title", "Experiment"))),
                    "simulation_engine": item.get("simulation_engine"),
                    "visualization_id": item.get("visualization_id"),
                }
                for item in experiment_registry.find_experiments(
                    module_id=module["module_id"], concept_id=point["id"], limit=5
                )
            ]
    return payload
