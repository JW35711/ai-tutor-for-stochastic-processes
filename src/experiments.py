"""Notebook-derived experiment discovery for the Tutor.

The JSON registry is the source of truth for experiment names, notebook
provenance and teaching context.  This module only selects an existing entry;
it never creates a simulation or invents a tool name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "notebook_experiments.json"


_QUERY_ALIASES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("waiting", "interarrival", "first arrival", "exponential waiting"), ("m01-geometric-waiting-time",)),
    (("poisson", "sample path", "arrival path", "counting path"), ("m01-poisson-process",)),
    (("brownian", "variance", "terminal distribution", "normal distribution"), ("m04-terminal-distribution",)),
    (("brownian", "sample path", "path", "increment"), ("m04-brownian-increments",)),
    (("pagerank", "page rank", "web page", "webpage"), ("m05-stationary-distribution",)),
    (("thinning", "accepted", "rejected", "intensity"), ("m08-thinning",)),
    (("self-avoiding", "self avoiding", "obstacle", "blocked", "trap"), ("m09-self-avoidance", "m09-path-trapping")),
    (("coalescence time", "coalescing time", "merge time"), ("m10-coalescence-time",)),
)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9-]{2,}", value.lower()))


class ExperimentRegistry:
    """Read-only index over the 74 notebook experiment records."""

    def __init__(self, path: Path = REGISTRY_PATH) -> None:
        payload = json.loads(path.read_text("utf-8"))
        experiments = payload.get("experiments")
        if not isinstance(experiments, list) or not experiments:
            raise ValueError("experiment registry must contain experiments")
        self.path = path
        self.payload = payload
        self.experiments: tuple[dict[str, Any], ...] = tuple(
            dict(item) for item in experiments
        )
        self.by_id = {str(item["experiment_id"]): item for item in self.experiments}
        if len(self.by_id) != len(self.experiments):
            raise ValueError("experiment IDs must be unique")

    def get(self, experiment_id: str | None) -> dict[str, Any] | None:
        return self.by_id.get(str(experiment_id)) if experiment_id else None

    @staticmethod
    def _clean_title(title: str) -> str:
        return re.sub(r"^(?:Example|Task|Solution)\s+[^:]*:\s*", "", title).strip() or title

    def _score(self, item: dict[str, Any], query: str, concept_id: str | None, module_id: str | None) -> int:
        lowered = query.lower()
        score = 0
        if module_id and item.get("module_id") == module_id:
            score += 30
        if concept_id and item.get("concept_id") == concept_id:
            score += 100
        title = str(item.get("title", ""))
        purpose = " ".join(
            str(item.get(key, ""))
            for key in ("section", "title", "teaching_purpose", "expected_observation", "theory_connection")
        )
        title_tokens = _tokens(title)
        score += min(30, 5 * len(_tokens(query) & title_tokens))
        if self._clean_title(title).lower() in lowered:
            score += 50
        for terms, concepts in _QUERY_ALIASES:
            if any(term in lowered for term in terms) and item.get("concept_id") in concepts:
                score += 80
        purpose_tokens = _tokens(purpose)
        score += min(20, 2 * len(_tokens(query) & purpose_tokens))
        # Prefer the first executable target for a broad module request.  The
        # registry preserves notebook order, which is the intended teaching order.
        if item.get("implementation_status") == "IMPLEMENTED":
            score += 3
        return score

    def find_experiments(
        self,
        *,
        module_id: str | None = None,
        concept_id: str | None = None,
        query: str = "",
        simulation_engine: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Return deterministic registry matches, strongest match first."""

        candidates = [
            item for item in self.experiments
            if (module_id is None or item.get("module_id") == module_id)
            and (concept_id is None or item.get("concept_id") == concept_id)
            and (simulation_engine is None or item.get("simulation_engine") == simulation_engine)
            and item.get("simulation_engine")
        ]
        if not candidates:
            return []
        ranked = sorted(
            enumerate(candidates),
            key=lambda pair: (-self._score(pair[1], query, concept_id, module_id), pair[0]),
        )
        return [item for _, item in ranked[: max(1, min(int(limit), 5))]]

    def summary(self, item: dict[str, Any], supported_parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Expose compact teaching metadata without dumping notebook prose."""

        return {
            "experiment_id": item["experiment_id"],
            "title": self._clean_title(str(item.get("title", "Experiment"))),
            "module_id": item.get("module_id"),
            "concept_id": item.get("concept_id"),
            "simulation_engine": item.get("simulation_engine"),
            "visualization_id": item.get("visualization_id"),
            "source_notebook": item.get("source_notebook"),
            "teaching_purpose": self._first_sentence(item.get("teaching_purpose")),
            "expected_observation": self._first_sentence(item.get("expected_observation")),
            "theory_connection": self._first_sentence(item.get("theory_connection")),
            "supported_parameters": supported_parameters or [],
        }

    @staticmethod
    def _first_sentence(value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0][:320]


__all__ = ["ExperimentRegistry", "REGISTRY_PATH"]
