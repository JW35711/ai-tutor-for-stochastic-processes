"""Tool-using, source-aware teaching agent for stochastic processes."""

from __future__ import annotations

import json
import math
import re
import time
import uuid
import inspect
from collections.abc import Callable
from typing import Any

from .knowledge import KnowledgeBase
from .experiments import ExperimentRegistry
from .config import runtime_config
from .curriculum import curriculum_catalog
from .agents import AssessmentAgent, CurriculumAgent, TutorAgent, TutorContext
from .llm import OpenAICompatibleLLM
from .memory import LearnerMemory
from .messages import message
from .module_registry import MODULES, MODULE_BY_ID, classify_module
from .pedagogy import adaptive_note, diagnose
from .provenance import execution_sha256
from .recommendation import recommend_next, recommend_next_knowledge_point
from .teaching_team import build_team_trace
from .validation import validate_question, validate_session_id
from .workflow import AgentState, NodeOutcome
from .visualization_contracts import project_and_validate, validate_native_visualization
from .graph.workflow import build_graph
from .graph.response import finalize as finalize_graph_response
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

    GENERAL_FALLBACK = (
        "I am StochLab, a tutor for the Stochastic Processes course. "
        "I can explain concepts, guide you through the modules, and run "
        "verified simulations when you ask for one."
    )
    # These aliases make concept routing specific without duplicating the full
    # curriculum in the router. Titles remain the source of truth; aliases only
    # cover common student wording and the main notebook terminology.
    CONCEPT_ALIASES: dict[str, tuple[str, ...]] = {
        "m00-monte-carlo-estimation": ("monte carlo", "estimate pi", "estimate π"),
        "m00-law-large-numbers": ("law of large numbers", "large numbers"),
        "m00-standard-error": ("standard error", "sampling error"),
        "m01-bernoulli-process": ("bernoulli process", "bernoulli arrivals"),
        "m01-poisson-process": ("poisson process", "homogeneous poisson", "poisson sample path", "arrival path"),
        "m01-geometric-waiting-time": ("geometric waiting time", "geometric distribution", "waiting time", "interarrival time"),
        "m02-random-walk-increments": ("random walk", "ordinary random walk", "simple random walk"),
        "m02-drift-variance": ("random walk drift", "random walk variance"),
        "m02-hitting-probability": ("hitting probability", "gambler's ruin"),
        "m03-poisson-jump-times": ("poisson jump times", "random jump times"),
        "m04-brownian-increments": ("brownian motion", "brownian increments", "independent increments", "gaussian increments"),
        "m04-brownian-scaling": ("brownian scaling", "scaled random walk approximation"),
        "m04-terminal-distribution": ("brownian terminal distribution", "distribution of b(t)", "brownian variance", "variance of b(t)"),
        "m05-markov-property": ("markov property", "memoryless state dependence"),
        "m05-stationary-distribution": ("stationary distribution", "invariant distribution"),
        "m06-holding-times": ("holding time", "holding times"),
        "m06-generator-matrix": ("generator matrix", "infinitesimal generator"),
        "m06-birth-death-process": ("birth death process", "birth-death process"),
        "m07-survival-and-hazard": ("survival function", "hazard rate", "hazard function"),
        "m07-mm1-queue": ("m/m/1", "mm1 queue", "queue stability"),
        "m08-thinning": ("thinning algorithm", "poisson thinning"),
        "m09-self-avoidance": ("self-avoiding walk", "self avoiding walk", "growing self-avoiding walk"),
        "m10-coalescence": ("coalescence", "coalescing particles"),
        "m10-coalescence-time": ("coalescence time",),
    }
    LANGUAGE_ALIASES: dict[str, tuple[str, ...]] = {
        "m00-law-large-numbers": ("lagen om stora tal", "stora talens lag", "大数定律"),
        "m01-poisson-process": ("poissonprocess", "poissonprocessen", "泊松过程"),
        "m01-geometric-waiting-time": ("geometrisk väntetid", "väntetid", "等待时间"),
        "m02-hitting-probability": ("träffsannolikhet", "sannolikhet att nå", "到达概率"),
        "m04-brownian-increments": ("brownsk rörelse", "brownsk rörelse", "布朗运动"),
        "m04-terminal-distribution": ("varians för brownsk rörelse", "布朗运动方差"),
        "m05-markov-property": ("markovegenskap", "马尔可夫性质"),
        "m03-rate-effects": ("hoppintensiteten", "antalet hopp", "hoppen"),
        "m05-stationary-distribution": ("stationär fördelning", "stationära fördelningen", "平稳分布"),
        "m06-holding-times": ("uppehållstid", "uppehållstider", "停留时间"),
        "m06-generator-matrix": ("generatormatris", "generatorn", "生成矩阵"),
        "m07-survival-and-hazard": ("överlevnadsfunktion", "hazardfunktion", "失效率"),
        "m07-mm1-queue": ("köstabilitet", "m/m/1-kö", "排队稳定性"),
        "m08-thinning": ("tunningsalgoritm", "tunning", "稀疏化算法"),
        "m09-self-avoidance": ("självundvikande vandring", "自避免游走"),
        "m10-coalescence": ("koalescerande partiklar", "partiklar som slås samman", "粒子合并"),
    }
    # Short, domain-level cues are used only to seed bounded candidates. They
    # are not accepted as evidence and are deliberately broader than exact
    # aliases so paraphrases can reach normal retrieval/evidence checking.
    CANDIDATE_CUES: dict[str, tuple[str, ...]] = {
        "m00-monte-carlo-estimation": ("repeated random sampling", "estimate a quantity", "random samples", "random points", "estimate an area", "monte carlo"),
        "m00-law-large-numbers": ("running average", "less erratic", "many trials", "sample grows"),
        "m00-standard-error": ("monte carlo uncertainty", "estimation error", "sampling variability"),
        "m01-poisson-process": ("constant rate", "zero arrivals", "waiting longer", "interarrival", "arrival count"),
        "m02-absorption-time": ("time to absorption", "until a boundary", "target boundary"),
        "m04-brownian-scaling": ("scaled random walk", "approximates brownian", "grid steps"),
        "m04-terminal-distribution": ("brownian increment", "fixed time", "variance grow", "variance of b"),
        "m04-hitting-events": ("crosses a level", "reaches a level", "hitting chance"),
        "m05-stationary-distribution": ("pi p = pi", "πp = π", "pi p", "invariant probability"),
        "m06-generator-matrix": ("instantaneous transition rates", "rate matrix"),
        "m08-integrated-intensity": ("integrating an intensity", "expected count"),
        "m09-path-trapping": ("path become trapped", "run out of moves", "available neighbouring sites"),
        "m10-coalescence": ("particles merging", "particles merge", "same location"),
        "m10-coalescence-time": ("how long merging takes", "time until all", "merging time"),
    }
    SWEDISH_MARKERS = (
        "och", "är", "vad", "varför", "hur", "förklara", "jämför", "visa", "visa mig", "med", "en", "ett", "sätt", "till", "ändrades",
        "väntetid", "fördelning", "sannolikhet", "stationär", "brownsk", "poissonprocess", "markovkedja",
    )
    ENGLISH_MARKERS = (
        "what", "why", "how", "explain", "compare", "show", "set", "give", "define", "does", "is", "are",
        "the", "with", "using", "course", "process", "distribution", "waiting", "property", "changed",
    )
    GENERAL_CHAT_MARKERS = (
        "你好",
        "您好",
        "在吗",
        "在不在",
        "嗨",
        "hello",
        "hi",
        "你叫什么",
        "你是谁",
        "介绍一下你自己",
        "你能做什么",
        "怎么用",
        "如何使用",
        "这个项目",
        "这个agent",
        "这个 agent",
        "这门课",
        "课程概览",
        "这门课学什么",
        "第一个module",
        "第一个 module",
        "第一个模块",
        "第一模块",
        "第1个module",
        "第1个 module",
        "随机过程是什么",
        "什么是随机过程",
        "技术栈",
        "架构",
        "rag",
        "agent",
        "随机过程课程介绍",
        "教学agent",
        "教学 agent",
    )
    SIMULATION_MARKERS = (
        "simulate",
        "simulation",
        "run ",
        "plot",
        "visualize",
        "模拟",
        "仿真",
        "运行",
        "画图",
        "绘图",
        "show ",
        "visualise",
        "simulera",
        "simulering",
        "visa mig",
        "visa resultatet",
        "给我看看",
        "显示结果",
        "运行它",
    )

    def __init__(self, memory: LearnerMemory | None = None) -> None:
        self.config = runtime_config()
        self.knowledge = KnowledgeBase(config=self.config)
        self.llm = OpenAICompatibleLLM(config=self.config)
        self.memory = memory or LearnerMemory()
        self.curriculum = curriculum_catalog()
        self.experiments = ExperimentRegistry()
        self.curriculum_agent = CurriculumAgent(self.curriculum)
        self.assessment_agent = AssessmentAgent()
        self.tutor_agent = TutorAgent()
        self._concepts = [
            {**point, "module_id": module["module_id"]}
            for module in self.curriculum["modules"]
            for point in module["knowledge_points"]
        ]
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
        # The graph is the orchestration boundary. Domain node methods remain
        # here so retrieval, memory, tools and response contracts stay stable.
        self.workflow = build_graph(self)

    @classmethod
    def detect_query_language(cls, question: str, ui_language: str = "en") -> str:
        """Detect the learner's language without making UI language authoritative."""

        text = str(question or "")
        if re.search(r"[\u3400-\u9fff]", text):
            return "zh"
        lowered = text.casefold()
        lexical = {item for item in re.findall(r"[a-zåäö]+", lowered)}
        if lexical.intersection(cls.SWEDISH_MARKERS) or any(
            marker in lowered for marker in ("poissonprocess", "väntetid", "stationär", "brownsk", "markovkedja", "fördelad", "markovegenskapen", "ändrades")
        ):
            return "sv"
        if lexical.intersection(cls.ENGLISH_MARKERS):
            return "en"
        return ui_language if ui_language in {"en", "zh", "sv"} else "en"

    @classmethod
    def _language_instruction(cls, language: str) -> str:
        return {
            "en": "Respond in English.",
            "zh": "请用中文回答。保留标准数学符号和 LaTeX，不要翻译公式。",
            "sv": "Svara på svenska. Behåll standardiserad matematisk notation och LaTeX.",
        }.get(language, "Respond in English.")

    @staticmethod
    def _explicit_response_language(question: str) -> str | None:
        lowered = question.casefold()
        if re.search(r"(?:answer|respond|reply)\s+in\s+english|用英语|用英文", lowered):
            return "en"
        if re.search(r"(?:answer|respond|reply)\s+in\s+chinese|用中文|用汉语", lowered):
            return "zh"
        if re.search(r"(?:answer|respond|reply)\s+in\s+swedish|på\s+svenska|用瑞典语", lowered):
            return "sv"
        return None

    @classmethod
    def _translate_fallback(cls, answer: str, language: str) -> str:
        """Translate stable system-owned fallback prose without translating math."""

        if language == "en":
            return answer
        if language == "zh":
            replacements = (
                ("A Poisson process has exponential waiting times because waiting longer than", "泊松过程的等待时间服从指数分布，因为等待超过"),
                ("means that no arrival has occurred by time", "意味着在时刻"), ("A Poisson process counts arrivals over time with independent, stationary increments and rate", "泊松过程以速率"),
                ("For an interval of length", "对于长度为"), ("its first waiting time is exponentially distributed with rate", "它的首次等待时间服从速率为"),
                ("Brownian motion is a continuous process that starts at", "布朗运动是从"), ("has independent stationary increments, and satisfies", "开始、具有独立平稳增量，并满足"),
                ("Its paths are continuous, so uncertainty grows continuously rather than through jumps.", "它的路径连续，因此不确定性是连续增长的，而不是通过跳跃变化。"),
                ("A stationary distribution is a probability vector that remains unchanged after one transition.", "平稳分布是在一次转移后保持不变的概率向量。"), ("For a transition matrix", "对于转移矩阵"), ("together with non-negative entries summing to one.", "并且各分量非负且总和为 1。"),
                ("The exponential distribution is memoryless because the chance of waiting another interval does not depend on how long you have already waited.", "指数分布具有无记忆性，因为再次等待一段时间的概率不取决于已经等待了多久。"),
            )
            for source, target in replacements:
                answer = answer.replace(source, target)
            answer = re.sub(r"\b(?:it satisfies|and its entries are non-negative and sum to one)\b", "满足且各分量非负并总和为 1", answer, flags=re.I)
            return answer
        if language == "sv":
            replacements = (
                ("A Poisson process has exponential waiting times because waiting longer than", "En Poissonprocess har exponentialfördelade väntetider eftersom väntan längre än"),
                ("means that no arrival has occurred by time", "betyder att ingen ankomst har skett vid tiden"), ("A Poisson process counts arrivals over time with independent, stationary increments and rate", "En Poissonprocess räknar ankomster över tid med oberoende, stationära inkrement och intensitet"),
                ("For an interval of length", "För ett intervall med längden"), ("its first waiting time is exponentially distributed with rate", "är den första väntetiden exponentialfördelad med intensiteten"),
                ("Brownian motion is a continuous process that starts at", "Brownsk rörelse är en kontinuerlig process som börjar vid"), ("has independent stationary increments, and satisfies", "har oberoende stationära inkrement och uppfyller"),
                ("Its paths are continuous, so uncertainty grows continuously rather than through jumps.", "Dess banor är kontinuerliga, så osäkerheten växer kontinuerligt i stället för genom hopp."),
                ("A stationary distribution is a probability vector that remains unchanged after one transition.", "En stationär fördelning är en sannolikhetsvektor som förblir oförändrad efter en övergång."), ("For a transition matrix", "För en övergångsmatris"), ("together with non-negative entries summing to one.", "samt icke-negativa komponenter som summerar till 1."),
                ("The exponential distribution is memoryless because the chance of waiting another interval does not depend on how long you have already waited.", "Exponentialfördelningen är minneslös eftersom sannolikheten att vänta ytterligare ett intervall inte beror på hur länge du redan har väntat."),
            )
            for source, target in replacements:
                answer = answer.replace(source, target)
            answer = re.sub(r"\b(?:it satisfies|and its entries are non-negative and sum to one)\b", "uppfyller detta och komponenterna är icke-negativa och summerar till 1", answer, flags=re.I)
            return answer
        return answer

    def _localized_fallback(self, state: AgentState) -> str | None:
        """Return concise multilingual deterministic answers for common course questions."""

        if state.response_language == "en":
            return None
        query = (state.retrieval_query_en or state.question).lower()
        if ("poisson" in query and "waiting" in query) or (
            state.concept_id == "m01-poisson-process" and "exponential" in query
        ):
            if state.response_language == "zh":
                return "泊松过程的等待时间服从指数分布，因为等待超过 $t$ 等价于在时刻 $t$ 之前没有到达。\n\n$N(t)\\sim\\operatorname{Poisson}(\\lambda t)$，且 $P(T>t)=P(N(t)=0)=e^{-\\lambda t}$，所以 $T\\sim\\operatorname{Exp}(\\lambda)$。"
            answer = "En Poissonprocess har exponentialfördelade väntetider eftersom väntan längre än $t$ betyder att ingen ankomst har skett vid tiden $t$.\n\n$N(t)\\sim\\operatorname{Poisson}(\\lambda t)$ och $P(T>t)=P(N(t)=0)=e^{-\\lambda t}$, så $T\\sim\\operatorname{Exp}(\\lambda)$."
        elif "brownian" in query:
            if state.response_language == "zh":
                return "布朗运动是一个从 $B(0)=0$ 开始的连续过程，具有独立平稳增量，并满足 $B(t)\\sim N(0,t)$。它的样本路径是连续的。"
            answer = "Brownsk rörelse är en kontinuerlig process som börjar vid $B(0)=0$, har oberoende stationära inkrement och uppfyller $B(t)\\sim N(0,t)$. Dess banor är kontinuerliga."
        elif "stationary distribution" in query or state.concept_id == "m05-stationary-distribution":
            if state.response_language == "zh":
                return "平稳分布是在一次转移后保持不变的概率向量。对于转移矩阵 $P$，它满足 $\\pi P=\\pi$，且各分量非负并总和为 1。"
            answer = "En stationär fördelning är en sannolikhetsvektor som förblir oförändrad efter en övergång. För en övergångsmatris $P$ gäller $\\pi P=\\pi$, och komponenterna är icke-negativa och summerar till 1."
        elif "memoryless" in query:
            if state.response_language == "zh":
                return "指数分布具有无记忆性，因为再次等待一段时间的概率不取决于已经等待了多久。"
            answer = "Exponentialfördelningen är minneslös eftersom sannolikheten att vänta ytterligare ett intervall inte beror på hur länge du redan har väntat."
        elif "random walk" in query and "self-avoiding" in query:
            if state.response_language == "zh":
                return "普通随机游走使用固定的增量规则，而自避免游走还取决于已经访问过的格点。访问集合会限制下一步，并可能使路径受困。"
            answer = "En vanlig random walk använder en fast inkrementregel, medan en självundvikande vandring också beror på tidigare besökta platser. Den besökta mängden kan begränsa nästa steg och få vägen att fastna."
        else:
            return None
        return answer if state.response_language == "sv" else self._translate_fallback(answer, state.response_language)

    @classmethod
    def _translate_retrieval_query(cls, question: str, language: str) -> tuple[str, bool]:
        """Map common multilingual course terms to English retrieval vocabulary."""

        if language == "en":
            return question, False
        replacements = {
            "为什么": "why", "什么是": "what is", "解释": "explain", "比较": "compare",
            "服从": "follows", "等待时间": "waiting time", "指数": "exponential",
            "泊松过程": "Poisson process", "等待时间": "waiting time", "指数分布": "exponential distribution",
            "布朗运动": "Brownian motion", "平稳分布": "stationary distribution", "马尔可夫链": "Markov chain",
            "生成矩阵": "generator matrix", "停留时间": "holding time", "自避免游走": "self-avoiding walk",
            "粒子合并": "coalescing particles", "大数定律": "law of large numbers",
            "poissonprocess": "Poisson process", "poissonprocessen": "Poisson process",
            "väntetiden": "waiting time", "väntetider": "waiting times", "väntetid": "waiting time", "exponentialfördelad": "exponential distribution", "betyder": "means", "för": "for",
            "brownsk rörelse": "Brownian motion", "stationär fördelning": "stationary distribution",
            "markovkedja": "Markov chain", "generatormatris": "generator matrix", "uppehållstid": "holding time", "pi": "pi",
            "självundvikande vandring": "self-avoiding walk", "koalescerande partiklar": "coalescing particles",
            "lagen om stora tal": "law of large numbers", "varför": "why", "vad är": "what is",
            "förklara": "explain", "jämför": "compare", "är": "is", "och": "and", "vad": "what", "varför": "why", "hur": "how", "sätt": "set", "till": "to", "ändrades": "changed",
            "är": "is", "är": "is", "och": "and", "vad": "what", "varför": "why", "hur": "how",
        }
        translated = question
        for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            translated = re.sub(re.escape(source), target, translated, flags=re.IGNORECASE)
        translated = re.sub(
            r"(?<=[A-Za-z])(?=(?:Poisson|waiting|wait|exponential|distribution|process|Brownian|stationary|Markov|holding|generator|self-avoiding|coalescing))",
            " ", translated, flags=re.IGNORECASE,
        )
        translated = re.sub(r"(?<=[A-Za-z])(?=的|服从|为什么|是什么)", " ", translated)
        translated = re.sub(r"[?？]", "?", translated)
        translated = re.sub(r"\s+", " ", translated).strip()
        return translated, translated != question

    def _tool_parameters(self, tool_key: str | None) -> list[dict[str, Any]]:
        if not tool_key or tool_key not in self.tools:
            return []
        return [
            {
                "name": parameter.name,
                "required": parameter.default is inspect.Parameter.empty,
                **({} if parameter.default is inspect.Parameter.empty else {"default": parameter.default}),
            }
            for parameter in inspect.signature(self.tools[tool_key]).parameters.values()
        ]

    def _experiment_summary(self, item: dict[str, Any]) -> dict[str, Any]:
        return self.experiments.summary(
            item, self._tool_parameters(item.get("simulation_engine"))
        )

    def _find_experiments(self, state: AgentState, *, limit: int = 2) -> list[dict[str, Any]]:
        concept_id = state.concept_id
        lowered = (state.retrieval_query_en or state.question).lower()
        # A rate/lambda question concerns the continuous-time Poisson waiting
        # experiment, even when lexical routing also sees the discrete
        # geometric-waiting knowledge point.
        if "waiting" in lowered and any(term in lowered for term in ("lambda", "rate", "intensity", "\u03bb")):
            concept_id = "m01-poisson-process"
        return self.experiments.find_experiments(
            module_id=state.module_id,
            concept_id=concept_id,
            query=state.question,
            limit=limit,
        )

    def _llm_metadata(self) -> dict[str, object]:
        """Read safe provider metadata while allowing lightweight test doubles."""

        last_request = getattr(self.llm, "last_request", None)
        if callable(last_request):
            return dict(last_request())
        stats = getattr(self.llm, "stats", None)
        snapshot = stats() if callable(stats) else {}
        return {
            "provider": snapshot.get("provider"),
            "model": snapshot.get("model"),
            "status": "disabled" if not getattr(self.llm, "enabled", False) else "unknown",
            "retry_count": 0,
            "latency_ms": 0.0,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
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
            label_pattern = re.escape(label)
            if label.isascii() and label.isalpha():
                label_pattern = rf"(?<![A-Za-z]){label_pattern}(?![A-Za-z])"
            pattern = (
                rf"(?:{label_pattern})\s*"
                rf"(?:为|=|:|是|改成|改为|调整为|设为|设置为|to|till)?\s*"
                rf"({StochasticTutorAgent.NUMBER_PATTERN})"
            )
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                reverse_pattern = (
                    rf"({StochasticTutorAgent.NUMBER_PATTERN})\s*"
                    rf"(?:个|条)?\s*(?:{label_pattern})"
                )
                match = re.search(reverse_pattern, text, flags=re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if not math.isfinite(value):
                    raise ValueError(f"{label} must be finite")
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
            label_pattern = re.escape(label)
            if label.isascii() and label.isalpha():
                label_pattern = rf"(?<![A-Za-z]){label_pattern}(?![A-Za-z])"
            forward = (
                rf"(?:{label_pattern})\s*"
                rf"(?:为|=|:|是|改成|改为|调整为|设为|设置为|to|till)?\s*"
                rf"{cls.NUMBER_PATTERN}"
            )
            reverse = (
                rf"{cls.NUMBER_PATTERN}\s*(?:个|条)?\s*(?:{label_pattern})"
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
        # Kept as a compatibility shim for callers of the former private
        # helper. Student-facing responses use the English implementation.
        return StochasticTutorAgent._summary_english(topic, result)

    @staticmethod
    def _summary_english(topic: str, result: dict[str, Any]) -> str:
        if topic == "monte_carlo":
            return f"Using {result['parameters']['samples']} samples gives π≈{result['estimate']}; the absolute error is {result['absolute_error']}."
        if topic == "bernoulli":
            return f"The empirical count mean is {result['empirical_count_mean']} versus theoretical np={result['theoretical_count_mean']}; the empirical waiting mean is {result['empirical_waiting_mean']} versus 1/p={result['theoretical_waiting_mean']}."
        if topic == "poisson":
            return f"The empirical mean event count is {result['empirical_mean_count']} versus theoretical λT={result['theoretical_mean_count']}; absolute error={result['absolute_error']}."
        if topic == "random_walk":
            return f"The endpoint mean is {result['empirical_endpoint_mean']} versus {result['theoretical_endpoint_mean']}; variance is {result['empirical_endpoint_variance']} versus {result['theoretical_endpoint_variance']}."
        if topic == "continuous_random_walk":
            return f"The mean jump count is {result['empirical_jump_mean']} versus λT={result['theoretical_jump_mean']}; endpoint mean and variance are {result['empirical_endpoint_mean']} and {result['empirical_endpoint_variance']}."
        if topic == "brownian_motion":
            return f"The terminal empirical mean is {result['empirical_terminal_mean']} and variance is {result['empirical_terminal_variance']}; theory gives mean 0 and variance T={result['theoretical_terminal_variance']}."
        if topic == "markov_chain":
            return f"Empirical state frequencies are {result['empirical_frequencies']}; the stationary distribution is {result['stationary_distribution']}; L1 error={result['l1_error']}."
        if topic in {"ctmc", "birth_death"}:
            return f"Empirical state probabilities are {result['empirical_state_probabilities']}; the theoretical stationary distribution is {result['stationary_distribution']}; L1 error={result['l1_error']}."
        if topic == "reliability":
            return f"Mean lifetime is {result['empirical_series_mean_lifetime']} for the series system and {result['empirical_parallel_mean_lifetime']} for the parallel system; theoretical values are {result['theoretical_series_mean_lifetime']} and {result['theoretical_parallel_mean_lifetime']}."
        if topic == "buffer":
            return f"Mean arrivals per slot are {result['empirical_arrivals_per_slot']} versus {result['theoretical_arrivals_per_slot']}; mean final buffer size is {result['empirical_mean_final_buffer']}."
        if topic == "mm1_queue":
            if result["stable"]:
                return f"Traffic intensity ρ={result['traffic_intensity']}<1, so the queue is stable. Mean customers are {result['empirical_mean_customers']} versus theoretical {result['theoretical_mean_customers']}."
            return f"Traffic intensity ρ={result['traffic_intensity']}≥1, so no stationary geometric distribution exists; the finite-run mean is {result['empirical_mean_customers']}."
        if topic == "nhpp":
            return f"Thinning generated {result['candidate_count']} candidates with acceptance rate {result['acceptance_rate']}; empirical mean count={result['empirical_mean_count']} versus theoretical {result['theoretical_mean_count']}."
        if topic == "self_avoiding_walk":
            return f"{result['trapped_runs']} of {result['parameters']['runs']} paths became trapped; trapping rate={result['trapping_rate']} and mean stopping length={result['average_stopping_length']}."
        if topic == "coalescing_particles":
            return f"{result['completed_runs']} of {result['parameters']['runs']} runs fully coalesced; mean coalescence time={result['average_coalescence_time']} and median={result['median_coalescence_time']}."
        return "The simulation completed and can be compared with the retrieved course evidence."

    @staticmethod
    def _guiding_question(topic: str, language: str = "en") -> str:
        questions = {
            "monte_carlo": "What happens to the estimate as the sample size grows?",
            "bernoulli": "How would a lower event probability affect the count and first waiting time?",
            "poisson": "How would increasing the rate change the expected event count?",
            "discrete_random_walk": "How would changing the up-step probability affect the endpoint mean?",
            "continuous_random_walk": "How would increasing the jump rate affect the number of jumps?",
            "brownian_motion": "What variance do you expect at the terminal time?",
            "discrete_markov_chain": "How do empirical state frequencies compare with the stationary distribution?",
            "continuous_markov_chain": "What happens to the long-run state probabilities when a transition rate changes?",
            "birth_death": "How do birth and death rates shape the long-run state distribution?",
            "reliability": "Why is a parallel-system lifetime a maximum while a series-system lifetime is a minimum?",
            "buffer": "What long-run trend would you expect when mean arrivals exceed service capacity?",
            "mm1_queue": "Why does the mean queue length grow quickly as the arrival rate approaches the service rate?",
            "nhpp": "What changes if the intensity peak is moved later in time?",
            "self_avoiding_walk": "Why is the current position alone not enough to determine the next step?",
            "coalescing_particles": "How might the coalescence time change if the circle grows but particle count stays fixed?",
        }
        question = questions.get(
            topic,
            "What would you expect if the number of samples or paths were multiplied by four?",
        )
        if language == "zh":
            return {
                "What happens to the estimate as the sample size grows?": "样本量增加时估计值会怎样变化？",
                "How would increasing the rate change the expected event count?": "提高速率会如何改变期望事件数？",
                "How would changing the up-step probability affect the endpoint mean?": "改变向上步概率会如何影响终点均值？",
                "How would increasing the jump rate affect the number of jumps?": "提高跳跃率会如何影响跳跃次数？",
                "What variance do you expect at the terminal time?": "你预计终点时刻的方差是多少？",
                "How do empirical state frequencies compare with the stationary distribution?": "经验状态频率与平稳分布有何差异？",
                "What happens to the long-run state probabilities when a transition rate changes?": "改变转移率时长期状态概率会怎样变化？",
                "How do birth and death rates shape the long-run state distribution?": "出生率和死亡率如何决定长期状态分布？",
                "What would you expect if the number of samples or paths were multiplied by four?": "如果样本数或路径数增加到四倍，你预计会发生什么？",
                "Why does the mean queue length grow quickly as the arrival rate approaches the service rate?": "为什么到达率接近服务率时平均队列长度会快速增长？",
            }.get(question, question)
        if language == "sv":
            return {
                "What happens to the estimate as the sample size grows?": "Vad händer med skattningen när stickprovsstorleken ökar?",
                "How would increasing the rate change the expected event count?": "Hur skulle en högre intensitet ändra det förväntade antalet händelser?",
                "How would changing the up-step probability affect the endpoint mean?": "Hur skulle en ändrad uppstegssannolikhet påverka slutpunktens medelvärde?",
                "How would increasing the jump rate affect the number of jumps?": "Hur skulle en högre hoppintensitet påverka antalet hopp?",
                "What variance do you expect at the terminal time?": "Vilken varians förväntar du dig vid sluttiden?",
                "How do empirical state frequencies compare with the stationary distribution?": "Hur jämförs de empiriska tillståndsfrekvenserna med den stationära fördelningen?",
                "What happens to the long-run state probabilities when a transition rate changes?": "Vad händer med de långsiktiga tillståndssannolikheterna när en övergångsintensitet ändras?",
                "How do birth and death rates shape the long-run state distribution?": "Hur formar födelse- och dödsintensiteterna den långsiktiga tillståndsfördelningen?",
                "What would you expect if the number of samples or paths were multiplied by four?": "Vad förväntar du dig om antalet stickprov eller vägar fyrdubblas?",
                "Why does the mean queue length grow quickly as the arrival rate approaches the service rate?": "Varför växer den genomsnittliga kölängden snabbt när ankomstintensiteten närmar sig serviceintensiteten?",
            }.get(question, question)
        return question

    def _node_classify(self, state: AgentState) -> NodeOutcome:
        state.routing_strategy = "EXACT"
        state.routing_candidates = []
        state.routing_confidence = None
        state.selected_routing_reason = ""
        state.detected_query_language = self.detect_query_language(state.question, state.ui_language)
        if state.previous_turn and self._is_explicit_follow_up(state.question):
            prior_question = str(state.previous_turn.get("question") or "")
            if prior_question and not re.search(r"[\u3400-\u9fff]", state.question) and not any(
                marker in state.question.casefold() for marker in ("what", "why", "how", "explain", "compare", "show", "set", "give", "vad", "varför", "hur", "förklara", "jämför", "visa", "sätt", "ändra", "什么", "为什么", "解释", "比较", "显示", "设置")
            ):
                state.detected_query_language = self.detect_query_language(prior_question, state.ui_language)
        state.response_language = self._explicit_response_language(state.question) or state.detected_query_language
        state.retrieval_query_en, state.translation_applied = self._translate_retrieval_query(
            state.question, state.detected_query_language
        )
        # Assessment handoffs already carry a validated module and intent. Do
        # not reinterpret the synthetic quiz question as a concept query.
        if state.intent in {"quiz", "practice"} and state.assessment_input:
            if state.module_id in MODULE_BY_ID:
                state.module = MODULE_BY_ID[state.module_id]
                state.topic = state.module.topic
            state.answerability_status = "SUPPORTED"
            return NodeOutcome("assessment result routed to learning agents")
        if self._is_course_navigation(state.question) and not self._is_simulation_request(state.question):
            state.intent = "course_navigation"
            state.module_id = self._navigation_module_id(state.question)
            if state.module_id:
                state.module = MODULE_BY_ID[state.module_id]
                state.topic = state.module.topic
                return NodeOutcome(f"course navigation: Module {state.module.number:02d}")
            return NodeOutcome("course overview navigation")

        routing_question = " ".join(
            item for item in (state.question, state.retrieval_query_en) if item
        )
        # Curriculum titles/aliases are authoritative when they are explicit.
        # This prevents broad words such as “reliability” or “particle” from
        # stealing a more specific knowledge point from another module.
        exact_concept = self._exact_curriculum_concept(state.question)
        detected_modules = self._detect_module_ids(state.question)
        if not detected_modules:
            detected_modules = self._detect_module_ids(routing_question)
        strong_module = self._strong_module_override(state.question)
        if strong_module and exact_concept and str(exact_concept.get("module_id")) != strong_module:
            # Specialized experiment wording outranks a broad concept alias
            # (for example continuous-time random walk vs random walk).
            exact_concept = None
        if strong_module:
            detected_modules = [strong_module, *[item for item in detected_modules if item != strong_module]]
        state.comparison_module_ids = (
            detected_modules if self._is_comparison(state.question) else []
        )
        state.module_id = (
            str(exact_concept.get("module_id"))
            if exact_concept
            else detected_modules[0]
            if detected_modules
            else self.classify_module(state.question)
        )
        if strong_module and not exact_concept:
            state.module_id = strong_module
        if state.requested_concept_id in self.curriculum_agent.concepts:
            state.module_id = str(self.curriculum_agent.concepts[state.requested_concept_id]["module_id"])
        if state.comparison_module_ids:
            state.concept_id = None
            state.comparison_concept_ids = [
                concept_id
                for module_id in state.comparison_module_ids
                for concept_id in [self._match_concept(state.question, module_id)]
                if concept_id is not None
            ]
        else:
            requested = state.requested_concept_id
            state.concept_id = (
                requested
                if requested in self.curriculum_agent.concepts
                else str(exact_concept["id"])
                if exact_concept
                else self._match_concept(routing_question, state.module_id)
            )
            if state.module_id == "module01" and "waiting" in state.retrieval_query_en and "exponential" in state.retrieval_query_en and "geometric" not in state.retrieval_query_en:
                state.concept_id = "m01-poisson-process"
            state.comparison_concept_ids = []
        if strong_module and not exact_concept:
            state.module_id = strong_module
            state.concept_id = self._match_concept(routing_question, strong_module)
        # A Knowledge Point title is authoritative curriculum metadata.  If
        # lexical module matching misses a title variant (for example,
        # "survival and hazard functions"), recover its owning module before
        # deciding whether the question is out of scope.
        if state.module_id is None and state.concept_id:
            concept = next(
                (point for point in self._concepts if point["id"] == state.concept_id),
                None,
            )
            if concept and concept.get("module_id") in MODULE_BY_ID:
                state.module_id = str(concept["module_id"])
        explicit_follow_up = self._is_explicit_follow_up(state.question)
        # Follow-ups inherit the active experiment before broad numeric words
        # such as "500 steps" can be mistaken for another module.
        if explicit_follow_up and state.active_experiment_id:
            active = self.experiments.get(state.active_experiment_id)
            if active and active.get("module_id") in MODULE_BY_ID:
                state.module_id = str(active["module_id"])
                state.module_from_context = True
                state.module = MODULE_BY_ID[state.module_id]
                state.topic = state.module.topic
        if state.module_id is None and state.active_experiment_id and (explicit_follow_up or self._is_active_experiment_question(state)) and not self._unsupported_experiment_parameter(state.question):
            active = self.experiments.get(state.active_experiment_id)
            if active:
                state.module_id = str(active["module_id"])
                state.module_from_context = True
        if state.module_id is None and state.previous_turn and explicit_follow_up:
            state.module_id = state.previous_turn["module_id"]
            state.module_from_context = True
            state.module = MODULE_BY_ID.get(state.module_id)
            state.topic = state.module.topic if state.module else None
        if state.module_id is None and state.requested_concept_id in self.curriculum_agent.concepts:
            requested_point = self.curriculum_agent.concepts[state.requested_concept_id]
            state.module_id = str(requested_point["module_id"])
            state.module_from_context = True
        if state.module_id is not None:
            state.module = MODULE_BY_ID[state.module_id]
            state.topic = state.module.topic
        # If lexical routing is absent or concept confidence is weak, use a
        # bounded candidate set. Evidence helps choose among candidates; it
        # is never treated as student-visible answer or gold metadata.
        if not exact_concept and not state.requested_concept_id:
            candidates = self._candidate_concept_routes(
                routing_question,
                # A broad module keyword is not strong enough to constrain
                # disambiguation; only an explicit concept may scope it.
                module_hint=(strong_module or (None if state.concept_id is None else state.module_id)),
                limit=3,
            )
            state.routing_candidates = candidates
            if candidates:
                best = candidates[0]
                second = candidates[1] if len(candidates) > 1 else None
                state.routing_confidence = round(
                    float(best.get("routing_score", 0.0))
                    / max(1.0, float(best.get("routing_score", 0.0)) + float(second.get("routing_score", 0.0)) if second else 1.0),
                    3,
                )
                weak_existing = state.concept_id is None or (
                    second is not None
                    and float(best.get("routing_score", 0.0)) - float(second.get("routing_score", 0.0)) < 10
                )
                # A concept-tagged hit is a useful disambiguator even when
                # dense evidence scores are fractional.  Keep the gate
                # bounded: require both a meaningful evidence signal and a
                # non-trivial lexical/cue score, rather than accepting every
                # weak global match.
                if weak_existing and float(best.get("evidence_score", 0.0)) >= 0.05 and float(best.get("routing_score", 0.0)) >= 8.0:
                    state.module_id = str(best["module_id"])
                    state.concept_id = str(best["concept_id"])
                    state.module = MODULE_BY_ID.get(state.module_id)
                    state.topic = state.module.topic if state.module else None
                    state.routing_strategy = "CANDIDATE_DISAMBIGUATION"
                    state.selected_routing_reason = "bounded curriculum/evidence candidate scoring"
            elif state.module_id or state.concept_id:
                state.routing_strategy = "HIGH_CONFIDENCE"
        elif exact_concept:
            state.routing_strategy = "EXACT"
            state.routing_confidence = 1.0
            state.selected_routing_reason = "explicit curriculum title or alias"
        if state.module_from_context and state.concept_id is None:
            saved_concept = self.memory.context(state.session_id).get("related_concept_id")
            if saved_concept:
                state.concept_id = str(saved_concept)
        if explicit_follow_up and state.active_experiment_id:
            active = self.experiments.get(state.active_experiment_id)
            if active and active.get("module_id") in MODULE_BY_ID:
                state.module_id = str(active["module_id"])
                state.module = MODULE_BY_ID[state.module_id]
                state.topic = state.module.topic
                state.module_from_context = True
        if state.active_experiment_id and state.requested_experiment_id is None:
            active_experiment = self.experiments.get(state.active_experiment_id)
            if active_experiment and active_experiment.get("module_id") == state.module_id:
                state.requested_experiment_id = state.active_experiment_id
        if self._unsupported_experiment_parameter(state.question):
            state.intent = "unsupported"
            state.module = None
            state.module_id = None
            state.topic = None
        elif state.action_type == "simulation":
            state.intent = "simulation" if state.module else "unsupported"
        elif self._is_simulation_request(state.question, explicit_follow_up) or self._is_active_simulation_handoff(state):
            state.intent = "simulation" if state.module else "unsupported"
        elif self._is_general_conversation(state.question):
            state.intent = "unsupported"
        else:
            state.intent = "concept"
        if (
            state.module is None
            and state.intent == "concept"
            and not self._is_supported_global_concept(state.question)
        ):
            state.intent = "unsupported"
        if state.intent == "concept":
            state.concept_sub_intent = self._detect_concept_sub_intent(state.question)
            if state.concept_id:
                personalization = self.curriculum_agent.decide(
                    current_module_id=state.module_id,
                    current_concept_id=state.concept_id,
                    profile=state.profile,
                    learning_mode="concept",
                )
                state.curriculum_decision = personalization.to_dict()
                state.teaching_mode = str(personalization.teaching_mode or "FOUNDATION")
                state.current_concept_mastery = next(
                    (item for item in state.profile.get("knowledge_points", []) if item.get("concept_id") == state.concept_id),
                    {"concept_id": state.concept_id, "status": "NOT_STARTED", "mastery_score": 0.0, "attempt_count": 0, "hint_count": 0},
                )
                point = self.curriculum_agent.concepts.get(state.concept_id, {})
                state.prerequisite_mastery = {
                    prerequisite: self.curriculum_agent._mastery(state.profile, prerequisite)
                    for prerequisite in point.get("prerequisites", [])
                }
                state.recommendation = recommend_next_knowledge_point(
                    self.curriculum_agent, state.profile, state.response_language, decision=personalization
                )
        if state.requested_experiment_id:
            requested = self.experiments.get(state.requested_experiment_id)
            if requested and requested.get("module_id") == state.module_id:
                state.concept_id = state.concept_id or requested.get("concept_id")
        state.question_requirements = self._analyze_question_requirements(state.question)
        if state.module_id == "module01" and "waiting" in state.retrieval_query_en and "exponential" in state.retrieval_query_en and "geometric" not in state.retrieval_query_en:
            state.question_requirements["concepts"] = ["m01-poisson-process"]
            state.question_requirements["concept_titles"] = ["Poisson process"]
            state.concept_id = "m01-poisson-process"
        if state.intent == "unsupported":
            state.answerability_status = "OUT_OF_SCOPE"
        elif state.intent == "course_navigation":
            state.answerability_status = "SUPPORTED"
        if state.module is None:
            if state.intent == "simulation":
                state.intent = "unsupported"
                return NodeOutcome("simulation request needs a named course model")
            return NodeOutcome("global concept or scope question")
        detail = f"Module {state.module.number:02d}: {state.module.label}; {state.intent}"
        if state.module_from_context:
            detail += " (inherited from previous turn)"
        return NodeOutcome(detail)

    @staticmethod
    def _is_show_handoff(question: str) -> bool:
        lowered = question.lower().strip().rstrip(".!?")
        return lowered in {
            "show me", "run it", "visualize it", "visualise it", "try it", "do it", "show the result",
            "visa mig", "visa resultatet", "kör den", "kör igen", "visa det", "visa",
            "显示结果", "给我看看", "看看", "运行它",
        }

    def _is_active_simulation_handoff(self, state: AgentState) -> bool:
        if not state.active_experiment_id:
            return False
        active = self.experiments.get(state.active_experiment_id)
        if active and state.module_id and active.get("module_id") != state.module_id:
            return False
        if self._is_show_handoff(state.question):
            return True
        if any(self._parameter_mentioned(key, state.question) for key in self.PARAMETER_LABELS):
            return True
        return bool(re.search(r"\b(?:rerun|re-run|run again|try)\b", state.question.lower()))

    def _is_active_experiment_question(self, state: AgentState) -> bool:
        if not state.active_experiment_id:
            return False
        lowered = state.question.lower()
        return any(
            marker in lowered
            for marker in ("what changed", "what should i notice", "explain this graph", "explain the result", "interpret this", "vad ändrades", "vad förändrades", "vad ska jag lägga märke till", "förklara resultatet", "有什么变化", "发生了什么变化")
        )

    @staticmethod
    def _unsupported_experiment_parameter(question: str) -> bool:
        lowered = question.lower()
        # "obstacle" is a valid Module 09 experiment request.  Only reject
        # unsupported custom parameters, not the course's registered obstacle
        # interpretation.
        if "obstacle" in lowered or "blocked site" in lowered:
            return False
        return any(term in lowered for term in ("arbitrary code", "python code"))

    def _node_retrieve(self, state: AgentState) -> NodeOutcome:
        state.retrieval_query = state.retrieval_query_en or state.question
        if (
            state.module_from_context
            and state.previous_turn
            and state.previous_turn["tool"]
        ):
            previous_tool = state.previous_turn["tool"]
            state.retrieval_query += " " + self.RETRIEVAL_HINTS.get(
                previous_tool, previous_tool
            )
        state.question_requirements = self._analyze_question_requirements(state.question)
        if state.module_id == "module01" and "waiting" in state.retrieval_query_en and "exponential" in state.retrieval_query_en and "geometric" not in state.retrieval_query_en:
            state.question_requirements["concepts"] = ["m01-poisson-process"]
            state.question_requirements["concept_titles"] = ["Poisson process"]
        if state.latest_result_summary:
            state.question_requirements["latest_result_summary"] = state.latest_result_summary
        state.retrieval_rounds = 0
        state.sources = self._retrieve_for_state(state, state.retrieval_query)
        state.retrieval_rounds = 1
        self._update_answerability(state)

        mode = state.sources[0]["retrieval_mode"] if state.sources else "no_results"
        return NodeOutcome(
            f"{len(state.sources)} source-aware notes via {mode}; "
            f"answerability={state.answerability_status}, rounds={state.retrieval_rounds}"
        )

    def _retrieve_for_state(self, state: AgentState, query: str) -> list[dict[str, Any]]:
        """Retrieve for one bounded round while preserving comparison behavior."""

        if state.comparison_module_ids:
            merged: list[dict[str, Any]] = []
            seen_sources: set[str] = set()
            for module_id in state.comparison_module_ids:
                for source in self.knowledge.retrieve(
                    query,
                    topic=MODULE_BY_ID[module_id].topic,
                    module_id=module_id,
                    limit=3,
                ):
                    if source["source"] not in seen_sources:
                        seen_sources.add(source["source"])
                        merged.append(source)
            return merged[:6]
        sources, expansion = self.knowledge.retrieve_with_context(
            query,
            topic=state.topic,
            module_id=state.module_id,
            concept_id=state.concept_id,
            limit=4,
        )
        state.question_requirements["retrieval_context"] = expansion
        return sources

    def _analyze_question_requirements(self, question: str) -> dict[str, Any]:
        """Extract small stochastic-process-specific requirements deterministically."""

        lowered = question.lower().replace("‑", "-").replace("–", "-")
        concepts: list[str] = []
        concept_titles: list[str] = []
        for concept in self._concepts:
            aliases = self.CONCEPT_ALIASES.get(concept["id"], ())
            if any(alias in lowered for alias in (concept["title"].lower(), *aliases)):
                concepts.append(concept["id"])
                concept_titles.append(concept["title"])

        groups: list[dict[str, Any]] = []
        user_groups: list[dict[str, Any]] = []
        if "poisson" in lowered and any(
            term in lowered for term in ("waiting", "wait", "interarrival", "arrival time")
        ):
            groups.extend(
                [
                    {"label": "Poisson process", "terms": ["poisson process", "poisson"]},
                    {"label": "waiting or interarrival time", "terms": ["waiting time", "waiting", "interarrival"]},
                    {"label": "exponential waiting-time law", "terms": ["exponential"]},
                ]
            )
        elif "poisson" in lowered:
            groups.extend(
                [
                    {"label": "Poisson process", "terms": ["poisson process", "poisson"]},
                    {"label": "independent increments or counts", "terms": ["independent increment", "independent increments", "count", "n(t)"]},
                ]
            )
        if "memoryless" in lowered:
            groups.extend(
                [
                    {"label": "exponential distribution", "terms": ["exponential"]},
                    {"label": "memoryless property", "terms": ["memoryless", "lack of memory"]},
                ]
            )
        if "brownian" in lowered:
            groups.extend(
                [
                    {"label": "Brownian motion", "terms": ["brownian"]},
                    {"label": "continuous paths or increments", "terms": ["continuous", "increment"]},
                    {"label": "normal terminal distribution", "terms": ["normal", "gaussian", "n(0,t)"]},
                ]
            )
        if "strict stationarity" in lowered or "weak stationarity" in lowered:
            groups.extend(
                [
                    {"label": "strict stationarity", "terms": ["strict stationarity"]},
                    {"label": "weak stationarity", "terms": ["weak stationarity", "covariance", "constant mean"]},
                ]
            )
        if "random walk" in lowered and "self-avoid" in lowered:
            groups.extend(
                [
                    {"label": "ordinary random walk", "terms": ["random walk"]},
                    {"label": "self-avoiding walk", "terms": ["self-avoiding", "self avoiding", "visited set"]},
                ]
            )
        if "hitting time" in lowered and any(
            marker in lowered for marker in ("exact", "formula", "result", "calculate", "compute")
        ):
            for label, terms in (
                ("initial state", ["initial", "start", "starting"]),
                ("target or hitting set", ["target", "hitting set", "level"]),
                ("step or transition probabilities", ["probability", "drift", "transition", "step probability"]),
                ("boundary conditions (if confined)", ["boundary", "absorbing", "reflecting", "finite interval", "barrier"]),
            ):
                user_groups.append({"label": label, "terms": terms})

        # A valid course keyword can coexist with a non-course policy claim.
        # Keep that condition explicit so a Poisson hit cannot answer it.
        if "poisson" in lowered and any(
            marker in lowered for marker in ("external contractor", "taxi", "travel expense", "reimburse", "claim")
        ):
            groups.extend(
                [
                    {"label": "external-contractor eligibility", "terms": ["external contractor", "contractor"]},
                    {"label": "travel or taxi reimbursement rule", "terms": ["travel", "taxi", "reimburse", "expense"]},
                ]
            )

        relation = None
        if self._is_comparison(question):
            relation = "comparison"
        elif any(marker in lowered for marker in (" imply ", " depends on ", " consequence", " can .* answer")):
            relation = "implication"
        target_quantity = next(
            (term for term in ("hitting time", "waiting time", "stationary distribution", "variance", "mean", "probability") if term in lowered),
            None,
        )
        assumptions = [
            marker
            for marker in ("initial state", "starting point", "boundary", "rate", "horizon", "capacity", "probability")
            if marker in lowered
        ]
        return {
            "concepts": concepts,
            "concept_titles": concept_titles,
            "sub_intent": self._detect_concept_sub_intent(question),
            "requested_claim": question.strip(),
            "assumptions": assumptions,
            "target_quantity": target_quantity,
            "relation_between_concepts": relation,
            "requirement_groups": groups,
            "user_requirement_groups": user_groups,
        }

    @staticmethod
    def _source_text(source: dict[str, Any]) -> str:
        return " ".join(
            str(source.get(field, "")) for field in ("title", "content", "claim", "summary")
        ).lower()

    def _update_answerability(self, state: AgentState) -> None:
        """Classify evidence support separately from retrieval relevance."""

        if state.intent == "unsupported":
            state.answerability_status = "OUT_OF_SCOPE"
            state.missing_requirements = []
            state.supporting_source_locators = []
            state.conflicting_source_locators = []
            return
        requirements = state.question_requirements or self._analyze_question_requirements(state.question)
        sources = state.sources
        if not sources:
            state.answerability_status = "NONE"
            state.missing_requirements = [
                group["label"] for group in requirements.get("requirement_groups", [])
            ] or ["course evidence for the requested claim"]
            state.supporting_source_locators = []
            state.conflicting_source_locators = []
            return

        missing: list[str] = []
        corpus = " ".join(self._source_text(source) for source in sources)
        for group in requirements.get("requirement_groups", []):
            if not any(term.lower() in corpus for term in group["terms"]):
                missing.append(group["label"])
        missing_user: list[str] = []
        lowered_question = state.question.lower()
        for group in requirements.get("user_requirement_groups", []):
            if not any(term.lower() in lowered_question for term in group["terms"]):
                missing_user.append(group["label"])
        requirements["missing_user_requirements"] = missing_user
        state.question_requirements = requirements
        state.missing_requirements = missing + missing_user

        supporting: list[str] = []
        for source in sources:
            locator = str(source.get("source") or "")
            text = self._source_text(source)
            if any(
                any(term.lower() in text for term in group["terms"])
                for group in requirements.get("requirement_groups", [])
            ) and locator:
                supporting.append(locator)
        state.supporting_source_locators = list(dict.fromkeys(supporting))
        conflicting = self._detect_conflicting_sources(sources)
        state.conflicting_source_locators = conflicting
        if conflicting:
            state.answerability_status = "CONFLICT"
        elif missing or missing_user:
            state.answerability_status = "PARTIAL"
        elif not state.supporting_source_locators and requirements.get("requirement_groups"):
            state.answerability_status = "NONE"
        else:
            state.answerability_status = "SUPPORTED"

    @staticmethod
    def _detect_conflicting_sources(sources: list[dict[str, Any]]) -> list[str]:
        """Detect explicit material contradictions, not ordinary wording changes."""

        claims: dict[str, dict[str, set[str]]] = {}
        patterns = (
            ("memoryless", r"\bmemoryless\b", r"\b(?:not|isn't|is not)\s+memoryless\b"),
            ("independent_increments", r"\bindependent\s+increments?\b", r"\b(?:not|aren't|are not)\s+independent\s+increments?\b"),
            ("stationary", r"\bstationary\b", r"\b(?:not|isn't|is not)\s+stationary\b"),
        )
        for source in sources:
            locator = str(source.get("source") or "")
            text = StochasticTutorAgent._source_text(source)
            explicit_key = source.get("claim_key")
            explicit_polarity = source.get("claim_polarity")
            if explicit_key and explicit_polarity in {"positive", "negative"}:
                claims.setdefault(str(explicit_key), {"positive": set(), "negative": set()})[str(explicit_polarity)].add(locator)
            for key, positive, negative in patterns:
                if re.search(negative, text, re.I):
                    claims.setdefault(key, {"positive": set(), "negative": set()})["negative"].add(locator)
                elif re.search(positive, text, re.I):
                    claims.setdefault(key, {"positive": set(), "negative": set()})["positive"].add(locator)
        conflicting: list[str] = []
        for claim in claims.values():
            if claim["positive"] and claim["negative"]:
                conflicting.extend(sorted(claim["positive"] | claim["negative"]))
        return list(dict.fromkeys(locator for locator in conflicting if locator))

    def _supplementary_query(self, state: AgentState) -> str:
        expansions = {
            "exponential waiting-time law": "exponential distribution interarrival time P(N(t)=0)",
            "waiting or interarrival time": "waiting time interarrival time survival probability",
            "independent increments or counts": "independent increments count distribution N(t)",
            "continuous paths or increments": "continuous sample paths independent increments",
            "normal terminal distribution": "Gaussian normal distribution B(t) N(0,t)",
            "strict stationarity": "strict stationarity finite-dimensional distributions",
            "weak stationarity": "weak stationarity constant mean covariance lag",
            "external-contractor eligibility": "external contractor eligibility policy",
            "travel or taxi reimbursement rule": "travel taxi reimbursement rule",
        }
        missing = [item for item in state.missing_requirements if item in expansions]
        if not missing:
            query = state.question
        else:
            query = f"{state.question} " + " ".join(expansions[item] for item in missing)
        # Keep supplementary retrieval requirement-driven while making use of
        # the reviewed alias vocabulary for the active knowledge point.
        if state.concept_id:
            spec = self.knowledge.retrieval_aliases.get(state.concept_id, {})
            aliases = [
                *spec.get("aliases", [])[:3],
                *spec.get("notation", [])[:2],
            ]
            if aliases:
                query = f"{query} " + " ".join(str(item) for item in aliases)
        return query

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
        active_handoff = self._is_active_simulation_handoff(state) or bool(
            state.previous_turn
            and state.previous_turn.get("tool") in self.tools
            and self._is_explicit_follow_up(state.question)
            and state.module_from_context
        )
        preferred_tool = (
            state.previous_turn.get("tool")
            if active_handoff and state.previous_turn and state.previous_turn.get("tool") in self.tools
            else self.resolve_tool(state.module_id, default_tool, state.question)
        )
        selected = self.experiments.get(state.requested_experiment_id or state.active_experiment_id) if (active_handoff or state.requested_experiment_id) else None
        if selected is not None and selected.get("simulation_engine") in self.tools:
            preferred_tool = str(selected["simulation_engine"])
        if selected is None:
            matches = self.experiments.find_experiments(
                module_id=state.module_id,
                concept_id=None if state.intent == "simulation" else state.concept_id,
                query=state.question,
                simulation_engine=preferred_tool,
                limit=1,
            )
            if not matches:
                matches = self.experiments.find_experiments(
                    module_id=state.module_id,
                    concept_id=None if state.intent == "simulation" else state.concept_id,
                    query=state.question,
                    limit=1,
                )
            selected = matches[0] if matches else None
        if state.requested_experiment_id:
            requested = self.experiments.get(state.requested_experiment_id)
            if requested and requested.get("module_id") == state.module_id:
                selected = requested
        if selected is not None and selected.get("simulation_engine") != preferred_tool:
            # Some module-level notebook targets (for example reliability in
            # Module 07) share a module with a distinct executable tool.  Do
            # not mislabel the run; the Python tool remains authoritative.
            selected = None
        state.experiment_id = str(selected["experiment_id"]) if selected else None
        state.visualization_id = str(selected.get("visualization_id")) if selected and selected.get("visualization_id") else None
        state.tool_key = str(selected.get("simulation_engine")) if selected else preferred_tool
        # A registry entry, rather than the LLM, owns the executable engine.
        state.tool_key = self.resolve_tool(state.module_id, state.tool_key, state.question)
        state.parameters = self.extract_parameters(state.tool_key, state.question)
        inherited = state.active_parameters if active_handoff else {}
        for key, previous_value in inherited.items():
            if key in state.parameters and not self._parameter_mentioned(key, state.question):
                state.parameters[key] = previous_value
                state.inherited_parameters.append(key)
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
                    if key not in state.inherited_parameters:
                        state.inherited_parameters.append(key)
        detail = f"call {state.tool_key} simulation tool"
        if state.experiment_id:
            detail = f"select {state.experiment_id}; " + detail
        if state.inherited_parameters:
            detail += "; inherited " + ", ".join(
                sorted(state.inherited_parameters)
            )
        return NodeOutcome(detail)

    def _node_tool(self, state: AgentState) -> NodeOutcome:
        if state.tool_key is None:
            raise RuntimeError("plan node did not select a tool")
        try:
            raw_result = self.tools[state.tool_key](**state.parameters)
            state.result = dict(raw_result)
            state.result["experiment_id"] = state.experiment_id
            state.result["visualization_id"] = state.visualization_id
            # Every selected notebook target is projected through the same
            # renderer contract before it reaches the API/frontend.  Existing
            # tool visualizations are preserved; the selected target is added
            # or replaced without changing any simulation values.
            if state.visualization_id:
                native = next(
                    (
                        item
                        for item in state.result.get("visualizations", [])
                        if isinstance(item, dict) and item.get("id") == state.visualization_id
                    ),
                    None,
                )
                if native is not None:
                    native_errors = validate_native_visualization(native)
                    if native_errors:
                        raise ValueError(
                            f"native visualization contract failed for {state.visualization_id}: "
                            + "; ".join(native_errors)
                        )
                else:
                    target = next(
                        (
                            item
                            for item in self.experiments.payload.get("visualizations", [])
                            if item.get("visualization_id") == state.visualization_id
                        ),
                        None,
                    )
                    if target is not None:
                        payload, contract_errors = project_and_validate(target, state.result)
                        if contract_errors:
                            raise ValueError(
                                f"visualization contract failed for {state.visualization_id}: "
                                + "; ".join(contract_errors)
                            )
                        visualizations = [
                            item
                            for item in state.result.get("visualizations", [])
                            if isinstance(item, dict) and item.get("id") != state.visualization_id
                        ]
                        visualizations.append(payload)
                        state.result["visualizations"] = visualizations
            state.verified = True
            state.active_experiment_id = state.experiment_id
            state.active_visualization_id = state.visualization_id
            state.active_parameters = dict(state.parameters)
            state.latest_result_reference = state.experiment_id
            state.latest_result_summary = self._summary_english(state.tool_key, state.result)
            self.memory.save_context(
                session_id=state.session_id,
                active_experiment_id=state.active_experiment_id,
                active_visualization_id=state.active_visualization_id,
                active_parameters=state.active_parameters,
                latest_result_reference=state.latest_result_reference,
                latest_result_summary=state.latest_result_summary,
                related_concept_id=state.concept_id,
            )
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
        state.recommendation = recommend_next_knowledge_point(
            self.curriculum_agent, state.profile, state.response_language
        )
        return NodeOutcome(
            f"persisted learner turn {state.profile['turns']} to SQLite"
        )

    def _node_respond(self, state: AgentState) -> NodeOutcome:
        if state.intent == "course_navigation":
            if state.module:
                curriculum_module = next(
                    item for item in self.curriculum["modules"]
                    if item["module_id"] == state.module_id
                )
                points = "\n".join(
                    f"- {point['title']}"
                    for point in curriculum_module["knowledge_points"]
                )
                state.answer = (
                    f"### Module {state.module.number:02d} · {state.module.label}\n\n"
                    f"{curriculum_module.get('summary', 'This module develops core stochastic-process ideas.')}\n\n"
                    "### Knowledge points\n"
                    f"{points}\n\n"
                    f"### Recommended starting point\nStart with {curriculum_module['knowledge_points'][0]['title']}."
                )
                label = state.module.label
                module_id = state.module_id
            else:
                labels = ", ".join(module.label for module in MODULES)
                state.answer = (
                    "## Stochastic Processes\n\n"
                    "This course moves from Monte Carlo estimation through Bernoulli and "
                    "Poisson processes, random walks, Brownian motion, Markov chains, "
                    f"and applied stochastic models: {labels}."
                )
                label = "Course overview"
                module_id = None
            state.response = self._non_simulation_response(
                state,
                module_id=module_id,
                module_label=label,
                topic="course_navigation",
                learning_note="Course navigation does not create a practice record.",
            )
            return NodeOutcome("answered from the curriculum catalogue")
        if state.intent == "unsupported":
            state.answer = self.tutor_agent.scope_response(
                is_general=self._is_general_conversation(state.question),
                general=lambda: self._localized_general_answer(state.question, state.response_language),
                out_of_scope=lambda: self._localized_scope_answer(state.question, state.response_language),
            )
            state.response = self._non_simulation_response(
                state,
                module_id="general",
                module_label="General conversation",
                topic="general_conversation",
                learning_note="This was a scope conversation; no simulation was run or recorded.",
            )
            if self._unsupported_experiment_parameter(state.question):
                state.response["answer"] = message("INVALID_PARAMETER", state.response_language)
                state.answer = state.response["answer"]
            return NodeOutcome("scope response without simulation")
        if state.intent == "concept":
            state.experiment_recommendations = [
                self._experiment_summary(item)
                for item in self._find_experiments(state, limit=2)
            ]
            if state.latest_result_summary and self._is_active_experiment_question(state):
                state.answer = self._localized_result_follow_up(state)
                state.llm_applied = False
            else:
                state.answer = self.tutor_agent.answer_concept(
                TutorContext(
                    question=state.question,
                    concept_id=state.concept_id,
                    curriculum_decision=state.curriculum_decision,
                    assessment=state.assessment_result,
                    sources=tuple(state.sources),
                    answerability_status=state.answerability_status,
                    sub_intent=state.concept_sub_intent,
                    teaching_mode=state.teaching_mode,
                    mastery_status=str(state.current_concept_mastery.get("status") or "NOT_STARTED"),
                    misconception_focus=(state.current_concept_mastery.get("recent_misconceptions") or [{}])[0].get("summary") if state.current_concept_mastery.get("recent_misconceptions") else None,
                ),
                synthesise=lambda: self._synthesise_concept(state),
                partial=lambda: self._partial_answer(state),
                conflict=lambda: self._conflict_answer(state),
                none=lambda: self._none_answer(state),
                fallback=lambda: message("CONCEPT_FALLBACK", state.response_language),
                )
            state.response = self._non_simulation_response(
                state,
                module_id=state.module_id,
                module_label=state.module.label if state.module else "Global course material",
                topic=state.topic or "global_concept",
                learning_note="This explanation used course evidence and did not run a simulation.",
            )
            state.response["experiment_recommendations"] = state.experiment_recommendations if not self._is_active_experiment_question(state) else []
            state.response["teaching_mode"] = state.teaching_mode
            state.response["current_concept_mastery"] = state.current_concept_mastery
            state.response["prerequisite_mastery"] = state.prerequisite_mastery
            if state.concept_sub_intent == "why/explanation" and state.experiment_recommendations and not self._is_active_experiment_question(state) and state.response_language == "en":
                state.answer += (
                    "\n\nExplore with: **"
                    f"{state.experiment_recommendations[0]['title']}**."
                )
                state.response["answer"] = state.answer
            # A recommendation is the lightweight handoff context for a later
            # “Show me.” It does not execute anything or store arrays.
            if state.experiment_recommendations and not self._is_active_experiment_question(state):
                recommended = self.experiments.get(
                    state.experiment_recommendations[0]["experiment_id"]
                )
                if recommended:
                    state.active_experiment_id = recommended["experiment_id"]
                    state.active_visualization_id = recommended.get("visualization_id")
                    self.memory.save_context(
                        session_id=state.session_id,
                        active_experiment_id=state.active_experiment_id,
                        active_visualization_id=state.active_visualization_id,
                        active_parameters={},
                        latest_result_reference=None,
                        related_concept_id=state.concept_id,
                    )
            return NodeOutcome("grounded concept response without simulation")
        if state.intent in {"quiz", "practice"}:
            state.answer = self.tutor_agent.assessment_feedback(
                state.assessment_input,
                state.curriculum_decision,
                language=state.response_language,
            )
            state.response = self._non_simulation_response(
                state,
                module_id=state.module_id,
                module_label=state.module.label if state.module else "Assessment",
                topic="assessment",
                learning_note="The Assessment Agent evaluated the attempt; the Tutor Agent provided feedback.",
            )
            state.response["result"] = state.assessment_input
            state.response["assessment"] = state.assessment_result
            state.response["curriculum_decision"] = state.curriculum_decision
            state.response["teaching_mode"] = state.teaching_mode
            state.response["grading_method"] = state.assessment_result.get("grading_method", "deterministic_keyword_or_relation_check")
            state.response["current_concept_mastery"] = state.current_concept_mastery
            state.response["prerequisite_mastery"] = state.prerequisite_mastery
            state.response["memory"] = state.profile
            state.response["recommendation"] = state.recommendation
            return NodeOutcome("Tutor feedback after assessment handoff")
        if state.tool_key is None or state.topic is None:
            raise RuntimeError("response state is incomplete")
        deterministic_answer = self.tutor_agent.simulation_feedback(
            verified=state.verified,
            result_summary=self._localized_simulation_summary(state.tool_key, state.result, state.response_language)
            if state.verified
            else "",
            module_label=state.module.label,
            guiding_question=self._guiding_question(state.tool_key, state.response_language),
            error=state.result.get("error"),
            corrections=[item["correction"] for item in state.misconceptions],
            response_language=state.response_language,
        )

        # Simulation output is authoritative numerical evidence from the Python
        # tool. Do not send it through an LLM rewrite that could add or alter numbers.
        state.llm_applied = False
        state.answer = deterministic_answer
        state.response = {
            "session_id": state.session_id,
            "answer": state.answer,
            "module_id": state.module_id,
            "module_number": state.module.number,
            "module_label": state.module.label,
            "topic": state.topic,
            "topic_label": state.module.label,
            "intent": state.intent,
            "concept_sub_intent": state.concept_sub_intent,
            "concept_id": state.concept_id,
            "selected_experiment_id": state.experiment_id,
            "selected_visualization_id": state.visualization_id,
            "active_experiment_id": state.active_experiment_id,
            "related_module_ids": state.comparison_module_ids,
            "related_concept_ids": state.comparison_concept_ids,
            "answerability_status": state.answerability_status,
            "missing_requirements": state.missing_requirements,
            "supporting_source_locators": state.supporting_source_locators,
            "conflicting_source_locators": state.conflicting_source_locators,
            "retrieval_rounds": state.retrieval_rounds,
            "question_requirements": state.question_requirements,
            "curriculum_decision": state.curriculum_decision,
            "assessment": state.assessment_result,
            "tool_called": True,
            "tool": self.tools[state.tool_key].__name__,
            "parameters": state.parameters,
            "result": state.result,
            "verified": state.verified,
            "sources": state.sources,
            "trace": state.trace,
            "workflow": {"nodes": [item["node"] for item in state.trace]},
            "memory": state.profile,
            "misconceptions": state.misconceptions,
            "learning_note": state.learning_note,
            "recommendation": state.recommendation,
            "context": {
                "module_inherited": state.module_from_context,
                "parameters_inherited": sorted(state.inherited_parameters),
            },
            "llm_enabled": self.llm.enabled,
            "llm_applied": state.llm_applied,
            "llm": dict(state.llm_metadata),
        }
        state.response["run_sha256"] = execution_sha256(
            module_id=state.module_id,
            tool=self.tools[state.tool_key].__name__,
            parameters=state.parameters,
            result=state.result,
            corpus_sha256=self.knowledge.corpus_sha256,
        )
        state.response["experiment"] = (
            self._experiment_summary(self.experiments.get(state.experiment_id))
            if state.experiment_id and self.experiments.get(state.experiment_id)
            else None
        )
        return NodeOutcome("verified tool answer; numerical output kept immutable")

    def _partial_answer(self, state: AgentState) -> str:
        """Answer only supported material and expose the missing requirement."""

        concepts = state.question_requirements.get("concept_titles", [])
        supported = ", ".join(concepts[:2]) if concepts else "the related stochastic-process concept"
        missing_user = state.question_requirements.get("missing_user_requirements", [])
        if missing_user:
            if len(missing_user) == 2:
                missing_text = f"{missing_user[0]} and {missing_user[1]}"
            elif len(missing_user) > 2:
                missing_text = ", ".join(missing_user[:-1]) + f", and {missing_user[-1]}"
            else:
                missing_text = missing_user[0]
            if len(missing_user) > 1:
                return message("EVIDENCE_PARTIAL", state.response_language, supported=supported, missing=missing_text)
            question = missing_text
            return message("EVIDENCE_PARTIAL_SINGLE", state.response_language, supported=supported, missing=question)
        missing = ", ".join(state.missing_requirements[:4]) or "a condition needed for the requested claim"
        return message("EVIDENCE_PARTIAL", state.response_language, supported=supported, missing=missing)

    @staticmethod
    def _none_answer(state: AgentState) -> str:
        if state.question_requirements.get("missing_user_requirements"):
            missing = state.question_requirements["missing_user_requirements"][0]
            return message("NEED_MORE_INFORMATION", state.response_language, missing=missing)
        return message("EVIDENCE_NONE", state.response_language)

    def _conflict_answer(self, state: AgentState) -> str:
        """Surface explicit source disagreement instead of selecting silently."""

        excerpts: list[str] = []
        for source in state.sources:
            locator = str(source.get("source") or "")
            if locator not in state.conflicting_source_locators:
                continue
            text = self._clean_evidence(str(source.get("content") or source.get("claim") or ""))
            sentence = re.split(r"(?<=[.!?])\s+", text)[0][:180]
            if sentence:
                excerpts.append(f"- {sentence} [Source: {locator}]")
        detail = "\n".join(excerpts[:4])
        answer = (
            "The supplied course sources make materially different claims, so I cannot give one definitive answer without more context.\n\n"
            f"The supported positions are:\n{detail}\n\n"
            "Which model, convention, or source should govern this question?"
        )
        return message("CONFLICT", state.response_language) + "\n\n" + detail + "\n\nWhich model, convention, or source should govern this question?"

    @staticmethod
    def _relevant_excerpt(question: str, content: str) -> str:
        """Show the most relevant textbook sentences instead of a whole PDF page."""

        terms = set(re.findall(r"[a-z][a-z0-9-]{2,}", question.lower()))
        sentences = re.split(r"(?<=[.!?])\s+", content)
        selected = [
            sentence.strip()
            for sentence in sentences
            if terms & set(re.findall(r"[a-z][a-z0-9-]{2,}", sentence.lower()))
        ]
        excerpt = " ".join(selected[:5]) or content
        return excerpt[:1200].strip()

    def _synthesise_concept(self, state: AgentState) -> str:
        """Use the configured LLM for grounded teaching, with a safe short fallback."""

        module_context = []
        module_ids = state.comparison_module_ids or ([state.module_id] if state.module_id else [])
        for module_id in module_ids:
            module = next(item for item in self.curriculum["modules"] if item["module_id"] == module_id)
            module_context.append({
                "module": f"Module {module['number']:02d} · {module['label']}",
                "goal": module.get("summary", ""),
                "knowledge_points": [point["title"] for point in module["knowledge_points"]],
            })
        evidence = [
            {
                "source": source["source"],
                "title": source.get("title", ""),
                "content": self._clean_evidence(str(source.get("content", "")))[: self.config.evidence_max_chars],
                "module_id": source.get("module_id"),
                "concept_id": source.get("concept_id"),
            }
            for source in state.sources[:6]
        ]
        detailed = self._asks_for_detail(state.question)
        sub_intent = state.concept_sub_intent
        system_prompt = f"""You are a university tutor for Stochastic Processes.
The original student question is the primary instruction. Answer it directly and
do not replace it with a module overview.

STUDENT QUESTION: {state.question}
CONCEPT SUB-INTENT: {sub_intent}
TEACHING MODE: {state.teaching_mode}
CURRENT CONCEPT STATUS: {state.current_concept_mastery.get('status', 'NOT_STARTED')}
MISCONCEPTION FOCUS: {state.current_concept_mastery.get('recent_misconceptions', [])}
QUESTION REQUIREMENTS: {json.dumps(state.question_requirements, ensure_ascii=False)}
ANSWERABILITY STATUS: {state.answerability_status}
COURSE CONTEXT: The module descriptions below are navigation metadata only.
SUPPORTED EVIDENCE: Use only the supplied curated course and textbook evidence as the factual source.
LATEST VERIFIED SIMULATION SUMMARY (use only when the student asks about a prior result): {state.latest_result_summary or "none"}

The first sentence must directly answer the exact student question. Then give only
the explanation needed for this sub-intent:
- definition: define the term, state its important properties, then give intuition;
- why/explanation: give the answer first, then 2–4 reasoning steps and a formula if needed;
- derivation: show a compact step-by-step derivation;
- comparison: state the distinction first, then compare both sides in concise bullets or a table;
- hint: give progressive hints only, without the full solution;
- example: explain the idea and give one concrete example;
- how_to: give a short ordered procedure.

Use headings only when they improve clarity. Do not use a universal template, and do
not output empty sections. Never copy a retrieved passage or mention retrieval,
chunks, embeddings, scores, tools, prompts, or internal metadata. Do not expose
garbled PDF extraction. Every substantive claim must be supported by the supplied
evidence; do not infer a conclusion merely because related concepts were retrieved.
Use standard LaTeX with $...$ or $$...$$ when appropriate.
Keep the default answer under 180 words{' (up to 260 words when the learner asks for detail)' if detailed else ''}.
{self._language_instruction(state.response_language)}
Use natural terminology in the requested language while retaining canonical English terms in parentheses when helpful."""
        candidate = self.llm.complete(
            system_prompt,
            json.dumps(
                {
                    "student_question": state.question,
                    "concept_sub_intent": sub_intent,
                    "comparison": bool(state.comparison_module_ids),
                    "curriculum_context": module_context,
                    "evidence": evidence,
                },
                ensure_ascii=False,
            ),
        )
        if candidate:
            state.llm_metadata = self._llm_metadata()
            cleaned = self._clean_llm_answer(
                candidate,
                detailed=detailed,
                question=state.question,
                sub_intent=sub_intent,
                response_language=state.response_language,
                max_words=self.config.answer_max_words,
            )
            if cleaned:
                state.llm_applied = True
                return cleaned
        state.llm_applied = False
        state.llm_metadata = self._llm_metadata()
        localized = self._localized_fallback(state)
        if localized:
            return localized
        return self._short_concept_fallback(state)

    @staticmethod
    def _clean_evidence(text: str) -> str:
        """Make extracted evidence safe for the prompt without presenting it to students."""

        cleaned = re.sub(r"\s+", " ", text)
        cleaned = re.sub(r"\b(?:page|第)\s*\d+\b", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"(?:PN|P N|pij)\s*[_^]?\s*i\s*=", "", cleaned, flags=re.I)
        return cleaned.strip()

    @staticmethod
    def _asks_for_detail(question: str) -> bool:
        lowered = question.lower()
        return any(marker in lowered for marker in ("in detail", "more detail", "detailed", "深入", "详细"))

    @staticmethod
    def _clean_llm_answer(
        candidate: str,
        *,
        detailed: bool,
        question: str = "",
        sub_intent: str | None = None,
        response_language: str = "en",
        max_words: int = 180,
    ) -> str | None:
        """Accept compact English without allowing a generic module overview."""

        text = candidate.strip()
        if not text:
            return None
        # Remove harmless TeX spacing commands so formulas remain readable in
        # both KaTeX and plain-text/API assertions (for example N(0,t)).
        text = re.sub(r"\\(?:,|;|:|!|\s+)", "", text)
        text = re.sub(r"\b([A-Za-z])\(0,\s+([A-Za-z0-9])\)", r"\1(0,\2)", text)
        if response_language == "en" and re.search(r"[\u4e00-\u9fff]", text):
            return None
        if re.search(r"according to retrieved|retriev(?:ed|al)|embedding|chunk|score|workflow|tool_called", text, re.I):
            return None
        if re.search(r"(?:PN|P N|pij)\s*[_^]?\s*i\s*=", text, re.I):
            return None
        if re.search(r"(?:this module|the module)\s+(?:studies|explores|covers)", text, re.I):
            return None
        if sub_intent == "hint" and re.search(
            r"(?:\\pi|π)\s*(?:=|=)\s*(?:\\pi|π)\s*P|detailed\s+balance|solve\s+this\s+linear\s+system",
            text,
            re.I,
        ):
            # A hosted model can turn a request for a hint into a complete
            # stationary-distribution derivation. Use the progressive offline
            # hint instead of exposing the solution.
            return None
        word_count = len(re.findall(r"\b[\w]+(?:[-'][\w]+)?\b", text))
        if word_count > (min(max_words + 80, 320) if detailed else max_words):
            return None
        return text

    def _short_concept_fallback(self, state: AgentState) -> str:
        """Give a question-aware answer when the hosted model is unavailable."""

        lowered = (state.retrieval_query_en or state.question).lower()
        sub_intent = state.concept_sub_intent
        evidence_text = " ".join(
            self._clean_evidence(str(source.get("content", "")))
            for source in state.sources[:6]
        ).lower()

        if state.latest_result_summary and any(
            marker in lowered
            for marker in ("what changed", "what should i notice", "explain this graph", "explain the result", "interpret this")
        ):
            answer = (
                "The latest run changed the selected experiment parameters to "
                f"{state.active_parameters}. Its verified summary is: "
                f"{state.latest_result_summary} "
                "Compare this run with the previous parameters to identify which change drives the difference."
            )
            return self._translate_fallback(answer, state.response_language)

        if "continuous" in lowered and "random walk" in lowered and "self-avoid" not in lowered:
            return self._translate_fallback(
                "A discrete-time random walk moves at integer time steps, whereas a continuous-time random walk waits a random amount of time between jumps.\n\n"
                "- Discrete time: the number of jumps is fixed by the time index.\n"
                "- Continuous time: jump times are random, often driven by a Poisson process.\n"
                "- The spatial increment rule can be similar, but the clock is different."
                , state.response_language)

        if state.comparison_module_ids or ("random walk" in lowered and "self-avoid" in lowered):
            return self._localized_fallback(state) or (
                "An ordinary random walk uses a fixed increment rule, whereas a self-avoiding walk also depends on the sites already visited.\n\n"
                "- Random walk: the current position is enough for the usual Markov description.\n"
                "- Self-avoiding walk: the visited set changes which moves are allowed.\n"
                "- Consequence: a self-avoiding path can become trapped."
            )

        if sub_intent == "hint":
            if "stationary" in lowered:
                return self._translate_fallback("Start by writing the balance condition that leaves the state probabilities unchanged after one transition. Then add the normalization condition and solve the resulting equations.", state.response_language)
            return self._translate_fallback("Begin by identifying the random quantity, its conditioning information, and the theoretical relation you want to verify. Write that relation before substituting numbers.", state.response_language)

        if "strict stationarity" in lowered or ("strict" in lowered and "weak" in lowered and "station" in lowered):
            return (
                "Strict stationarity preserves every finite-dimensional distribution under a time shift. Weak stationarity asks only for a constant mean and a covariance that depends on the lag.\n\n"
                "$E[X_t]=m$ and $\\operatorname{Cov}(X_t,X_{t+h})=\\gamma(h)$ are the key weak-stationarity conditions."
            )

        if "exponential" in lowered and "memoryless" in lowered:
            return (
                "The exponential distribution is memoryless because the chance of waiting another interval does not depend on how long you have already waited.\n\n"
                "For $T\\sim\\operatorname{Exp}(\\lambda)$, $P(T>s+t\\mid T>s)=P(T>t)$. The exponential survival function makes the factor $e^{-\\lambda s}$ cancel."
            )

        if "poisson" in lowered and sub_intent in {"why/explanation", "derivation"}:
            if "poisson" in evidence_text and "exponential" in evidence_text:
                answer = (
                    "A Poisson process has exponential waiting times because waiting longer than $t$ means that no arrival has occurred by time $t$.\n\n"
                    "1. $N(t)\\sim\\operatorname{Poisson}(\\lambda t)$.\n"
                    "2. Therefore $P(T>t)=P(N(t)=0)$.\n"
                    "3. The Poisson probability at zero is $e^{-\\lambda t}$.\n"
                    "Hence $T\\sim\\operatorname{Exp}(\\lambda)$."
                )
            return self._translate_fallback(answer if "answer" in locals() else "The waiting time is exponential because its survival probability is determined by the probability of observing zero arrivals during the waiting interval.", state.response_language)

        if "poisson" in lowered:
            answer = (
                "A Poisson process counts arrivals over time with independent, stationary increments and rate $\\lambda$. For an interval of length $t$, $N(t)\\sim\\operatorname{Poisson}(\\lambda t)$; its first waiting time is exponentially distributed with rate $\\lambda$."
            )
            return self._translate_fallback(answer, state.response_language)

        if "brownian" in lowered or state.module_id == "module04":
            answer = (
                "Brownian motion is a continuous process that starts at $B(0)=0$, has independent stationary increments, and satisfies $B(t)\\sim N(0,t)$. Its paths are continuous, so uncertainty grows continuously rather than through jumps."
            )
            return self._translate_fallback(answer, state.response_language)

        if "stationary distribution" in lowered or ("stationary" in lowered and state.module_id == "module05") or state.concept_id == "m05-stationary-distribution":
            return self._translate_fallback("A stationary distribution is a probability vector that remains unchanged after one transition. For a transition matrix $P$, it satisfies $\\pi P=\\pi$ together with non-negative entries summing to one.", state.response_language)

        if "law of large numbers" in lowered:
            return "The law of large numbers says that the average of many suitable observations approaches the expected value. This is why repeated Monte Carlo estimates become more stable as the sample size grows."

        if sub_intent == "example":
            excerpt = self._relevant_excerpt(state.question, evidence_text)
            return f"The idea becomes concrete when you inspect one sample path and then repeat the experiment. For example, compare a single path with the distribution of its endpoint. {excerpt[:260]}".strip()

        if sub_intent == "how_to":
            return "First identify the state space and transition mechanism. Next write the governing probability equations, impose normalization, and only then evaluate the resulting expression or simulation."

        if sub_intent == "derivation":
            return "Start from the model definition, write the relevant probability or balance equation, simplify one step at a time, and check that the final expression satisfies the required normalization or boundary condition."

        excerpt = self._relevant_excerpt(state.question, evidence_text)
        return f"The key idea is stated by the model evidence: {excerpt[:360]}".strip()

    @staticmethod
    def _localized_result_follow_up(state: AgentState) -> str:
        if state.response_language == "zh":
            return f"最近一次 {state.active_experiment_id or '课程实验'} 运行使用了参数 {state.active_parameters}，结果为：{StochasticTutorAgent._translate_simulation_summary(state.latest_result_summary or '', 'zh')} 请将这次运行与之前的参数比较，找出变化的原因。"
        if state.response_language == "sv":
            summary = StochasticTutorAgent._translate_simulation_summary(state.latest_result_summary or "", "sv")
            return f"Den senaste körningen {state.active_experiment_id or 'i kursen'} använde parametrarna {state.active_parameters} och gav: {summary or 'inget sammanfattat resultat ännu'} Jämför körningen med de tidigare parametrarna för att se vad som ändrades."
        return f"The latest {state.active_experiment_id or 'course'} run used {state.active_parameters} and produced: {state.latest_result_summary} Compare it with the previous parameters to identify what changed."

    @staticmethod
    def _translate_simulation_summary(summary: str, language: str) -> str:
        poisson = re.fullmatch(
            r"The empirical mean event count is (?P<emp>-?[0-9]+(?:\.[0-9]+)?) versus theoretical λT=(?P<th>-?[0-9]+(?:\.[0-9]+)?); absolute error=(?P<err>-?[0-9]+(?:\.[0-9]+)?)\.",
            summary.strip(),
        )
        if poisson and language == "sv":
            return f"Det empiriska medelantalet händelser är {poisson['emp']} jämfört med det teoretiska värdet λT={poisson['th']}; absolutfelet är {poisson['err']}."
        if poisson and language == "zh":
            return f"经验事件计数均值为 {poisson['emp']}，理论值 λT={poisson['th']}；绝对误差为 {poisson['err']}。"
        bernoulli = re.fullmatch(
            r"The empirical count mean is (?P<cm>-?[0-9]+(?:\.[0-9]+)?) versus theoretical np=(?P<ct>-?[0-9]+(?:\.[0-9]+)?); the empirical waiting mean is (?P<wm>-?[0-9]+(?:\.[0-9]+)?) versus 1/p=(?P<wt>-?[0-9]+(?:\.[0-9]+)?)\.",
            summary.strip(),
        )
        if bernoulli and language == "sv":
            return f"Det empiriska medelvärdet för antalet händelser är {bernoulli['cm']} jämfört med np={bernoulli['ct']}; den empiriska väntetiden är {bernoulli['wm']} jämfört med 1/p={bernoulli['wt']}."
        if bernoulli and language == "zh":
            return f"经验事件计数均值为 {bernoulli['cm']}，理论值为 np={bernoulli['ct']}；经验等待时间均值为 {bernoulli['wm']}，理论值为 1/p={bernoulli['wt']}。"
        if language == "sv":
            return f"Experimentet gav följande verifierade resultat: {summary}"
        if language == "zh":
            return f"实验得到以下经过验证的结果：{summary}"
        return summary

    @staticmethod
    def _localized_simulation_summary(topic: str, result: dict[str, Any], language: str) -> str:
        """Render tool-owned numbers with localized prose; never translate by word replacement."""
        if language == "en":
            return StochasticTutorAgent._summary_english(topic, result)
        def val(key: str, default: object = "?") -> object:
            return result.get(key, default)
        if topic == "poisson":
            if language == "sv":
                return f"Det empiriska medelantalet händelser är {val('empirical_mean_count')} jämfört med det teoretiska värdet λT={val('theoretical_mean_count')}; absolutfelet är {val('absolute_error')}."
            return f"经验事件计数均值为 {val('empirical_mean_count')}，理论值 λT={val('theoretical_mean_count')}；绝对误差为 {val('absolute_error')}。"
        if topic == "bernoulli":
            if language == "sv":
                return f"Det empiriska medelvärdet för antalet händelser är {val('empirical_count_mean')} jämfört med np={val('theoretical_count_mean')}; den empiriska väntetiden är {val('empirical_waiting_mean')} jämfört med 1/p={val('theoretical_waiting_mean')}."
            return f"经验事件计数均值为 {val('empirical_count_mean')}，理论值为 np={val('theoretical_count_mean')}；经验等待时间均值为 {val('empirical_waiting_mean')}，理论值为 1/p={val('theoretical_waiting_mean')}。"
        if topic == "brownian_motion":
            if language == "sv":
                return f"Det empiriska medelvärdet vid sluttiden är {val('empirical_terminal_mean')} och variansen är {val('empirical_terminal_variance')}; teorin ger medelvärde 0 och varians T={val('theoretical_terminal_variance')}."
            return f"终点的经验均值为 {val('empirical_terminal_mean')}，经验方差为 {val('empirical_terminal_variance')}；理论均值为 0，理论方差 T={val('theoretical_terminal_variance')}。"
        if topic in {"bernoulli_poisson", "poisson"}:
            return f"实验完成。经验输出已与理论参考值进行比较。"
        # Keep other tools concise and free of mixed English labels. Values still
        # come verbatim from the Python tool.
        summary = StochasticTutorAgent._summary_english(topic, result)
        if language == "sv":
            return f"Experimentet gav följande verifierade resultat: {summary}"
        return f"实验得到以下经过验证的结果：{summary}"

    def _non_simulation_response(
        self,
        state: AgentState,
        *,
        module_id: str | None,
        module_label: str,
        topic: str,
        learning_note: str,
    ) -> dict[str, Any]:
        """Use the existing response contract without inventing a tool run."""

        return {
            "session_id": state.session_id,
            "answer": state.answer,
            "module_id": module_id,
            "module_number": state.module.number if state.module else None,
            "module_label": module_label,
            "topic": topic,
            "topic_label": module_label,
            "intent": state.intent,
            "concept_sub_intent": state.concept_sub_intent,
            "concept_id": state.concept_id,
            "active_experiment_id": state.active_experiment_id,
            "selected_experiment_id": state.experiment_id,
            "related_module_ids": state.comparison_module_ids,
            "related_concept_ids": state.comparison_concept_ids,
            "answerability_status": state.answerability_status,
            "missing_requirements": state.missing_requirements,
            "supporting_source_locators": state.supporting_source_locators,
            "conflicting_source_locators": state.conflicting_source_locators,
            "retrieval_rounds": state.retrieval_rounds,
            "question_requirements": state.question_requirements,
            "retrieval_query": state.retrieval_query,
            "retrieval_query_en": state.retrieval_query_en,
            "detected_query_language": state.detected_query_language,
            "response_language": state.response_language,
            "translation_applied": state.translation_applied,
            "tool_called": False,
            "tool": "no_simulation",
            "parameters": {},
            "result": {"series": []},
            "verified": False,
            "sources": state.sources,
            "trace": state.trace,
            "workflow": {"nodes": [item["node"] for item in state.trace]},
            "memory": self.memory.profile(state.session_id),
            "misconceptions": [],
            "learning_note": learning_note,
            "recommendation": state.recommendation,
            "curriculum_decision": state.curriculum_decision,
            "teaching_mode": state.teaching_mode,
            "current_concept_mastery": state.current_concept_mastery,
            "prerequisite_mastery": state.prerequisite_mastery,
            "context": {"module_inherited": state.module_from_context, "parameters_inherited": []},
            "llm_enabled": self.llm.enabled,
            "llm_applied": state.llm_applied,
            "llm": dict(state.llm_metadata),
            "run_sha256": None,
            "experiment_recommendations": [],
            "experiment": None,
        }

    def _general_response(
        self,
        question: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Answer product conversation without pretending it is a simulation.

        Course tools are intentionally not selected for greetings, identity
        questions, or product questions.  This avoids the old unsafe default of
        treating every unknown utterance as a Monte Carlo request.
        """

        candidate = self.llm.complete(
            (
                "You are StochLab, a friendly English tutor for "
                "stochastic processes. Answer the user's product or casual "
                "question directly in concise English. Do not claim that a "
                "simulation was run and do not invent course citations."
            ),
            json.dumps({"question": question}, ensure_ascii=False),
        )
        # Keep the student channel English even if a provider ignores the
        # language instruction. The local fallback is deliberately concise.
        if candidate and re.search(r"[\u4e00-\u9fff]", candidate):
            candidate = None
        answer = candidate or self._offline_general_answer(question)
        detail = "LLM general conversation" if candidate else "offline general conversation"
        trace = [
            {
                "node": "respond",
                "detail": detail,
                "status": "ok",
                "duration_ms": 0.0,
            }
        ]
        return {
            "session_id": session_id,
            "answer": answer,
            "module_id": "general",
            "module_number": None,
            "module_label": "General conversation",
            "topic": "general_conversation",
            "topic_label": "General conversation",
            "tool": "no_simulation",
            "parameters": {},
            "result": {"series": []},
            "verified": False,
            "sources": [],
            "answerability_status": "OUT_OF_SCOPE",
            "missing_requirements": [],
            "supporting_source_locators": [],
            "conflicting_source_locators": [],
            "retrieval_rounds": 0,
            "question_requirements": self._analyze_question_requirements(question),
            "trace": trace,
            "workflow": {"nodes": ["respond"]},
            "memory": self.memory.profile(session_id),
            "misconceptions": [],
            "learning_note": "This was a general conversation; no simulation was run and no practice record was written.",
            "recommendation": None,
            "context": {"module_inherited": False, "parameters_inherited": []},
            "llm_enabled": self.llm.enabled,
            "llm_applied": bool(candidate),
            "teaching_team": build_team_trace(trace),
            "run_sha256": None,
        }

    @classmethod
    def _offline_scope_answer(cls, question: str) -> str:
        """Decline out-of-scope claims without implying unsupported knowledge."""

        return (
            "That question is outside the scope of this stochastic-process course. "
            "The course evidence does not cover it, so I will not guess. "
            "I can help with stochastic-process concepts, course modules, or verified simulations."
        )

    @classmethod
    def _localized_scope_answer(cls, question: str, language: str) -> str:
        return message("OUT_OF_SCOPE", language)

    @classmethod
    def _localized_general_answer(cls, question: str, language: str) -> str:
        if language == "zh":
            lowered = question.lower()
            if ("课程" in question or "这门课" in question) and "学" in question:
                return "This course develops stochastic-process intuition through definitions, practice questions, and verified simulations."
            if "第一个" in question or "第1" in question:
                return "Module 00 介绍蒙特卡洛估计；第一个主要教学模块是 Module 01——伯努利与泊松过程。"
            if "技术栈" in question or "架构" in question or "agent" in lowered:
                return "Tutor 使用本地 Python 服务、课程材料检索、受限的模拟工具和浏览器工作区。"
            return message("GENERAL", language)
        if language == "sv":
            lowered = question.casefold()
            if "kurs" in lowered and ("lär" in lowered or "innehåll" in lowered):
                return "Kursen bygger intuition för stokastiska processer genom definitioner, övningar och verifierade simuleringar. Den omfattar Monte Carlo, Bernoulli- och Poissonprocesser, random walks, Brownsk rörelse, Markovkedjor samt tillämpade modeller."
            return message("GENERAL", language)
        return message("GENERAL", language)

    @classmethod
    def _offline_general_answer(cls, question: str) -> str:
        """Give useful product answers when a hosted model is unavailable."""

        lowered = question.lower()
        if any(marker in lowered for marker in ("this course", "course", "学什么", "课程")):
            return (
                "This course develops stochastic-process intuition through definitions, "
                "practice questions, and verified simulations. It covers Monte Carlo "
                "estimation, Bernoulli and Poisson processes, random walks, Brownian "
                "motion, Markov chains, and applied reliability, buffer, and queue models."
            )
        if any(
            marker in lowered
            for marker in (
                "first module",
                "第一个module",
                "第一个 module",
            )
        ):
            return (
                "Module 00 introduces Monte Carlo estimation. The first main teaching "
                "module is Module 01 — Bernoulli and Poisson processes."
            )
        if any(marker in lowered for marker in ("technical stack", "architecture", "rag", "agent")):
            return (
                "The tutor uses a local Python service, course-material retrieval, "
                "bounded simulation tools, and a browser workspace."
            )
        if any(marker in lowered for marker in ("what is your name", "who are you", "你是谁", "你叫什么")):
            return cls.GENERAL_FALLBACK
        return (
            "I can explain a course concept, describe a module, or run a verified "
            "simulation when you provide explicit simulation instructions."
        )

    @classmethod
    def _is_general_conversation(cls, question: str) -> bool:
        """Allow a narrow chat lane without swallowing unknown tool requests."""

        lowered = question.lower().strip()
        for marker in cls.GENERAL_CHAT_MARKERS:
            # Short English markers such as ``hi`` must match a word, not a
            # substring (otherwise ``finding`` is misclassified as a greeting).
            if marker.isascii() and marker.isalpha() and len(marker) <= 3:
                if re.search(rf"\b{re.escape(marker)}\b", lowered):
                    return True
            elif marker in lowered:
                return True
        return False

    @staticmethod
    def _is_course_navigation(question: str) -> bool:
        lowered = question.lower().strip()
        return bool(
            re.search(r"\bmodule\s*0*(?:10|[0-9])\b", lowered)
            or re.search(r"模块\s*0*(?:10|[0-9])", lowered)
            or any(
                phrase in lowered
                for phrase in (
                    "what is this course",
                    "what do we learn in this course",
                    "course overview",
                    "这门课学什么",
                    "课程概览",
                )
            )
        )

    @staticmethod
    def _navigation_module_id(question: str) -> str | None:
        match = re.search(r"(?:module|模块)\s*0*(10|[0-9])(?:\b|$)", question.lower())
        return f"module{int(match.group(1)):02d}" if match else None

    @staticmethod
    def _is_comparison(question: str) -> bool:
        lowered = question.lower()
        # ``compare with theory`` is an evaluation instruction, not a
        # two-concept comparison.  Only treat comparison language as routing
        # evidence when it relates two objects or an explicit contrast.
        return bool(
            any(marker in lowered for marker in ("difference between", "different from", " vs ", "versus", "distinguish", "what changes between", "区别", "比较"))
            or re.search(r"\bcompare\b.+\b(with|and)\b.+\b(random walk|process|distribution|chain|motion|model|walk)\b", lowered)
        )

    @staticmethod
    def _detect_concept_sub_intent(question: str) -> str:
        """Classify the teaching task with deterministic, low-risk cues."""

        lowered = question.lower().strip()
        if StochasticTutorAgent._is_comparison(lowered):
            return "comparison"
        if any(marker in lowered for marker in ("give me a hint", "hint", "clue", "提示")):
            return "hint"
        if any(
            marker in lowered
            for marker in ("derive", "derivation", "prove", "show that", "step by step", "推导", "证明")
        ):
            return "derivation"
        if any(
            marker in lowered
            for marker in ("why", "explain why", "how come", "reason", "varför", "förklara varför", "orsak", "原因", "为什么", "解释")
        ):
            return "why/explanation"
        if any(
            marker in lowered
            for marker in ("give an example", "for example", "example of", "illustrate", "举例", "例子")
        ):
            return "example"
        if any(
            marker in lowered
            for marker in ("how do i", "how to", "how can i", "find a", "calculate", "compute", "怎么求", "如何找")
        ):
            return "how_to"
        return "definition"

    @staticmethod
    def _is_supported_global_concept(question: str) -> bool:
        """Keep recognized theory questions on the global RAG lane."""

        lowered = question.lower()
        return any(
            marker in lowered
            for marker in (
                "law of large numbers",
                "strict stationarity",
                "weak stationarity",
                "stationarity",
                "stationary distribution",
                "exponential distribution",
                "memoryless",
                "ergodic",
                "martingale",
                "stochastic process",
                "monte carlo",
                "random points",
                "running average",
                "sample grows",
                "brownian increment",
                "crosses a level",
                "integrating an intensity",
                "expected count",
                "how long merging takes",
                "merging time",
            )
        )

    @staticmethod
    def _detect_module_ids(question: str) -> list[str]:
        lowered = question.lower().replace("‑", "-").replace("–", "-")
        scores: list[tuple[int, int, str]] = []
        for module in MODULES:
            matched = [keyword for keyword in module.keywords if keyword in lowered]
            if matched:
                scores.append((max(len(item) for item in matched), len(matched), module.module_id))
        scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scores]

    @staticmethod
    def _strong_module_override(question: str) -> str | None:
        """Resolve distinctive experiment wording before broad aliases.

        A query such as "nonhomogeneous Poisson thinning" contains the broad
        Poisson alias from Module 01, but its experiment qualifier is the
        stronger routing signal.  These are stable model terms, not case
        strings, and are used only for deterministic first-pass routing.
        """

        lowered = question.casefold().replace("‑", "-").replace("–", "-")
        groups = (
            ("module08", ("nonhomogeneous", "non-homogeneous", "非齐次", "thinning", "time-varying intensity", "tidsvarierande intensitet")),
            ("module09", ("self-avoiding", "self avoiding", "självundvikande", "自避免")),
            ("module10", ("coalescing", "coalescence", "particles merge", "particle merging", "粒子合并", "圆上粒子")),
            ("module03", ("continuous-time random walk", "continuous time random walk", "连续时间随机游走")),
            ("module07", ("m/m/1", "mm1", "buffer", "queue stability", "批量到达", "可靠性模型", "reliability model", "series and parallel")),
            ("module06", ("birth-death", "birth death", "出生死亡", "generator matrix", "holding time", "故障率", "修复率")),
            ("module04", ("brownian motion", "brownian", "布朗运动")),
        )
        for module_id, markers in groups:
            if any(marker in lowered for marker in markers):
                return module_id
        return None

    def _match_concept(self, question: str, module_id: str | None) -> str | None:
        """Resolve a concept only when title/alias evidence is sufficiently specific."""

        lowered = " ".join(
            question.lower().replace("‑", "-").replace("–", "-").replace("-", " ").split()
        )
        if module_id == "module01" and "waiting" in lowered and "exponential" in lowered and "geometric" not in lowered:
            return "m01-poisson-process"
        if module_id == "module01" and any(marker in lowered for marker in ("waiting", "interarrival", "exponential")) and not any(marker in lowered for marker in ("geometric", "bernoulli")):
            return "m01-poisson-process"
        if module_id == "module05" and ("pi p" in lowered or "stationary distribution" in lowered):
            return "m05-stationary-distribution"
        # Strict/weak stationarity is a process-level distinction, not the
        # discrete Markov-chain stationary-distribution concept in Module 05.
        if "strict stationarity" in lowered or "weak stationarity" in lowered:
            return None
        candidates = [
            point
            for point in self._concepts
            if module_id is None or point["module_id"] == module_id
        ]
        stopwords = {
            "and", "the", "for", "from", "with", "what", "why", "how",
            "does", "this", "that", "process", "model", "time", "state",
            "distribution", "function", "system", "chain", "random",
        }
        query_tokens = {
            token
            for token in re.findall(r"[a-z][a-z0-9-]{2,}", lowered)
            if token not in stopwords
        }
        scored: list[tuple[int, int, str]] = []
        for point in candidates:
            concept_id = str(point["id"])
            title = " ".join(str(point["title"]).lower().replace("-", " ").split())
            aliases = set(self.CONCEPT_ALIASES.get(concept_id, ()))
            aliases.update(self.LANGUAGE_ALIASES.get(concept_id, ()))
            aliases.add(title)
            aliases.add(str(point["summary"]).lower())
            best = 0
            for alias in aliases:
                normalized_alias = " ".join(alias.replace("-", " ").split())
                if len(normalized_alias) >= 5 and normalized_alias in lowered:
                    best = max(best, 100 + len(normalized_alias.split()))
            title_tokens = {
                token for token in re.findall(r"[a-z][a-z0-9-]{2,}", title)
                if token not in stopwords
            }
            overlap = len(query_tokens & title_tokens)
            if overlap >= 2:
                best = max(best, 20 + overlap * 8)
            if best:
                scored.append((best, overlap, concept_id))
        if not scored:
            return self._retrieval_concept_fallback(question, module_id)
        scored.sort(reverse=True)
        best_score, _, best_id = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        if best_score < 20 or (best_score < 100 and best_score - second_score < 8):
            return self._retrieval_concept_fallback(question, module_id)
        return best_id

    @staticmethod
    def _normalize_routing_text(value: str) -> str:
        value = value.casefold().replace("π", "pi").replace("λ", "lambda")
        value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
        return " ".join(value.replace("-", " ").split())

    def _exact_curriculum_concept(self, question: str) -> dict[str, Any] | None:
        """Return one unambiguous curriculum concept for explicit wording."""

        normalized = self._normalize_routing_text(question)
        matches: list[tuple[int, str, dict[str, Any]]] = []
        for point in self._concepts:
            phrases = {
                str(point.get("title") or ""),
                *self.CONCEPT_ALIASES.get(str(point["id"]), ()),
                *self.LANGUAGE_ALIASES.get(str(point["id"]), ()),
            }
            for phrase in phrases:
                candidate = self._normalize_routing_text(phrase)
                if len(candidate) >= 5 and candidate in normalized:
                    matches.append((len(candidate), str(point["id"]), point))
        if not matches:
            # Notation is often separated by spaces or Unicode punctuation in
            # student input (for example ``πP = π``). Keep this deterministic
            # and limited to a curriculum concept's declared aliases/cues.
            normalized_compact = normalized.replace(" ", "")
            for point in self._concepts:
                for phrase in (
                    *self.CONCEPT_ALIASES.get(str(point["id"]), ()),
                    *self.LANGUAGE_ALIASES.get(str(point["id"]), ()),
                    *self.CANDIDATE_CUES.get(str(point["id"]), ()),
                ):
                    candidate = self._normalize_routing_text(str(phrase)).replace(" ", "")
                    if len(candidate) >= 5 and candidate in normalized_compact:
                        matches.append((len(candidate), str(point["id"]), point))
        if not matches:
            return None
        matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
        if len(matches) > 1 and matches[0][0] == matches[1][0] and matches[0][1] != matches[1][1]:
            return None
        return matches[0][2]

    def _candidate_concept_routes(
        self,
        question: str,
        *,
        module_hint: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Bounded candidate routing using curriculum text plus evidence support."""

        normalized = self._normalize_routing_text(question)
        query_tokens = {
            token for token in normalized.split()
            if len(token) >= 3
            and token not in {
                "what", "why", "how", "does", "this", "that", "with", "from",
                "give", "can", "you", "the", "and", "for", "is", "are", "mean",
                "explain", "using", "course", "material", "main", "quantity", "compare",
            }
        }
        scored: list[dict[str, Any]] = []
        for point in self._concepts:
            if module_hint and str(point["module_id"]) != module_hint:
                continue
            text = " ".join(
                [
                    str(point.get("title") or ""),
                    str(point.get("summary") or ""),
                    *self.CONCEPT_ALIASES.get(str(point["id"]), ()),
                    *self.LANGUAGE_ALIASES.get(str(point["id"]), ()),
                ]
            )
            tokens = set(self._normalize_routing_text(text).split())
            overlap = len(query_tokens & tokens)
            exact_phrase = any(
                len(self._normalize_routing_text(str(phrase))) >= 7
                and self._normalize_routing_text(str(phrase)) in normalized
                for phrase in (point.get("title"), *self.CONCEPT_ALIASES.get(str(point["id"]), ()), *self.LANGUAGE_ALIASES.get(str(point["id"]), ()))
            )
            cue_match = any(
                self._normalize_routing_text(cue) in normalized
                for cue in self.CANDIDATE_CUES.get(str(point["id"]), ())
            )
            score = float(overlap * 4 + (30 if exact_phrase else 0) + (24 if cue_match else 0))
            if score:
                scored.append({
                    "module_id": str(point["module_id"]),
                    "concept_id": str(point["id"]),
                    "routing_score": score,
                    "evidence_score": 0.0,
                })
        # Only a small global evidence request is used to disambiguate the
        # lexical shortlist; this does not turn every query into an all-module
        # search and does not alter production top-k.
        evidence = self.knowledge.retrieve(question, module_id=module_hint, limit=6)
        evidence_by_concept: dict[str, float] = {}
        for index, source in enumerate(evidence, start=1):
            concept_id = source.get("concept_id")
            if concept_id:
                evidence_by_concept[str(concept_id)] = evidence_by_concept.get(str(concept_id), 0.0) + 1.0 / index
            source_module = str(source.get("module_id") or "")
            for candidate in scored:
                if source_module and source_module == candidate["module_id"]:
                    evidence_by_concept.setdefault(candidate["concept_id"], 0.0)
                    evidence_by_concept[candidate["concept_id"]] += 0.15 / index
        for candidate in scored:
            candidate["evidence_score"] = round(evidence_by_concept.get(candidate["concept_id"], 0.0), 3)
            candidate["routing_score"] = round(candidate["routing_score"] + candidate["evidence_score"] * 8.0, 3)
        scored.sort(key=lambda item: (item["routing_score"], item["evidence_score"]), reverse=True)
        return scored[: max(1, min(limit, 3))]

    def _retrieval_concept_fallback(
        self, question: str, module_id: str | None
    ) -> str | None:
        """Use repeated concept-tagged evidence only when lexical confidence is low."""

        if module_id is None:
            return None
        evidence = self.knowledge.retrieve(
            question,
            module_id=module_id,
            limit=5,
        )
        counts: dict[str, int] = {}
        for source in evidence:
            concept_id = source.get("concept_id")
            if concept_id:
                counts[str(concept_id)] = counts.get(str(concept_id), 0) + 1
        candidates = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if not candidates or candidates[0][1] < 2:
            return None
        if len(candidates) > 1 and candidates[0][1] == candidates[1][1]:
            return None
        return candidates[0][0]

    @classmethod
    def _is_simulation_request(cls, question: str, explicit_follow_up: bool = False) -> bool:
        lowered = question.lower().strip()
        if any(marker in lowered for marker in cls.SIMULATION_MARKERS):
            return True
        # Legacy course prompts often provide model parameters without the
        # English word "simulate" (for example, a Bernoulli process followed
        # by a slot count and probability). Treat those as experiments while
        # keeping definition-only questions on the concept path.
        if classify_module(question) is not None and any(
            cls._parameter_mentioned(key, question)
            for key in cls.PARAMETER_LABELS
        ):
            return True
        # A parameter-only continuation such as “rate to 3” remains a
        # simulation follow-up, but a normal definition question never does.
        return explicit_follow_up and any(
            cls._parameter_mentioned(key, question) for key in cls.PARAMETER_LABELS
        )

    @staticmethod
    def _is_explicit_follow_up(question: str) -> bool:
        """Only inherit a simulation when the learner explicitly continues it."""

        lowered = question.lower().strip()
        follow_up_markers = (
            "再",
            "继续",
            "上一轮",
            "上一次",
            "刚才",
            "给我看看",
            "看看",
            "把 lambda",
            "把λ",
            "把它",
            "改成",
            "改为",
            "调整为",
            "增加到",
            "减少到",
            "同样的",
            "show me",
            "show it",
            "visa mig",
            "visa det",
            "visa resultatet",
            "kör den",
            "kör igen",
            "sätt ",
            "ändra ",
            "vad ändrades",
            "vad förändrades",
            "run it",
            "visualize it",
            "visualise it",
            "rerun",
            "re-run",
            "run again",
            "set ",
            "use ",
            "try ",
            # Natural-language parameter comparisons are still simulation
            # follow-ups when an active run exists, for example
            # "What changes if I use 500 steps?".
            "what changes if",
            "what happens if",
            "what if i use",
            "what if we use",
            "if i use",
            "if we use",
            "increase the",
            "decrease the",
            "给我看看",
            "把 lambda",
            "设为",
        )
        if any(marker in lowered for marker in follow_up_markers):
            return True
        # Cover compact parameter-change questions without making every
        # question containing a number a follow-up.
        return bool(
            re.search(
                r"\b(?:change|compare|increase|decrease|use|set)\b.*\b(?:steps|paths|samples|rate|horizon|time)\b|\b(?:ändra|sätt|öka|minska)\b.*\b(?:steg|vägar|stickprov|intensitet|tid|lambda)\b",
                lowered,
            )
        )

    def answer(
        self,
        question: str,
        session_id: str | None = None,
        ui_language: str = "en",
        *,
        action_type: str | None = None,
        concept_id: str | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        normalized_question = validate_question(question)
        resolved_session = validate_session_id(session_id) or str(uuid.uuid4())
        history = self.memory.history(resolved_session, limit=1)
        context = self.memory.context(resolved_session)
        state = AgentState(
            question=normalized_question,
            session_id=resolved_session,
            previous_turn=history[-1] if history else None,
            active_experiment_id=context.get("active_experiment_id"),
            active_visualization_id=context.get("active_visualization_id"),
            active_parameters=context.get("active_parameters", {}),
            latest_result_reference=context.get("latest_result_reference"),
            latest_result_summary=context.get("latest_result_summary"),
            concept_id=context.get("related_concept_id"),
            profile=self.memory.profile(resolved_session),
            llm_metadata={**self._llm_metadata(), "status": "not_called", "latency_ms": 0.0, "retry_count": 0},
        )
        state.ui_language = ui_language if ui_language in {"en", "zh", "sv"} else "en"
        state.action_type = action_type if action_type in {"learn", "practice", "simulation", "quiz"} else None
        state.requested_concept_id = concept_id if concept_id in self.curriculum_agent.concepts else None
        state.requested_experiment_id = experiment_id if self.experiments.get(experiment_id) else None
        graph_result = self.workflow.invoke(
            {"runtime": state, "visited_nodes": [], "route_taken": "", "supplementary_query": ""}
        )
        return finalize_graph_response(self, graph_result, started)

    def handle_assessment(
        self,
        result: dict[str, Any],
        session_id: str,
        response_language: str = "en",
    ) -> dict[str, Any]:
        """Run Assessment → Curriculum → Tutor as an explicit graph handoff."""

        if not isinstance(result, dict) or not result.get("module_id"):
            raise ValueError("assessment result must include module_id")
        resolved_session = validate_session_id(session_id)
        if not resolved_session:
            raise ValueError("session_id is required for assessment handoff")
        module_id = str(result["module_id"])
        if module_id not in MODULE_BY_ID:
            raise ValueError("assessment module_id is not in the curriculum")
        state = AgentState(
            question=f"Assessment result for {module_id}",
            session_id=resolved_session,
            intent="quiz",
            module_id=module_id,
            assessment_input=dict(result),
            profile=self.memory.profile(resolved_session),
            llm_metadata={**self._llm_metadata(), "status": "not_called", "latency_ms": 0.0, "retry_count": 0},
        )
        state.ui_language = response_language if response_language in {"en", "zh", "sv"} else "en"
        state.response_language = state.ui_language
        started = time.perf_counter()
        graph_result = self.workflow.invoke(
            {"runtime": state, "visited_nodes": [], "route_taken": "", "supplementary_query": ""}
        )
        return finalize_graph_response(self, graph_result, started)
