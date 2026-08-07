"""Tool-using, source-aware teaching agent for stochastic processes."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from typing import Any

from .knowledge import KnowledgeBase
from .llm import OpenAICompatibleLLM, preserves_verified_facts
from .memory import LearnerMemory
from .module_registry import MODULE_BY_ID, classify_module
from .pedagogy import adaptive_note, diagnose
from .recommendation import recommend_next
from .workflow import AgentState, NodeOutcome, StateGraph, WorkflowNode
from .processes import (
    analyze_markov_chain,
    analyze_reliability_system,
    run_monte_carlo_pi,
    simulate_batch_buffer,
    simulate_bernoulli_process,
    simulate_brownian_motion,
    simulate_birth_death_process,
    simulate_coalescing_particles,
    simulate_continuous_random_walk,
    simulate_mm1_queue,
    simulate_nhpp_thinning,
    simulate_poisson_process,
    simulate_random_walk,
    simulate_self_avoiding_walk,
    simulate_two_state_ctmc,
)


class StochasticTutorAgent:
    """Route questions through retrieval, simulation, verification and teaching."""

    NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

    PARAMETER_LABELS: dict[str, tuple[str, ...]] = {
        "samples": ("samples", "样本数", "样本", "实验数"),
        "seed": ("seed", "随机种子"),
        "slots": ("slots", "时间槽数", "时隙数", "时间槽"),
        "probability": ("probability", "event probability", "p", "事件概率", "到达概率"),
        "paths": ("paths", "路径数", "条路径", "实验数"),
        "rate": ("lambda", "λ", "rate", "强度", "速率", "跳跃率"),
        "horizon": ("horizon", "时间范围", "时长", "T"),
        "steps": ("steps", "步数", "网格数", "时间槽数"),
        "probability_up": ("probability_up", "p", "向上概率", "正向概率"),
        "failure_rate": ("failure_rate", "failure rate", "alpha", "故障率"),
        "repair_rate": ("repair_rate", "repair rate", "beta", "维修率", "修复率"),
        "birth_rate": ("birth_rate", "birth rate", "lambda", "λ", "出生率"),
        "death_rate": ("death_rate", "death rate", "mu", "μ", "死亡率"),
        "capacity": ("capacity", "容量", "最大状态"),
        "initial_state": ("initial_state", "初始状态"),
        "failure_rate_1": ("failure_rate_1", "failure rate 1", "lambda1", "λ1", "部件1故障率"),
        "failure_rate_2": ("failure_rate_2", "failure rate 2", "lambda2", "λ2", "部件2故障率"),
        "arrival_probability": ("arrival_probability", "arrival probability", "p", "到达概率"),
        "arrival_rate": ("arrival_rate", "arrival rate", "lambda", "λ", "到达率"),
        "service_rate": ("service_rate", "service rate", "mu", "μ", "服务率"),
        "max_state": ("max_state", "显示状态数", "最大状态"),
        "base_rate": ("base_rate", "base rate", "基础强度", "基础率"),
        "peak_rate": ("peak_rate", "peak rate", "峰值增量", "峰值强度"),
        "peak_center": ("peak_center", "peak center", "峰值时刻", "高峰时刻"),
        "peak_width": ("peak_width", "peak width", "峰值宽度", "高峰宽度"),
        "max_steps": ("max_steps", "maximum steps", "最大步数", "步数"),
        "runs": ("runs", "实验次数", "模拟次数"),
        "circle_size": ("circle_size", "circle size", "m", "圆周大小", "格点数"),
        "particles": ("particles", "k", "粒子数", "初始粒子"),
    }

    RETRIEVAL_HINTS: dict[str, str] = {
        "monte_carlo": "Monte Carlo sample mean standard error 蒙特卡洛 样本误差",
        "bernoulli": "Bernoulli geometric waiting time 伯努利 几何等待时间",
        "poisson": "homogeneous Poisson process exponential waiting 泊松过程 指数等待",
        "random_walk": "discrete random walk gambler ruin 离散随机游走 赌徒破产",
        "continuous_random_walk": "continuous time random walk Poisson jump times 连续时间随机游走",
        "brownian_motion": "Brownian motion Gaussian increments 布朗运动 高斯增量",
        "markov_chain": "discrete Markov chain stationary distribution 转移矩阵 平稳分布",
        "ctmc": "continuous time Markov chain generator holding time 生成矩阵 停留时间",
        "birth_death": "birth death process stationary distribution 出生死亡过程",
        "reliability": "reliability survival hazard series parallel 可靠性 生存函数 串联 并联",
        "buffer": "batch arrival buffer service 批量到达 缓冲区 服务",
        "mm1_queue": "M/M/1 queue arrival service stability 排队 到达率 服务率 稳定性",
        "nhpp": "nonhomogeneous Poisson thinning intensity 非齐次泊松 时变强度",
        "self_avoiding_walk": "growing self avoiding walk trapping visited set 自避免游走 受困",
        "coalescing_particles": "coalescing particles circle cluster count 粒子合并 圆周 簇数量",
    }

    def __init__(self, memory: LearnerMemory | None = None) -> None:
        self.knowledge = KnowledgeBase()
        self.llm = OpenAICompatibleLLM()
        self.memory = memory or LearnerMemory()
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {
            "monte_carlo": run_monte_carlo_pi,
            "bernoulli": simulate_bernoulli_process,
            "poisson": simulate_poisson_process,
            "random_walk": simulate_random_walk,
            "continuous_random_walk": simulate_continuous_random_walk,
            "brownian_motion": simulate_brownian_motion,
            "markov_chain": analyze_markov_chain,
            "ctmc": simulate_two_state_ctmc,
            "birth_death": simulate_birth_death_process,
            "reliability": analyze_reliability_system,
            "buffer": simulate_batch_buffer,
            "mm1_queue": simulate_mm1_queue,
            "nhpp": simulate_nhpp_thinning,
            "self_avoiding_walk": simulate_self_avoiding_walk,
            "coalescing_particles": simulate_coalescing_particles,
        }
        self.workflow = StateGraph(
            [
                WorkflowNode("classify", self._node_classify),
                WorkflowNode("retrieve", self._node_retrieve),
                WorkflowNode("plan", self._node_plan),
                WorkflowNode("tool", self._node_tool),
                WorkflowNode("diagnose", self._node_diagnose),
                WorkflowNode("memory", self._node_memory),
                WorkflowNode("respond", self._node_respond),
            ]
        )

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
        if module_id == "module01" and any(
            keyword in lowered
            for keyword in (
                "bernoulli",
                "伯努利",
                "geometric waiting",
                "geometric distribution",
                "几何等待",
                "几何分布",
            )
        ):
            return "bernoulli"
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
        if module_id == "module07":
            if any(
                keyword in lowered
                for keyword in ("m/m/1", "mm1", "queue", "排队", "队列")
            ):
                return "mm1_queue"
            if any(keyword in lowered for keyword in ("buffer", "缓冲区", "缓存")):
                return "buffer"
        return default_tool

    @staticmethod
    def _find_number(
        text: str, labels: tuple[str, ...], default: float, integer: bool = False
    ) -> float | int:
        for label in labels:
            pattern = (
                rf"(?:{re.escape(label)})\s*"
                rf"(?:为|=|:|是|改成|改为|调整为|设为)?\s*"
                rf"({StochasticTutorAgent.NUMBER_PATTERN})"
            )
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                reverse_pattern = (
                    rf"({StochasticTutorAgent.NUMBER_PATTERN})\s*"
                    rf"(?:个|条)?\s*(?:{re.escape(label)})"
                )
                match = re.search(reverse_pattern, text, flags=re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if integer:
                    if not value.is_integer():
                        raise ValueError(f"{label} must be an integer")
                    return int(value)
                return value
        return int(default) if integer else float(default)

    @classmethod
    def _parameter_mentioned(cls, key: str, text: str) -> bool:
        """Check whether a turn explicitly supplies one parameter value."""

        labels = cls.PARAMETER_LABELS.get(key, (key, key.replace("_", " ")))
        for label in labels:
            forward = (
                rf"(?:{re.escape(label)})\s*"
                rf"(?:为|=|:|是|改成|改为|调整为|设为)?\s*"
                rf"{cls.NUMBER_PATTERN}"
            )
            reverse = (
                rf"{cls.NUMBER_PATTERN}\s*(?:个|条)?\s*(?:{re.escape(label)})"
            )
            if re.search(forward, text, flags=re.IGNORECASE) or re.search(
                reverse, text, flags=re.IGNORECASE
            ):
                return True
        return False

    def extract_parameters(self, topic: str, question: str) -> dict[str, Any]:
        seed = self._find_number(question, ("seed", "随机种子"), 42, integer=True)
        if topic == "monte_carlo":
            return {
                "samples": self._find_number(
                    question, ("samples", "样本数", "样本"), 5000, integer=True
                ),
                "seed": seed,
            }
        if topic == "bernoulli":
            return {
                "slots": self._find_number(
                    question, ("slots", "时间槽数", "时隙数", "时间槽"), 100, integer=True
                ),
                "probability": self._find_number(
                    question,
                    ("probability", "event probability", "p", "事件概率", "到达概率"),
                    0.3,
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径", "实验数"), 500, integer=True
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
                    question, ("paths", "路径数", "条路径"), 200, integer=True
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
                    question, ("paths", "路径数", "条路径"), 500, integer=True
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
                    question, ("paths", "路径数", "条路径"), 500, integer=True
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
                    question, ("paths", "路径数", "条路径"), 500, integer=True
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
        if topic == "reliability":
            return {
                "failure_rate_1": self._find_number(
                    question,
                    ("failure_rate_1", "failure rate 1", "lambda1", "λ1", "部件1故障率"),
                    0.8,
                ),
                "failure_rate_2": self._find_number(
                    question,
                    ("failure_rate_2", "failure rate 2", "lambda2", "λ2", "部件2故障率"),
                    1.2,
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时长", "时间范围", "T"), 6.0
                ),
                "samples": self._find_number(
                    question, ("samples", "样本数", "实验数"), 5000, integer=True
                ),
                "points": 120,
                "seed": seed,
            }
        if topic == "buffer":
            return {
                "steps": self._find_number(
                    question, ("steps", "步数", "时间槽数"), 120, integer=True
                ),
                "arrival_probability": self._find_number(
                    question, ("arrival_probability", "arrival probability", "p", "到达概率"), 0.6
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 200, integer=True
                ),
                "seed": seed,
            }
        if topic == "mm1_queue":
            return {
                "arrival_rate": self._find_number(
                    question, ("arrival_rate", "arrival rate", "lambda", "λ", "到达率"), 0.9
                ),
                "service_rate": self._find_number(
                    question, ("service_rate", "service rate", "mu", "μ", "服务率"), 1.0
                ),
                "horizon": self._find_number(
                    question, ("horizon", "时长", "时间范围", "T"), 2000.0
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径"), 20, integer=True
                ),
                "max_state": self._find_number(
                    question, ("max_state", "显示状态数", "最大状态"), 50, integer=True
                ),
                "seed": seed,
            }
        if topic == "nhpp":
            return {
                "horizon": self._find_number(
                    question, ("horizon", "时长", "时间范围", "T"), 24.0
                ),
                "base_rate": self._find_number(
                    question, ("base_rate", "base rate", "基础强度", "基础率"), 2.0
                ),
                "peak_rate": self._find_number(
                    question, ("peak_rate", "peak rate", "峰值增量", "峰值强度"), 6.0
                ),
                "peak_center": self._find_number(
                    question, ("peak_center", "peak center", "峰值时刻", "高峰时刻"), 13.0
                ),
                "peak_width": self._find_number(
                    question, ("peak_width", "peak width", "峰值宽度", "高峰宽度"), 4.0
                ),
                "paths": self._find_number(
                    question, ("paths", "路径数", "条路径", "实验数"), 200, integer=True
                ),
                "seed": seed,
            }
        if topic == "self_avoiding_walk":
            return {
                "max_steps": self._find_number(
                    question, ("max_steps", "maximum steps", "最大步数", "步数"), 1000, integer=True
                ),
                "runs": self._find_number(
                    question, ("runs", "实验次数", "模拟次数"), 1000, integer=True
                ),
                "seed": seed,
            }
        if topic == "coalescing_particles":
            return {
                "circle_size": self._find_number(
                    question, ("circle_size", "circle size", "m", "圆周大小", "格点数"), 12, integer=True
                ),
                "particles": self._find_number(
                    question, ("particles", "k", "粒子数", "初始粒子"), 9, integer=True
                ),
                "runs": self._find_number(
                    question, ("runs", "实验次数", "模拟次数"), 500, integer=True
                ),
                "max_steps": self._find_number(
                    question, ("max_steps", "maximum steps", "最大步数"), 10000, integer=True
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
        if topic == "bernoulli":
            return (
                f"终点计数的经验均值为 {result['empirical_count_mean']}，"
                f"理论均值 np 为 {result['theoretical_count_mean']}；经验方差为 "
                f"{result['empirical_count_variance']}，理论方差为 "
                f"{result['theoretical_count_variance']}。首次到达的经验平均等待"
                f"时间为 {result['empirical_waiting_mean']}，几何分布理论值"
                f"1/p为 {result['theoretical_waiting_mean']}。"
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
        if topic == "reliability":
            return (
                f"串联系统经验平均寿命为 "
                f"{result['empirical_series_mean_lifetime']}，理论值为 "
                f"{result['theoretical_series_mean_lifetime']}；并联系统经验"
                f"平均寿命为 {result['empirical_parallel_mean_lifetime']}，"
                f"理论值为 {result['theoretical_parallel_mean_lifetime']}。"
            )
        if topic == "buffer":
            return (
                f"每个时间槽的经验平均到达数为 "
                f"{result['empirical_arrivals_per_slot']}，理论值为 "
                f"{result['theoretical_arrivals_per_slot']}；忙时理论漂移为 "
                f"{result['theoretical_drift_when_busy']}，经验平均最终 buffer "
                f"大小为 {result['empirical_mean_final_buffer']}。"
            )
        if topic == "mm1_queue":
            if result["stable"]:
                return (
                    f"交通强度 ρ={result['traffic_intensity']}<1，队列稳定。"
                    f"经验平均客户数为 {result['empirical_mean_customers']}，"
                    f"理论值 ρ/(1-ρ) 为 {result['theoretical_mean_customers']}，"
                    f"展示状态上的L1误差为 {result['displayed_state_l1_error']}。"
                )
            return (
                f"交通强度 ρ={result['traffic_intensity']}≥1，不存在稳定的"
                f"几何平稳分布；有限时间仿真中的经验平均客户数"
                f"为 {result['empirical_mean_customers']}。"
            )
        if topic == "nhpp":
            return (
                f"Thinning 生成 {result['candidate_count']} 个候选事件，"
                f"接受率为 {result['acceptance_rate']}。最终计数的经验"
                f"均值为 {result['empirical_mean_count']}，强度积分给出的"
                f"理论均值为 {result['theoretical_mean_count']}，绝对误差为 "
                f"{result['absolute_error']}。"
            )
        if topic == "self_avoiding_walk":
            return (
                f"{result['trapped_runs']} / {result['parameters']['runs']} 条路径"
                f"在数值上限前真正受困，受困率为 "
                f"{result['trapping_rate']}，平均停止长度为 "
                f"{result['average_stopping_length']}。示例路径的自避性和"
                f"最近邻移动校验分别为 {result['sample_self_avoiding']} 和 "
                f"{result['sample_nearest_neighbour']}。"
            )
        if topic == "coalescing_particles":
            return (
                f"{result['completed_runs']} / {result['parameters']['runs']} 次实验"
                f"在上限前合并为一个簇，平均合并时间为 "
                f"{result['average_coalescence_time']}，中位数为 "
                f"{result['median_coalescence_time']}。示例路径的簇数量单调不增"
                f"校验为 {result['sample_cluster_count_monotone']}。"
            )
        raise ValueError(f"unsupported summary topic: {topic}")

    @staticmethod
    def _guiding_question(topic: str) -> str:
        questions = {
            "bernoulli": "如果降低单个时间槽的到达概率，计数和首次等待时间会怎样变化？",
            "reliability": "为什么并联系统的寿命是部件寿命的最大值，而串联系统是最小值？",
            "buffer": "当每槽平均到达数超过服务能力1时，buffer路径会呈现什么长期趋势？",
            "mm1_queue": "当到达率逐渐接近服务率时，理论平均客户数为什么会快速增大？",
            "nhpp": "如果把高峰时刻向后移动，总事件数和事件时刻分布会分别如何变化？",
            "self_avoiding_walk": "为什么只知道当前位置不足以确定自避游走的下一步分布？",
            "coalescing_particles": "增大圆周格点数但保持初始粒子数不变，合并时间可能怎样变化？",
        }
        return questions.get(
            topic,
            "如果把样本量或路径数扩大4倍，你预计经验误差会怎样变化？",
        )

    def _node_classify(self, state: AgentState) -> NodeOutcome:
        state.module_id = self.classify_module(state.question)
        if state.module_id is None and state.previous_turn:
            state.module_id = state.previous_turn["module_id"]
            state.module_from_context = True
        if state.module_id is None:
            raise ValueError(
                "I could not identify the teaching module. Please name a model or Module 00-10."
            )
        state.module = MODULE_BY_ID[state.module_id]
        state.topic = state.module.topic
        detail = f"Module {state.module.number:02d}: {state.module.label}"
        if state.module_from_context:
            detail += " (inherited from previous turn)"
        return NodeOutcome(detail)

    def _node_retrieve(self, state: AgentState) -> NodeOutcome:
        state.retrieval_query = state.question
        if (
            state.module_from_context
            and state.previous_turn
            and state.previous_turn["tool"]
        ):
            previous_tool = state.previous_turn["tool"]
            state.retrieval_query += " " + self.RETRIEVAL_HINTS.get(
                previous_tool, previous_tool
            )
        state.sources = self.knowledge.retrieve(
            state.retrieval_query,
            topic=state.topic,
            module_id=state.module_id,
        )
        return NodeOutcome(f"{len(state.sources)} source-aware notes")

    def _node_plan(self, state: AgentState) -> NodeOutcome:
        default_tool = state.module.tool_key
        if default_tool is None:
            raise ValueError(f"Module {state.module.number:02d} has no executable tool")
        if (
            state.previous_turn
            and state.previous_turn["module_id"] == state.module_id
            and state.previous_turn["tool"] in self.tools
        ):
            default_tool = state.previous_turn["tool"]
        state.tool_key = self.resolve_tool(
            state.module_id, default_tool, state.question
        )
        state.parameters = self.extract_parameters(state.tool_key, state.question)
        if (
            state.previous_turn
            and state.previous_turn["module_id"] == state.module_id
            and state.previous_turn["tool"] == state.tool_key
        ):
            for key, previous_value in state.previous_turn["parameters"].items():
                if key in state.parameters and not self._parameter_mentioned(
                    key, state.question
                ):
                    state.parameters[key] = previous_value
                    state.inherited_parameters.append(key)
        detail = f"call {state.tool_key} simulation tool"
        if state.inherited_parameters:
            detail += "; inherited " + ", ".join(
                sorted(state.inherited_parameters)
            )
        return NodeOutcome(detail)

    def _node_tool(self, state: AgentState) -> NodeOutcome:
        if state.tool_key is None:
            raise RuntimeError("plan node did not select a tool")
        try:
            state.result = self.tools[state.tool_key](**state.parameters)
            state.verified = True
            return NodeOutcome("simulation completed and validated")
        except ValueError as error:
            state.result = {
                "error": str(error),
                "parameters": state.parameters,
                "series": [],
            }
            state.verified = False
            return NodeOutcome(f"validation failed: {error}")

    def _node_diagnose(self, state: AgentState) -> NodeOutcome:
        if state.module_id is None:
            raise RuntimeError("classification state is missing")
        state.misconceptions = diagnose(state.question, state.module_id)
        if not state.misconceptions:
            return NodeOutcome("no explicit misconception trigger")
        codes = ", ".join(item["code"] for item in state.misconceptions)
        return NodeOutcome(f"identified {codes}")

    def _node_memory(self, state: AgentState) -> NodeOutcome:
        if state.module_id is None or state.topic is None:
            raise RuntimeError("classified module state is missing")
        self.memory.record_turn(
            session_id=state.session_id,
            question=state.question,
            module_id=state.module_id,
            topic=state.topic,
            tool=state.tool_key,
            parameters=state.parameters,
            verified=state.verified,
            misconceptions=state.misconceptions,
        )
        state.profile = self.memory.profile(state.session_id)
        state.learning_note = adaptive_note(state.profile, state.module_id)
        state.recommendation = recommend_next(state.profile)
        return NodeOutcome(
            f"persisted learner turn {state.profile['turns']} to SQLite"
        )

    def _node_respond(self, state: AgentState) -> NodeOutcome:
        if state.tool_key is None or state.topic is None:
            raise RuntimeError("response state is incomplete")
        if state.verified:
            explanation = self._summary(state.tool_key, state.result)
            verified_anchor_text = explanation
            source_text = (
                state.sources[0]["content"]
                if state.sources
                else "本题使用可复现仿真与理论参考值进行比较。"
            )
            deterministic_answer = (
                f"### 先看实验结果\n{explanation}\n\n"
                f"### 如何理解\n{source_text}\n\n"
                f"### 给你的思考题\n{self._guiding_question(state.tool_key)}"
            )
            citations = "；".join(source["source"] for source in state.sources)
            if citations:
                deterministic_answer += f"\n\n来源：{citations}"
        else:
            deterministic_answer = (
                f"参数校验没有通过：{state.result['error']}。请修改参数后再运行，"
                "我不会用不合法的参数生成看似合理的图。"
            )
            verified_anchor_text = deterministic_answer

        if state.misconceptions:
            corrections = "\n".join(
                f"- {item['correction']}" for item in state.misconceptions
            )
            deterministic_answer += f"\n\n### 先纠正一个常见误区\n{corrections}"

        llm_prompt = json.dumps(
            {
                "question": state.question,
                "topic": state.topic,
                "tool_result": {
                    key: value
                    for key, value in state.result.items()
                    if key not in {"series", "event_times", "endpoints", "counts"}
                },
                "retrieved_sources": state.sources,
                "learner_profile": state.profile,
                "draft": deterministic_answer,
            },
            ensure_ascii=False,
        )
        candidate = self.llm.complete(
            (
                "You are a Socratic mathematics tutor. Preserve every numerical "
                "result and source exactly. Explain in concise Chinese, distinguish "
                "simulation from theory, and end with one guiding question."
            ),
            llm_prompt,
        )
        polished = (
            candidate
            if candidate
            and preserves_verified_facts(
                candidate,
                verified_anchor_text,
                state.sources,
            )
            else None
        )
        state.answer = polished or deterministic_answer
        state.response = {
            "session_id": state.session_id,
            "answer": state.answer,
            "module_id": state.module_id,
            "module_number": state.module.number,
            "module_label": state.module.label,
            "topic": state.topic,
            "topic_label": state.module.label,
            "tool": self.tools[state.tool_key].__name__,
            "parameters": state.parameters,
            "result": state.result,
            "sources": state.sources,
            "trace": state.trace,
            "workflow": {"nodes": list(self.workflow.node_names)},
            "memory": state.profile,
            "misconceptions": state.misconceptions,
            "learning_note": state.learning_note,
            "recommendation": state.recommendation,
            "context": {
                "module_inherited": state.module_from_context,
                "parameters_inherited": sorted(state.inherited_parameters),
            },
            "llm_enabled": self.llm.enabled,
            "llm_applied": bool(polished),
        }
        if polished:
            return NodeOutcome("verified LLM-polished answer")
        if candidate:
            return NodeOutcome("rejected ungrounded LLM rewrite; offline safe answer")
        return NodeOutcome("offline safe answer")

    def answer(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must not be empty")
        if session_id is not None and (
            not isinstance(session_id, str)
            or not session_id.strip()
            or len(session_id) > 128
        ):
            raise ValueError(
                "session_id must be a non-empty string of at most 128 characters"
            )
        resolved_session = session_id or str(uuid.uuid4())
        history = self.memory.history(resolved_session, limit=1)
        state = AgentState(
            question=question.strip(),
            session_id=resolved_session,
            previous_turn=history[-1] if history else None,
        )
        completed = self.workflow.invoke(state)
        return completed.response
