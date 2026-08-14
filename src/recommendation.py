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

PRACTICE_PROMPTS_LOCALIZED: dict[str, dict[str, str]] = {
    "zh": {
        module_id: prompt for module_id, prompt in {
            "module00": "用 10000 个样本估计 π，并解释样本量增加时误差如何变化",
            "module01": "比较伯努利等待时间与泊松过程等待时间",
            "module02": "改变向上步概率，预测终点均值的变化方向",
            "module03": "改变跳跃率，比较连续时间随机游走中的跳跃次数",
            "module04": "预测 B(T) 的方差，然后用布朗运动模拟验证",
            "module05": "模拟马尔可夫链，并将经验频率与平稳分布比较",
            "module06": "改变故障率，预测正常状态的长期概率",
            "module07": "改变 M/M/1 到达率并解释稳定性边界",
            "module08": "改变峰值强度，预测非齐次泊松计数均值",
            "module09": "比较普通随机游走与自避免游走的停止机制",
            "module10": "改变初始粒子数，比较合并时间分布",
        }.items()
    },
    "sv": {
        module_id: prompt for module_id, prompt in {
            "module00": "Skatta π med 10000 stickprov och förklara hur felet ändras när stickprovsstorleken ökar",
            "module01": "Jämför väntetider i Bernoulliförsök med väntetider i en Poissonprocess",
            "module02": "Ändra sannolikheten för ett uppsteg och förutsäg riktningen för slutpunktens medelvärde",
            "module03": "Ändra hoppintensiteten och jämför antalet hopp i en kontinuerlig random walk",
            "module04": "Förutsäg variansen för B(T) och kontrollera den med en Brownsk simulering",
            "module05": "Simulera en Markovkedja och jämför empiriska frekvenser med en stationär fördelning",
            "module06": "Ändra felfrekvensen och förutsäg den långsiktiga sannolikheten för upp-tillståndet",
            "module07": "Ändra ankomstintensiteten i M/M/1 och förklara stabilitetsgränsen",
            "module08": "Ändra toppintensiteten och förutsäg medelantalet i en icke-homogen Poissonprocess",
            "module09": "Jämför stoppmekanismerna för en vanlig och en självundvikande vandring",
            "module10": "Ändra det ursprungliga partikelantalet och jämför koalescenstidernas fördelningar",
        }.items()
    },
}

REASONS_LOCALIZED: dict[str, dict[str, str]] = {
    "zh": {
        "start_foundation": "还没有练习记录。先从蒙特卡洛开始，学习重复抽样和理论比较。",
        "strengthen_evidence": "这个模块的练习证据仍然有限；改变一个参数并解释变化方向。",
        "expand_coverage": "已练习模块的证据较完整；按课程顺序继续学习下一个模型。",
        "boundary_challenge": "每个模块都有记录；下一步尝试边界情形或检验模型假设。",
    },
    "sv": {
        "start_foundation": "Det finns ännu ingen övningshistorik. Börja med Monte Carlo och lär dig upprepad sampling och teoretisk jämförelse.",
        "strengthen_evidence": "Övningsunderlaget för denna modul är fortfarande begränsat; ändra en parameter och förklara förändringens riktning.",
        "expand_coverage": "Underlaget för de övade modulerna är ganska komplett; fortsätt i kursordning till nästa modell.",
        "boundary_challenge": "Alla moduler har en studiepost; prova nu ett gränsfall eller en modellförutsägelse.",
    },
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


def recommend_next(profile: dict[str, Any], language: str = "en") -> dict[str, str]:
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
    localized_prompt = PRACTICE_PROMPTS_LOCALIZED.get(language, {}).get(target.module_id, PRACTICE_PROMPTS[target.module_id])
    localized_reason = REASONS_LOCALIZED.get(language, {}).get(reason_code, reason)
    return {
        "module_id": target.module_id,
        "module_label": target.label,
        "reason_code": reason_code,
        "reason": localized_reason,
        "suggested_question": localized_prompt,
        "review_interval_days": str(_review_interval_days(selected_module)),
    }


def recommend_next_knowledge_point(curriculum_agent: Any, profile: dict[str, Any], language: str = "en", decision: Any | None = None) -> dict[str, Any]:
    """Return a catalog-backed KP recommendation for Overview/Progress.

    This is intentionally separate from the legacy module recommendation
    contract.  Module mastery remains a display aggregate; this payload is
    driven by assessed ``knowledge_points`` evidence.
    """

    decision = decision or curriculum_agent.recommend(profile)
    target_id = decision.target_concept
    point = curriculum_agent.concepts.get(target_id or "")
    module = next((item for item in curriculum_agent.modules if item["module_id"] == decision.module_id), None)
    if point is None and module:
        point = next((item for item in module.get("knowledge_points", []) if item["id"] == target_id), None)
    action_labels = {
        "zh": {"LEARN": "学习", "PRACTICE": "练习", "REVIEW": "复习", "REVIEW_PREREQUISITE": "复习先修知识点", "QUIZ": "测验", "ADVANCE": "继续下一个知识点"},
        "sv": {"LEARN": "Lär dig", "PRACTICE": "Öva", "REVIEW": "Repetera", "REVIEW_PREREQUISITE": "Repetera förkunskapen", "QUIZ": "Quiz", "ADVANCE": "Fortsätt till nästa kunskapspunkt"},
    }
    reason_labels = {
        "zh": {
            "LEARN": "这个知识点还没有经过评估的证据。",
            "PRACTICE": "继续通过练习积累这个知识点的证据。",
            "REVIEW": "最近的评估显示需要复习这个知识点。",
            "REVIEW_PREREQUISITE": "一个已经评估过的先修知识点需要复习。",
            "QUIZ": "用一次测验检验这个知识点的理解。",
            "ADVANCE": "这个知识点已达到掌握状态，可以继续下一个知识点。",
        },
        "sv": {
            "LEARN": "Den här kunskapspunkten har ännu inga bedömda bevis.",
            "PRACTICE": "Bygg mer evidens för kunskapspunkten genom övning.",
            "REVIEW": "Den senaste bedömningen visar att kunskapspunkten behöver repeteras.",
            "REVIEW_PREREQUISITE": "En bedömd förkunskap behöver repeteras.",
            "QUIZ": "Kontrollera förståelsen med ett quiz.",
            "ADVANCE": "Kunskapspunkten är etablerad; fortsätt till nästa.",
        },
    }
    action = action_labels.get(language, {}).get(decision.decision_type, decision.decision_type)
    payload = decision.to_dict()
    payload.update({
        "concept_id": target_id,
        "concept_title": (point or {}).get("title"),
        "module_label": next((item.label for item in MODULES if item.module_id == decision.module_id), decision.module_id),
        "action_label": action,
        "suggested_question": ((point or {}).get("practice_prompt", "") if language == "en" else (
            f"请练习：{(point or {}).get('title', target_id)}" if language == "zh" else
            f"Öva på: {(point or {}).get('title', target_id)}"
        )),
        "decision_reason": reason_labels.get(language, {}).get(decision.decision_type, decision.reason),
        "review_interval_days": "1" if decision.decision_type in {"LEARN", "REVIEW", "REVIEW_PREREQUISITE"} else "3",
    })
    return payload
