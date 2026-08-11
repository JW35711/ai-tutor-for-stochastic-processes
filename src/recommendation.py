"""Transparent next-step recommendations from the learner practice profile."""

from __future__ import annotations

from typing import Any

from .module_registry import MODULES


PRACTICE_PROMPTS: dict[str, str] = {
    "module00": "Estimate π with 10000 samples and explain how the error changes as sample size grows",
    "module01": "Compare Bernoulli waiting times with Poisson-process waiting times",
    "module02": "Change the up-step probability and predict the direction of the endpoint mean",
    "module03": "Change the jump rate and compare jump counts in a continuous-time random walk",
    "module04": "Predict the variance of B(T), then verify it with a Brownian-motion simulation",
    "module05": "Simulate a Markov chain and compare empirical frequencies with a stationary distribution",
    "module06": "Change the failure rate and predict the long-run probability of the up state",
    "module07": "Change the M/M/1 arrival rate and explain the stability boundary",
    "module08": "Change the peak intensity and predict the nonhomogeneous Poisson count mean",
    "module09": "Compare the stopping mechanisms of an ordinary and a self-avoiding walk",
    "module10": "Change the initial particle count and compare coalescence-time distributions",
}


def _review_interval_days(module: dict[str, Any] | None) -> int:
    """Small SM-2-inspired interval policy from local evidence only."""

    if not module:
        return 1
    mastery = float(module.get("mastery", 0.0))
    quiz_attempts = int(module.get("quiz_attempts", 0))
    if quiz_attempts == 0 or mastery < 0.55:
        return 1
    if mastery < 0.8:
        return 3
    return 7


def recommend_next(profile: dict[str, Any]) -> dict[str, str]:
    """Return one explainable practice suggestion without claiming ability."""

    modules = {item["module_id"]: item for item in profile.get("modules", [])}
    if not modules:
        target = MODULES[0]
        selected_module = None
        reason_code = "start_foundation"
        reason = "There is no practice record yet. Start with Monte Carlo to learn repeated sampling and theoretical comparison."
    else:
        needs_evidence = sorted(
            (
                item
                for item in modules.values()
                if item.get("mastery", 0.0) < 0.55
                or item.get("quiz_attempts", 0) == 0
            ),
            key=lambda item: (
                item.get("mastery", 0.0),
                item.get("quiz_attempts", 0),
                item["module_id"],
            ),
        )
        if needs_evidence:
            selected = needs_evidence[0]
            selected_module = selected
            target = next(
                module for module in MODULES if module.module_id == selected["module_id"]
            )
            reason_code = "strengthen_evidence"
            if selected.get("quiz_attempts", 0) == 0:
                reason = "This module has a simulation record but no concept evidence yet; predict first, then verify."
            else:
                reason = "Practice evidence for this module is still limited; change one parameter and explain the direction of change."
        else:
            uncovered = [module for module in MODULES if module.module_id not in modules]
            if uncovered:
                target = uncovered[0]
                selected_module = modules.get(target.module_id)
                reason_code = "expand_coverage"
                reason = "Evidence for practiced modules is fairly complete; continue in course order to the next model."
            else:
                selected = min(
                    modules.values(),
                    key=lambda item: (item.get("mastery", 0.0), item["module_id"]),
                )
                selected_module = selected
                target = next(
                    module
                    for module in MODULES
                    if module.module_id == selected["module_id"]
                )
                reason_code = "boundary_challenge"
                reason = "Every module has a record; next, test a boundary case or a model assumption."
    return {
        "module_id": target.module_id,
        "module_label": target.label,
        "reason_code": reason_code,
        "reason": reason,
        "suggested_question": PRACTICE_PROMPTS[target.module_id],
        "review_interval_days": str(_review_interval_days(selected_module)),
    }
