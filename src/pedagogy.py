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
        "把统计可复现性误解为每次都要产生同一条随机路径。",
        "不固定 seed 时单次结果会变化，但样本量足够大时统计规律应保持稳定。",
    ),
    MisconceptionRule(
        "poisson_mean_rate_only",
        "module01",
        ("均值就是lambda", "均值就是λ", "mean is lambda"),
        "忽略了观察区间长度对 Poisson 计数均值的影响。",
        "在长度为 T 的区间上，N(T) 的均值和方差都是 λT。",
    ),
    MisconceptionRule(
        "brownian_variance_sqrt_t",
        "module04",
        ("方差是根号t", "方差为根号t", "variance is sqrt"),
        "混淆了 Brownian motion 的标准差与方差。",
        "B(T) 的方差为 T，标准差才是 √T。",
    ),
    MisconceptionRule(
        "markov_requires_independence",
        "module05",
        ("马尔可夫链每步独立", "markov states are independent", "状态相互独立"),
        "把 Markov property 误解为不同时刻的状态相互独立。",
        "下一状态可以依赖当前状态；Markov property 排除的是给定当前状态后的更早历史。",
    ),
    MisconceptionRule(
        "mm1_stable_at_equality",
        "module07",
        ("lambda等于mu也稳定", "λ=μ稳定", "到达率等于服务率也稳定"),
        "把零漂移误认为存在平稳队长分布。",
        "M/M/1 队列只有在 λ<μ 时正再生并具有几何平稳分布。",
    ),
    MisconceptionRule(
        "saw_position_is_markov",
        "module09",
        ("只看当前位置", "当前位置就够", "position alone is markov"),
        "忽略了已访问集合对 self-avoiding walk 可选动作的影响。",
        "若状态只写当前位置，过程通常不是 Markov；把 visited set 纳入状态后才可恢复 Markov 描述。",
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
        return "这是你第一次练习该模块，我会先连接仿真结果与一个核心理论量。"
    attempts = current["attempts"]
    if attempts <= 1:
        return "你刚开始练习该模块，下一步适合先改变一个参数并预测方向。"
    if current["mastery"] < 0.55:
        return "你已经运行过该模块，但练习证据还不充分；建议先解释理论值再看下一次仿真。"
    return "你已多次成功运行该模块，下一步适合比较边界情形或检验模型假设。"

