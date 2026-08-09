"""Explainable teaching-agent roles layered over the state graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TeachingRole:
    role_id: str
    role_name: str
    responsibility: str


ROLE_BY_NODE: dict[str, TeachingRole] = {
    "classify": TeachingRole(
        "curriculum_agent",
        "Curriculum Agent",
        "route the learner question to one approved course module",
    ),
    "retrieve": TeachingRole(
        "content_agent",
        "Content Agent",
        "retrieve notebook and lecture-note evidence inside the routed module",
    ),
    "plan": TeachingRole(
        "simulation_planner",
        "Simulation Planner",
        "choose the bounded tool and parse numerical parameters",
    ),
    "tool": TeachingRole(
        "simulation_agent",
        "Simulation Agent",
        "run the validated stochastic-process computation",
    ),
    "diagnose": TeachingRole(
        "assessment_agent",
        "Assessment Agent",
        "detect explicitly stated misconceptions with transparent rules",
    ),
    "memory": TeachingRole(
        "learner_model_agent",
        "Learner Model Agent",
        "update persistent practice evidence and next-step recommendation",
    ),
    "respond": TeachingRole(
        "tutor_agent",
        "Tutor Agent",
        "compose a grounded teaching response from verified evidence",
    ),
}


def build_team_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach stable educational role metadata to workflow trace entries."""

    team_trace: list[dict[str, Any]] = []
    for item in trace:
        role = ROLE_BY_NODE.get(
            str(item.get("node", "")),
            TeachingRole(
                "unknown_agent",
                "Unknown Agent",
                "handle an undeclared workflow step",
            ),
        )
        team_trace.append(
            {
                "node": item.get("node"),
                "role_id": role.role_id,
                "role_name": role.role_name,
                "responsibility": role.responsibility,
                "status": item.get("status"),
                "detail": item.get("detail"),
                "duration_ms": item.get("duration_ms"),
            }
        )
    return team_trace
