"""Rule-based misconception diagnosis and adaptive teaching prompts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MisconceptionRule:
    code: str
    module_id: str | None
    triggers: tuple[str, ...]
    explanation: str
    correction: str


RULES: tuple[MisconceptionRule, ...] = (
    MisconceptionRule(
        "simulation_must_repeat_exactly",
        None,
        ("每次必须一样", "每次都一样", "结果完全一样", "固定结果"),
        "Confuses statistical reproducibility with producing the same random path every time.",
        "Without a fixed seed, individual paths change; with enough samples, the statistical pattern should remain stable.",
    ),
    MisconceptionRule(
        "poisson_mean_rate_only",
        "module01",
        ("均值就是lambda", "均值就是λ", "mean is lambda"),
        "Ignores the observation-interval length when interpreting a Poisson count.",
        "Over an interval of length T, both the mean and variance of N(T) are λT.",
    ),
    MisconceptionRule(
        "brownian_variance_sqrt_t",
        "module04",
        ("方差是根号t", "方差为根号t", "variance is sqrt"),
        "Confuses the standard deviation of Brownian motion with its variance.",
        "B(T) has variance T; its standard deviation is √T.",
    ),
    MisconceptionRule(
        "markov_requires_independence",
        "module05",
        ("马尔可夫链每步独立", "markov states are independent", "状态相互独立"),
        "Confuses the Markov property with independence across all time points.",
        "The next state may depend on the current state; the property excludes earlier history once the current state is given.",
    ),
    MisconceptionRule(
        "mm1_stable_at_equality",
        "module07",
        ("lambda等于mu也稳定", "λ=μ稳定", "到达率等于服务率也稳定"),
        "Mistakes zero drift for the existence of a stationary queue-length distribution.",
        "An M/M/1 queue has a geometric stationary distribution only when λ<μ.",
    ),
    MisconceptionRule(
        "saw_position_is_markov",
        "module09",
        ("只看当前位置", "当前位置就够", "position alone is markov"),
        "Ignores how the visited set changes the available moves of a self-avoiding walk.",
        "With only the current position as the state, the process is usually not Markov; including the visited set restores a Markov description.",
    ),
)


def diagnose(question: str, module_id: str) -> list[dict[str, str]]:
    """Return transparent diagnoses only when the learner states a trigger."""

    normalized = question.lower().replace(" ", "")
    findings: list[dict[str, str]] = []
    for rule in RULES:
        if rule.module_id not in {None, module_id}:
            continue
        if any(trigger.lower().replace(" ", "") in normalized for trigger in rule.triggers):
            findings.append(
                {
                    "code": rule.code,
                    "explanation": rule.explanation,
                    "correction": rule.correction,
                }
            )
    return findings


def adaptive_note(profile: dict[str, object], module_id: str) -> str:
    """Describe why the next prompt is chosen, without overstating mastery."""

    modules = {
        item["module_id"]: item
        for item in profile.get("modules", [])  # type: ignore[union-attr]
    }
    current = modules.get(module_id)
    if not current:
        return "This is your first practice run for this module. We will connect the simulation with one core theoretical quantity."
    attempts = current["attempts"]
    if attempts <= 1:
        return "You are just starting this module. Next, change one parameter and predict the direction of the change."
    if current["mastery"] < 0.55:
        return "You have run this module, but the practice evidence is still limited. Explain the theoretical value before the next simulation."
    return "You have run this module several times. Next, compare a boundary case or test a model assumption."
