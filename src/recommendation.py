"""Transparent next-step recommendations from the learner practice profile."""

from __future__ import annotations

from typing import Any

from .module_registry import MODULES


PRACTICE_PROMPTS: dict[str, str] = {
    "module00": "用10000个样本估计π，并解释样本量增大后误差如何变化",
    "module01": "比较伯努利等待时间和泊松过程等待时间",
    "module02": "改变向上概率，预测随机游走终点均值的方向",
    "module03": "改变跳跃率，比较连续时间随机游走的跳跃次数",
    "module04": "先预测B(T)的方差，再用布朗运动仿真验证",
    "module05": "模拟马尔可夫链并比较经验分布与平稳分布",
    "module06": "改变故障率，预测连续时间链的平稳概率",
    "module07": "改变M/M/1到达率并解释稳定性边界",
    "module08": "改变峰值强度，预测非齐次泊松计数均值",
    "module09": "比较普通随机游走与自避免游走的停止机制",
    "module10": "改变初始粒子数，比较合并时间分布",
}


def recommend_next(profile: dict[str, Any]) -> dict[str, str]:
    """Return one explainable practice suggestion without claiming ability."""

    modules = {item["module_id"]: item for item in profile.get("modules", [])}
    if not modules:
        target = MODULES[0]
        reason_code = "start_foundation"
        reason = "还没有练习记录，先用 Monte Carlo 熟悉重复抽样和理论对照。"
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
            target = next(
                module for module in MODULES if module.module_id == selected["module_id"]
            )
            reason_code = "strengthen_evidence"
            if selected.get("quiz_attempts", 0) == 0:
                reason = "该模块已有仿真实践，但还没有概念题证据，适合先预测再验证。"
            else:
                reason = "该模块的练习证据仍较少，先改变一个参数并解释变化方向。"
        else:
            uncovered = [module for module in MODULES if module.module_id not in modules]
            if uncovered:
                target = uncovered[0]
                reason_code = "expand_coverage"
                reason = "已练习模块的证据较完整，可以按课程顺序扩展到下一个模型。"
            else:
                selected = min(
                    modules.values(),
                    key=lambda item: (item.get("mastery", 0.0), item["module_id"]),
                )
                target = next(
                    module
                    for module in MODULES
                    if module.module_id == selected["module_id"]
                )
                reason_code = "boundary_challenge"
                reason = "所有模块都已有记录，下一步适合检验边界情形和模型假设。"
    return {
        "module_id": target.module_id,
        "module_label": target.label,
        "reason_code": reason_code,
        "reason": reason,
        "suggested_question": PRACTICE_PROMPTS[target.module_id],
    }
