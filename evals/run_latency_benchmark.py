"""Measure local Agent latency without presenting it as a hosted SLA."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402


DEFAULT_CASES = Path(__file__).with_name("cases.json")
DEFAULT_REPORT = ROOT / "artifacts" / "latency_benchmark.json"


def percentile(values: list[float], percentage: float) -> float:
    """Return the nearest-rank percentile for a non-empty sample."""

    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 < percentage <= 100:
        raise ValueError("percentage must be in (0, 100]")
    ordered = sorted(values)
    rank = max(1, math.ceil((percentage / 100) * len(ordered)))
    return ordered[rank - 1]


def summary(values: list[float]) -> dict[str, float | int]:
    return {
        "samples": len(values),
        "mean_ms": round(statistics.fmean(values), 2),
        "p50_ms": round(percentile(values, 50), 2),
        "p95_ms": round(percentile(values, 95), 2),
        "max_ms": round(max(values), 2),
    }


def representative_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the first acceptance prompt for each of the 11 modules."""

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in cases:
        module_id = case["expected_module"]
        if module_id not in seen:
            selected.append(case)
            seen.add(module_id)
    expected = {f"module{index:02d}" for index in range(11)}
    if seen != expected:
        raise ValueError("benchmark cases must cover module00 through module10")
    return selected


def benchmark(
    cases: list[dict[str, Any]], repetitions: int = 2
) -> dict[str, Any]:
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("repetitions must be a positive integer")

    selected = representative_cases(cases)
    end_to_end: list[float] = []
    by_module: dict[str, list[float]] = {case["expected_module"]: [] for case in selected}
    by_node: dict[str, list[float]] = {}
    with tempfile.TemporaryDirectory() as directory:
        memory = LearnerMemory(Path(directory) / "benchmark.sqlite3")
        agent = StochasticTutorAgent(memory=memory)
        corpus_sha256 = agent.knowledge.corpus_sha256
        try:
            for repetition in range(repetitions):
                for case in selected:
                    started = time.perf_counter()
                    response = agent.answer(
                        case["question"],
                        session_id=f"benchmark-{repetition}-{case['expected_module']}",
                    )
                    duration_ms = (time.perf_counter() - started) * 1000
                    if response["module_id"] != case["expected_module"]:
                        raise RuntimeError(
                            f"benchmark routing drifted for {case['id']}"
                        )
                    end_to_end.append(duration_ms)
                    by_module[case["expected_module"]].append(duration_ms)
                    for trace_item in response["trace"]:
                        by_node.setdefault(trace_item["node"], []).append(
                            float(trace_item["duration_ms"])
                        )
        finally:
            memory.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "local deterministic offline benchmark; not a production SLA",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "corpus_sha256": corpus_sha256,
        "modules": len(selected),
        "repetitions": repetitions,
        "end_to_end": summary(end_to_end),
        "by_module": {
            module_id: summary(values) for module_id, values in by_module.items()
        },
        "by_node": {
            node: summary(values) for node, values in by_node.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text("utf-8"))
    report = benchmark(cases, repetitions=args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        "utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
