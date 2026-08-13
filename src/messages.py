"""Small catalog for deterministic, student-facing system messages."""

from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "OUT_OF_SCOPE": {
        "en": "That question is outside the scope of this stochastic-process course. The course evidence does not cover it, so I will not guess. I can help with stochastic-process concepts, course modules, or verified simulations.",
        "zh": "这个问题不属于随机过程课程范围。课程材料没有覆盖它，因此我不会猜测。我可以帮助你学习随机过程概念、课程模块或经过验证的模拟。",
        "sv": "Den frågan ligger utanför kursen i stokastiska processer. Kursmaterialet täcker den inte, så jag gissar inte. Jag kan hjälpa till med stokastiska processer, kursmoduler eller verifierade simuleringar.",
    },
    "GENERAL": {
        "en": "I am StochLab, a tutor for the stochastic-process course. I can explain concepts, guide you through the modules, and run verified simulations when you ask for one.",
        "zh": "我是 StochLab 随机过程课程导师。我可以解释课程概念、引导你学习模块，并在你明确提出请求时运行经过验证的模拟。",
        "sv": "Jag är StochLab-handledaren för kursen i stokastiska processer. Jag kan förklara kursbegrepp, guida dig genom modulerna och köra verifierade simuleringar när du ber om det.",
    },
    "EVIDENCE_PARTIAL": {
        "en": "The course material can explain {supported}, but an exact result depends on {missing}. Could you provide these model details so I can proceed without guessing?",
        "zh": "课程材料可以解释{supported}，但精确结果取决于{missing}。请补充这些模型信息，这样我就能继续而不凭空猜测。",
        "sv": "Kursmaterialet kan förklara {supported}, men ett exakt resultat beror på {missing}. Kan du ange dessa modelldetaljer så att jag kan fortsätta utan att gissa?",
    },
    "EVIDENCE_PARTIAL_SINGLE": {
        "en": "The course material can explain {supported}, but it does not determine the requested result without the {missing}. Please provide the {missing} so I can check the claim rather than guess.",
        "zh": "课程材料可以解释{supported}，但没有{missing}就无法确定所要求的结果。请提供{missing}，这样我可以核查这个结论，而不是猜测。",
        "sv": "Kursmaterialet kan förklara {supported}, men det önskade resultatet kan inte bestämmas utan {missing}. Ange {missing} så att jag kan kontrollera påståendet i stället för att gissa.",
    },
    "NEED_MORE_INFORMATION": {
        "en": "I do not have enough course evidence to answer that exactly. What is the {missing}?",
        "zh": "课程材料不足以精确回答这个问题。{missing}是多少？",
        "sv": "Kursmaterialet räcker inte för ett exakt svar. Vilket värde har {missing}?",
    },
    "EVIDENCE_NONE": {
        "en": "The course materials do not provide enough evidence for that claim. Please name the stochastic model or specify the quantity you want to determine.",
        "zh": "课程材料没有足够证据支持这个结论。请说明随机模型，或明确你想确定的量。",
        "sv": "Kursmaterialet ger inte tillräckligt stöd för påståendet. Ange den stokastiska modellen eller vilken storhet du vill bestämma.",
    },
    "INVALID_PARAMETER": {
        "en": "That parameter is not supported by the selected course experiment. I will not pass arbitrary inputs to the simulation engine. Please use one of the declared experiment parameters.",
        "zh": "所选课程实验不支持这个参数。我不会把任意输入传给模拟引擎。请使用已声明的实验参数。",
        "sv": "Den parametern stöds inte av det valda kursexperimentet. Jag skickar inte godtyckliga indata till simuleringsmotorn. Använd en deklarerad experimentparameter.",
    },
    "SIMULATION_FAILED": {
        "en": "The parameters were not valid: {error}. Please adjust them and try again.",
        "zh": "参数无效：{error}。请调整参数后重试。",
        "sv": "Parametrarna var inte giltiga: {error}. Justera dem och försök igen.",
    },
    "CONCEPT_FALLBACK": {
        "en": "I could not find enough course evidence for that question. Try naming a module or concept.",
        "zh": "我没有找到足够的课程证据来回答这个问题。请说明模块或概念名称。",
        "sv": "Jag hittade inte tillräckligt kursstöd för frågan. Ange gärna en modul eller ett begrepp.",
    },
    "CONFLICT": {
        "en": "The supplied course sources make materially different claims, so I cannot give one definitive answer without more context.",
        "zh": "提供的课程来源包含实质不同的结论，因此在缺少更多背景时我不能给出唯一确定的答案。",
        "sv": "De angivna kurskällorna gör väsentligt olika påståenden, så jag kan inte ge ett entydigt svar utan mer sammanhang.",
    },
}


def message(key: str, language: str = "en", **values: object) -> str:
    """Render one catalog message, falling back to English for bad locales."""

    template = MESSAGES.get(key, {}).get(language) or MESSAGES.get(key, {}).get("en", key)
    return template.format(**values)


__all__ = ["MESSAGES", "message"]
