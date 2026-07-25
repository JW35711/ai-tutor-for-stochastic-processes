"""Tool-using, source-aware teaching agent for stochastic processes."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from typing import Any

from .knowledge import KnowledgeBase
from .llm import OpenAICompatibleLLM
from .processes import (
    analyze_markov_chain,
    run_monte_carlo_pi,
    simulate_brownian_motion,
    simulate_poisson_process,
    simulate_random_walk,
)


TOPIC_LABELS = {
    "monte_carlo": "Monte Carlo",
    "poisson": "Poisson process",
    "random_walk": "Random walk",
    "brownian_motion": "Brownian motion",
    "markov_chain": "Markov chain",
}


class StochasticTutorAgent:
    """Route questions through retrieval, simulation, verification and teaching."""

    def __init__(self) -> None:
        self.knowledge = KnowledgeBase()
        self.llm = OpenAICompatibleLLM()
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {
            "monte_carlo": run_monte_carlo_pi,
            "poisson": simulate_poisson_process,
            "random_walk": simulate_random_walk,
            "brownian_motion": simulate_brownian_motion,
            "markov_chain": analyze_markov_chain,
        }

    @staticmethod
    def classify_topic(question: str) -> str:
        lowered = question.lower()
        rules = [
            ("brownian_motion", ("brownian", "布朗", "wiener")),
            ("poisson", ("poisson", "泊松", "等待时间", "到达过程")),
            ("markov_chain", ("markov", "马尔可夫", "平稳分布", "转移矩阵")),
            ("random_walk", ("random walk", "随机游走", "gambler", "赌徒")),
            ("monte_carlo", ("monte carlo", "蒙特卡洛", "估计π", "估计pi")),
        ]
        for topic, keywords in rules:
            if any(keyword in lowered for keyword in keywords):
                return topic
        return "monte_carlo"

    @staticmethod
    def _find_number(
        text: str, labels: tuple[str, ...], default: float, integer: bool = False
    ) -> float | int:
        for label in labels:
            pattern = rf"(?:{re.escape(label)})\s*(?:为|=|:|是)?\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = float(match.group(1))
                return int(value) if integer else value
        return int(default) if integer else float(default)

    def extract_parameters(self, topic: str, question: str) -> dict[str, Any]:
        seed = self._find_number(question, ("seed", "随机种子"), 42, integer=True)
        if topic == "monte_carlo":
            return {
                "samples": self._find_number(
                    question, ("samples", "样本数", "样本"), 5000, integer=True
                ),
                "seed": seed,
            }
        if topic == "poisson":
            return {
                "rate": self._find_number(
                    question, ("lambda", "λ", "rate", "强度", "速率"), 2.0
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时间范围", "时长", "T"), 5.0
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 20, integer=True
                ),
                "seed": seed,
            }
        if topic == "random_walk":
            return {
                "steps": self._find_number(
                    question, ("steps", "步数", "步"), 100, integer=True
                ),
                "probability_up": self._find_number(
                    question, ("p", "向上概率", "正向概率"), 0.5
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 20, integer=True
                ),
                "seed": seed,
            }
        if topic == "brownian_motion":
            return {
                "horizon": self._find_number(
                    question, ("horizon", "时间范围", "时长", "T"), 1.0
                ),
                "steps": self._find_number(
                    question, ("steps", "步数", "网格数"), 200, integer=True
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 12, integer=True
                ),
                "seed": seed,
            }
        return {
            "steps": self._find_number(
                question, ("steps", "步数", "步"), 500, integer=True
            ),
            "initial_state": self._find_number(
                question, ("initial_state", "初始状态"), 0, integer=True
            ),
            "seed": seed,
        }

    @staticmethod
    def _summary(topic: str, result: dict[str, Any]) -> str:
        if topic == "monte_carlo":
            return (
                f"使用 {result['parameters']['samples']} 个样本得到 π≈"
                f"{result['estimate']}，与理论值 {result['theoretical']} 的绝对误差为 "
                f"{result['absolute_error']}。"
            )
        if topic == "poisson":
            return (
                f"仿真平均事件数为 {result['empirical_mean_count']}，理论值 λT="
                f"{result['theoretical_mean_count']}，绝对误差为 "
                f"{result['absolute_error']}。"
            )
        if topic == "random_walk":
            return (
                f"终点经验均值为 {result['empirical_endpoint_mean']}，理论均值为 "
                f"{result['theoretical_endpoint_mean']}；经验方差为 "
                f"{result['empirical_endpoint_variance']}，理论方差为 "
                f"{result['theoretical_endpoint_variance']}。"
            )
        if topic == "brownian_motion":
            return (
                f"终点经验均值为 {result['empirical_terminal_mean']}，经验方差为 "
                f"{result['empirical_terminal_variance']}；标准布朗运动在T时刻的"
                f"理论均值为0、方差为T={result['theoretical_terminal_variance']}。"
            )
        return (
            f"经验状态频率为 {result['empirical_frequencies']}，平稳分布为 "
            f"{result['stationary_distribution']}，L1误差为 {result['l1_error']}。"
        )

    def answer(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("question must not be empty")
        session_id = session_id or str(uuid.uuid4())
        trace: list[dict[str, str]] = []

        topic = self.classify_topic(question)
        trace.append({"node": "classify", "detail": TOPIC_LABELS[topic]})

        sources = self.knowledge.retrieve(question, topic=topic)
        trace.append(
            {"node": "retrieve", "detail": f"{len(sources)} source-aware notes"}
        )

        parameters = self.extract_parameters(topic, question)
        trace.append({"node": "plan", "detail": f"call {topic} simulation tool"})

        try:
            result = self.tools[topic](**parameters)
            trace.append({"node": "tool", "detail": "simulation completed"})
            verified = True
        except ValueError as error:
            result = {"error": str(error), "parameters": parameters, "series": []}
            trace.append({"node": "tool", "detail": f"validation failed: {error}"})
            verified = False

        if verified:
            explanation = self._summary(topic, result)
            citation_text = "；".join(source["source"] for source in sources)
            deterministic_answer = (
                f"### 先看实验结果\n{explanation}\n\n"
                f"### 如何理解\n{sources[0]['content'] if sources else '本题使用可复现仿真与理论参考值进行比较。'}\n\n"
                f"### 给你的思考题\n如果把样本量或路径数扩大4倍，你预计经验误差会怎样变化？"
            )
            if citation_text:
                deterministic_answer += f"\n\n来源：{citation_text}"
        else:
            deterministic_answer = (
                f"参数校验没有通过：{result['error']}。请修改参数后再运行，"
                "我不会用不合法的参数生成看似合理的图。"
            )

        llm_prompt = json.dumps(
            {
                "question": question,
                "topic": topic,
                "tool_result": {
                    key: value
                    for key, value in result.items()
                    if key not in {"series", "event_times", "endpoints", "counts"}
                },
                "retrieved_sources": sources,
                "draft": deterministic_answer,
            },
            ensure_ascii=False,
        )
        polished = self.llm.complete(
            (
                "You are a Socratic mathematics tutor. Preserve every numerical "
                "result and source exactly. Explain in concise Chinese, distinguish "
                "simulation from theory, and end with one guiding question."
            ),
            llm_prompt,
        )
        answer = polished or deterministic_answer
        trace.append(
            {
                "node": "respond",
                "detail": "LLM-polished answer" if polished else "offline safe answer",
            }
        )

        self.sessions.setdefault(session_id, []).append(
            {"question": question, "topic": topic}
        )
        return {
            "session_id": session_id,
            "answer": answer,
            "topic": topic,
            "topic_label": TOPIC_LABELS[topic],
            "tool": self.tools[topic].__name__,
            "parameters": parameters,
            "result": result,
            "sources": sources,
            "trace": trace,
            "memory": {
                "turns": len(self.sessions[session_id]),
                "topics": [item["topic"] for item in self.sessions[session_id]],
            },
            "llm_enabled": self.llm.enabled,
        }
