"""Canonical catalogue for the eleven thesis teaching modules."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModuleSpec:
    """Metadata used by routing, retrieval, the API and the web interface."""

    module_id: str
    number: int
    topic: str
    label: str
    notebook: str
    keywords: tuple[str, ...]
    tool_key: str | None = None


MODULES: tuple[ModuleSpec, ...] = (
    ModuleSpec(
        "module00",
        0,
        "monte_carlo",
        "Monte Carlo simulation",
        "notebooks/00_Monte_Carlo.ipynb",
        ("monte carlo", "蒙特卡洛", "dice simulation", "掷骰子", "估计pi", "估计π"),
        "monte_carlo",
    ),
    ModuleSpec(
        "module01",
        1,
        "bernoulli_poisson",
        "Bernoulli and Poisson processes",
        "notebooks/01_Bernoulli&Poisson.ipynb",
        (
            "bernoulli process",
            "伯努利过程",
            "bernoulli arrivals",
            "伯努利到达",
            "poisson process",
            "泊松过程",
            "geometric waiting time",
            "几何等待时间",
            "exponential waiting time",
            "指数等待时间",
            "counting process",
            "计数过程",
            "poisson",
            "泊松",
        ),
        "poisson",
    ),
    ModuleSpec(
        "module02",
        2,
        "discrete_random_walk",
        "Discrete-time random walk",
        "notebooks/02_Random_Walk_Part1.ipynb",
        (
            "discrete time random walk",
            "discrete-time random walk",
            "离散时间随机游走",
            "gambler's ruin",
            "gamblers ruin",
            "赌徒破产",
            "hitting probability",
            "到达概率",
            "random walk endpoint",
            "随机游走终点",
            "random walk",
            "随机游走",
        ),
        "random_walk",
    ),
    ModuleSpec(
        "module03",
        3,
        "continuous_random_walk",
        "Continuous-time random walk",
        "notebooks/03_Random_Walk_Part2.ipynb",
        (
            "continuous time random walk",
            "continuous-time random walk",
            "连续时间随机游走",
            "poisson jump times",
            "泊松跳跃时刻",
            "random jump times",
            "随机跳跃时刻",
        ),
        "continuous_random_walk",
    ),
    ModuleSpec(
        "module04",
        4,
        "brownian_motion",
        "Brownian motion",
        "notebooks/04_Random_Walk_Part3.ipynb",
        (
            "brownian motion",
            "布朗运动",
            "wiener process",
            "维纳过程",
            "random walk approximation",
            "随机游走逼近",
            "gaussian increments",
            "高斯增量",
        ),
        "brownian_motion",
    ),
    ModuleSpec(
        "module05",
        5,
        "discrete_markov_chain",
        "Discrete-time Markov chains",
        "notebooks/05_Markov_Chain_Part1.ipynb",
        (
            "discrete time markov chain",
            "discrete-time markov chain",
            "离散时间马尔可夫链",
            "transition matrix",
            "转移矩阵",
            "stationary distribution",
            "平稳分布",
            "pagerank",
            "马尔可夫链",
            "markov chain",
            "markov",
        ),
        "markov_chain",
    ),
    ModuleSpec(
        "module06",
        6,
        "continuous_markov_chain",
        "Continuous-time Markov chains and birth-death processes",
        "notebooks/06_Markov_Chain_Part2.ipynb",
        (
            "continuous time markov chain",
            "continuous-time markov chain",
            "连续时间马尔可夫链",
            "birth death process",
            "birth-death process",
            "出生死亡过程",
            "generator matrix",
            "生成矩阵",
            "holding time",
            "停留时间",
            "ctmc",
        ),
        "ctmc",
    ),
    ModuleSpec(
        "module07",
        7,
        "applied_markov_models",
        "Reliability, buffers and M/M/1 queues",
        "notebooks/07_Markov_Chain_Part3.ipynb",
        (
            "reliability model",
            "可靠性模型",
            "series system",
            "parallel system",
            "串联系统",
            "并联系统",
            "survival function",
            "生存函数",
            "buffer model",
            "缓冲区模型",
            "m/m/1",
            "mm1",
            "queue stability",
            "排队稳定性",
            "hazard rate",
            "失效率",
        ),
    ),
    ModuleSpec(
        "module08",
        8,
        "nonhomogeneous_poisson",
        "Nonhomogeneous Poisson processes by thinning",
        "notebooks/08_Exploratory_Module_1.ipynb",
        (
            "nonhomogeneous poisson process",
            "non-homogeneous poisson process",
            "非齐次泊松过程",
            "time varying intensity",
            "时变强度",
            "thinning algorithm",
            "thinning method",
            "稀疏化算法",
            "接受拒绝法",
        ),
    ),
    ModuleSpec(
        "module09",
        9,
        "self_avoiding_walk",
        "Growing self-avoiding walks",
        "notebooks/09_Exploratory_Module_2.ipynb",
        (
            "growing self avoiding walk",
            "growing self-avoiding walk",
            "self avoiding walk",
            "self-avoiding walk",
            "自避免游走",
            "自回避游走",
            "path trapping",
            "路径受困",
            "blocked sites",
            "阻塞位置",
        ),
    ),
    ModuleSpec(
        "module10",
        10,
        "coalescing_particles",
        "Coalescing particles on a circle",
        "notebooks/10_Exploratory_Module_3.ipynb",
        (
            "coalescing particles",
            "coalescing particle",
            "粒子合并",
            "合并粒子",
            "particles on a circle",
            "圆上的粒子",
            "coalescence time",
            "合并时间",
            "cluster count",
            "簇数量",
        ),
    ),
)

MODULE_BY_ID = {module.module_id: module for module in MODULES}


def classify_module(question: str) -> str | None:
    """Return the best matching module, preferring explicit module numbers."""

    lowered = question.lower().replace("‑", "-").replace("–", "-")
    explicit = re.search(r"\bmodule\s*0*(10|[0-9])\b", lowered)
    if not explicit:
        explicit = re.search(r"模块\s*0*(10|[0-9])", lowered)
    if explicit:
        return f"module{int(explicit.group(1)):02d}"

    scored: list[tuple[int, int, str]] = []
    for module in MODULES:
        matched = [keyword for keyword in module.keywords if keyword in lowered]
        if matched:
            score = sum(10 + len(keyword) for keyword in matched)
            longest = max(len(keyword) for keyword in matched)
            scored.append((score, longest, module.module_id))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][2]


def module_catalog() -> list[dict[str, object]]:
    """Return JSON-ready public module metadata without routing keywords."""

    catalog: list[dict[str, object]] = []
    for module in MODULES:
        item = asdict(module)
        item.pop("keywords")
        item["tool_ready"] = module.tool_key is not None
        catalog.append(item)
    return catalog
