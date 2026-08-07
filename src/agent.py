"""Tool-using, source-aware teaching agent for stochastic processes."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from typing import Any

from .knowledge import KnowledgeBase
from .llm import OpenAICompatibleLLM
from .module_registry import MODULE_BY_ID, classify_module
from .processes import (
    analyze_markov_chain,
    run_monte_carlo_pi,
    simulate_brownian_motion,
    simulate_birth_death_process,
    simulate_continuous_random_walk,
    simulate_poisson_process,
    simulate_random_walk,
    simulate_two_state_ctmc,
)


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
            "continuous_random_walk": simulate_continuous_random_walk,
            "brownian_motion": simulate_brownian_motion,
            "markov_chain": analyze_markov_chain,
            "ctmc": simulate_two_state_ctmc,
            "birth_death": simulate_birth_death_process,
        }

    @staticmethod
    def classify_topic(question: str) -> str:
        """Backward-compatible topic label derived from the module registry."""

        module_id = classify_module(question)
        return MODULE_BY_ID[module_id].topic if module_id else "unknown"

    @staticmethod
    def classify_module(question: str) -> str | None:
        return classify_module(question)

    @staticmethod
    def resolve_tool(module_id: str, default_tool: str, question: str) -> str:
        """Select a module-specific tool variant from the student's wording."""

        lowered = question.lower().replace("‑", "-").replace("–", "-")
        if module_id == "module06" and any(
            keyword in lowered
            for keyword in (
                "birth death",
                "birth-death",
                "birth–death",
                "出生死亡",
                "生灭过程",
            )
        ):
            return "birth_death"
        return default_tool

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
        if topic == "continuous_random_walk":
            return {
                "rate": self._find_number(
                    question, ("lambda", "λ", "rate", "跳跃率", "速率"), 1.0
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时间范围", "时长", "T"), 10.0
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
        if topic == "ctmc":
            return {
                "failure_rate": self._find_number(
                    question,
                    ("failure_rate", "failure rate", "alpha", "故障率"),
                    0.25,
                ),
                "repair_rate": self._find_number(
                    question,
                    ("repair_rate", "repair rate", "beta", "维修率", "修复率"),
                    0.15,
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时间范围", "时长", "T"), 200.0
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 200, integer=True
                ),
                "initial_state": self._find_number(
                    question, ("initial_state", "初始状态"), 0, integer=True
                ),
                "seed": seed,
            }
        if topic == "birth_death":
            return {
                "birth_rate": self._find_number(
                    question,
                    ("birth_rate", "birth rate", "lambda", "λ", "出生率"),
                    0.35,
                ),
                "death_rate": self._find_number(
                    question,
                    ("death_rate", "death rate", "mu", "μ", "死亡率"),
                    0.30,
                ),
                "capacity": self._find_number(
                    question, ("capacity", "容量", "最大状态"), 6, integer=True
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时间范围", "时长", "T"), 500.0
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 200, integer=True
                ),
                "initial_state": self._find_number(
                    question, ("initial_state", "初始状态"), 2, integer=True
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
        if topic == "continuous_random_walk":
            return (
                f"到时间T的经验平均跳跃数为 {result['empirical_jump_mean']}，"
                f"理论值λT为 {result['theoretical_jump_mean']}。终点经验均值为 "
                f"{result['empirical_endpoint_mean']}，理论均值为 "
                f"{result['theoretical_endpoint_mean']}；终点经验方差为 "
                f"{result['empirical_endpoint_variance']}，理论方差为 "
                f"{result['theoretical_endpoint_variance']}。"
            )
        if topic == "brownian_motion":
            return (
                f"终点经验均值为 {result['empirical_terminal_mean']}，经验方差为 "
                f"{result['empirical_terminal_variance']}；标准布朗运动在T时刻的"
                f"理论均值为0、方差为T={result['theoretical_terminal_variance']}。"
            )
        if topic == "markov_chain":
            return (
                f"经验状态频率为 {result['empirical_frequencies']}，平稳分布为 "
                f"{result['stationary_distribution']}，L1误差为 {result['l1_error']}。"
            )
        if topic == "ctmc":
            return (
                f"经验时间占比为 {result['empirical_state_probabilities']}，"
                f"由 πQ=0 得到的平稳分布为 "
                f"{result['stationary_distribution']}，L1误差为 {result['l1_error']}。"
                f"两个状态的经验平均停留时间为 "
                f"{result['empirical_mean_holding_times']}，理论值为 "
                f"{result['theoretical_mean_holding_times']}。有限观测时长和固定"
                "初始状态会带来过渡偏差。"
            )
        if topic == "birth_death":
            return (
                f"状态经验时间占比为 "
                f"{result['empirical_state_probabilities']}，理论平稳分布为 "
                f"{result['stationary_distribution']}，L1误差为 {result['l1_error']}。"
                f"经验平均状态为 {result['empirical_mean_state']}，"
                f"理论值为 {result['theoretical_mean_state']}。有限观测时长和"
                "固定初始状态会带来过渡偏差。"
            )
        raise ValueError(f"unsupported summary topic: {topic}")

    def answer(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("question must not be empty")
        session_id = session_id or str(uuid.uuid4())
        trace: list[dict[str, str]] = []

        module_id = self.classify_module(question)
        if module_id is None:
            raise ValueError(
                "I could not identify the teaching module. Please name a model or Module 00-10."
            )
        module = MODULE_BY_ID[module_id]
        topic = module.topic
        trace.append(
            {
                "node": "classify",
                "detail": f"Module {module.number:02d}: {module.label}",
            }
        )

        sources = self.knowledge.retrieve(
            question, topic=topic, module_id=module_id
        )
        trace.append(
            {"node": "retrieve", "detail": f"{len(sources)} source-aware notes"}
        )

        default_tool = module.tool_key
        if default_tool is None:
            trace.append(
                {
                    "node": "plan",
                    "detail": f"Module {module.number:02d} tool extraction pending",
                }
            )
            source_text = sources[0]["content"] if sources else module.label
            answer = (
                f"### Module {module.number:02d}: {module.label}\n{source_text}\n\n"
                "该模块已经进入课程检索与路由系统；对应的可执行仿真工具正在从论文 Notebook 中提取。"
            )
            self.sessions.setdefault(session_id, []).append(
                {"question": question, "topic": topic, "module_id": module_id}
            )
            return {
                "session_id": session_id,
                "answer": answer,
                "module_id": module_id,
                "module_number": module.number,
                "module_label": module.label,
                "topic": topic,
                "topic_label": module.label,
                "tool": None,
                "parameters": {},
                "result": {"status": "tool_pending"},
                "sources": sources,
                "trace": trace,
                "memory": {
                    "turns": len(self.sessions[session_id]),
                    "modules": [
                        item["module_id"] for item in self.sessions[session_id]
                    ],
                },
                "llm_enabled": self.llm.enabled,
            }

        tool_key = self.resolve_tool(module_id, default_tool, question)

        parameters = self.extract_parameters(tool_key, question)
        trace.append({"node": "plan", "detail": f"call {tool_key} simulation tool"})

        try:
            result = self.tools[tool_key](**parameters)
            trace.append({"node": "tool", "detail": "simulation completed"})
            verified = True
        except ValueError as error:
            result = {"error": str(error), "parameters": parameters, "series": []}
            trace.append({"node": "tool", "detail": f"validation failed: {error}"})
            verified = False

        if verified:
            explanation = self._summary(tool_key, result)
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
            {"question": question, "topic": topic, "module_id": module_id}
        )
        return {
            "session_id": session_id,
            "answer": answer,
            "module_id": module_id,
            "module_number": module.number,
            "module_label": module.label,
            "topic": topic,
            "topic_label": module.label,
            "tool": self.tools[tool_key].__name__,
            "parameters": parameters,
            "result": result,
            "sources": sources,
            "trace": trace,
            "memory": {
                "turns": len(self.sessions[session_id]),
                "modules": [
                    item["module_id"] for item in self.sessions[session_id]
                ],
            },
            "llm_enabled": self.llm.enabled,
        }
