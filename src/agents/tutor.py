"""Tutor Agent policy: choose how to teach after evidence and assessment."""

from __future__ import annotations

from typing import Any, Callable

from .contracts import TutorContext
from ..messages import message


class TutorAgent:
    """Own answerability-aware teaching policy, not retrieval or computation."""

    def answer_concept(
        self,
        context: TutorContext,
        *,
        synthesise: Callable[[], str],
        partial: Callable[[], str],
        conflict: Callable[[], str],
        none: Callable[[], str],
        fallback: Callable[[], str],
    ) -> str:
        """Select a response policy before invoking the synthesis callback."""

        if context.answerability_status == "CONFLICT":
            return conflict()
        if context.answerability_status == "PARTIAL":
            return partial()
        if context.answerability_status == "NONE":
            return none()
        if context.sources:
            return synthesise()
        return fallback()

    def assessment_feedback(
        self,
        result: dict[str, Any],
        decision: dict[str, Any],
        *,
        language: str = "en",
    ) -> str:
        """Turn an assessment result into concise feedback, without rescoring it."""

        if result.get("correct") is True:
            next_concept = decision.get("next_concept")
            if language == "zh":
                return f"回答正确。可以继续学习下一个知识点（{next_concept}）。" if next_concept else "回答正确。保持这个推理方式，并尝试一个相近的应用。"
            if language == "sv":
                return f"Rätt. Du kan nu gå vidare mot nästa kunskapspunkt ({next_concept})." if next_concept else "Rätt. Behåll samma resonemang och prova en närliggande tillämpning."
            if next_concept:
                return (
                    "Correct. You can now move toward the next knowledge point "
                    f"({next_concept})."
                )
            return "Correct. Keep the same reasoning and try a nearby application."
        explanation = str(result.get("explanation") or "Review the worked concept and try again.")
        if language == "zh":
            return f"这份答案需要复习。{explanation} 在尝试更难的问题前，先复习推荐的先修知识点。"
        if language == "sv":
            return f"Detta svar behöver repeteras. {explanation} Repetera den rekommenderade förkunskapen innan du försöker med en svårare fråga."
        return f"This answer needs review. {explanation} Start with the recommended prerequisite before attempting a harder question."

    def simulation_feedback(
        self,
        *,
        verified: bool,
        result_summary: str,
        module_label: str,
        guiding_question: str,
        error: str | None = None,
        corrections: list[str] | None = None,
        response_language: str = "en",
    ) -> str:
        """Explain immutable Python output without recalculating its numbers."""

        if verified:
            if response_language == "zh":
                localized_label = {
                    "Monte Carlo simulation": "蒙特卡洛模拟",
                    "Bernoulli and Poisson processes": "伯努利与泊松过程",
                    "Brownian motion": "布朗运动",
                    "Discrete-time random walk": "离散时间随机游走",
                    "Continuous-time random walk": "连续时间随机游走",
                }.get(module_label, module_label)
                answer = f"## 结果\n{result_summary}\n\n## 含义\n这个实验展示了{localized_label}，并将经验输出与相应理论进行比较。\n\n## 下一步\n{guiding_question}"
            elif response_language == "sv":
                localized_label = {
                    "Monte Carlo simulation": "Monte Carlo-simulering",
                    "Bernoulli and Poisson processes": "Bernoulli- och Poissonprocesser",
                    "Brownian motion": "Brownsk rörelse",
                    "Discrete-time random walk": "diskret-tids random walk",
                    "Continuous-time random walk": "kontinuerlig-tids random walk",
                }.get(module_label, module_label.lower())
                answer = f"## Resultat\n{result_summary}\n\n## Tolkning\nExperimentet visar {localized_label} och jämför empiriska resultat med motsvarande teori.\n\n## Nästa steg\n{guiding_question}"
            else:
                answer = f"## Result\n{result_summary}\n\n## What it means\nThis experiment illustrates {module_label.lower()} and compares empirical output with the corresponding theoretical reference.\n\n## Try next\n{guiding_question}"
        else:
            answer = message("SIMULATION_FAILED", response_language, error=error or "the tool rejected the request")
        if corrections:
            heading = {"zh": "检查这个想法", "sv": "Kontrollera denna idé"}.get(response_language, "Check this idea")
            answer += f"\n\n## {heading}\n" + "\n".join(f"- {item}" for item in corrections)
        return answer

    def scope_response(
        self,
        *,
        is_general: bool,
        general: Callable[[], str],
        out_of_scope: Callable[[], str],
    ) -> str:
        """Keep casual and out-of-course responses in the Tutor boundary."""

        return general() if is_general else out_of_scope()
