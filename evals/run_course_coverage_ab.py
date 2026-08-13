#!/usr/bin/env python3
"""Compare current hybrid ordering with a transparent deterministic reranker."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge import KnowledgeBase


def _hit(items: list[dict], gold: list[str], k: int) -> bool:
    top = items[:k]
    for item in top:
        source = str(item.get("source") or "")
        for locator in gold:
            if source == locator or source.startswith(locator) or Path(source.split("#", 1)[0]).name == Path(locator.split("#", 1)[0]).name:
                return True
    return False


def _mrr(items: list[dict], gold: list[str]) -> float:
    for index, item in enumerate(items, start=1):
        if _hit([item], gold, 1):
            return 1.0 / index
    return 0.0


def run(cases_path: Path) -> dict:
    cases = json.loads(cases_path.read_text("utf-8"))
    knowledge = KnowledgeBase()
    rows: list[dict] = []
    for case in cases:
        timings = {"baseline": [], "deterministic_rerank": []}
        outputs = {}
        for variant in ("baseline", "deterministic_rerank"):
            started = time.perf_counter()
            outputs[variant] = knowledge.retrieve_ab(
                case["question"],
                module_id=case["module_id"],
                concept_id=case["concept_id"],
                limit=3,
            )[variant]
            timings[variant].append((time.perf_counter() - started) * 1000)
        rows.append({
            "case_id": case["case_id"],
            "gold_source_locators": case["gold_source_locators"],
            "variants": {
                name: {
                    "hit_at_1": _hit(items, case["gold_source_locators"], 1),
                    "hit_at_3": _hit(items, case["gold_source_locators"], 3),
                    "mrr": _mrr(items, case["gold_source_locators"]),
                    "latency_ms": timings[name][0],
                }
                for name, items in outputs.items()
            },
        })
    summary = {}
    for variant in ("baseline", "deterministic_rerank"):
        metrics = [row["variants"][variant] for row in rows]
        summary[variant] = {
            "hit_at_1": sum(item["hit_at_1"] for item in metrics) / len(metrics),
            "hit_at_3": sum(item["hit_at_3"] for item in metrics) / len(metrics),
            "mrr": sum(item["mrr"] for item in metrics) / len(metrics),
            "mean_latency_ms": statistics.mean(item["latency_ms"] for item in metrics),
            "p95_latency_ms": sorted(item["latency_ms"] for item in metrics)[max(0, int(len(metrics) * 0.95) - 1)],
        }
    delta = {
        key: summary["deterministic_rerank"][key] - summary["baseline"][key]
        for key in ("hit_at_1", "hit_at_3", "mrr", "mean_latency_ms")
    }
    return {
        "corpus_sha256": knowledge.corpus_sha256,
        "cases": len(cases),
        "summary": summary,
        "delta": delta,
        "production_reranker_kept": bool(delta["hit_at_3"] > 0.005 and delta["mean_latency_ms"] < 20),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "evals" / "course_coverage_cases.json")
    parser.add_argument("--output", type=Path, default=Path("/tmp/course_coverage_ab.json"))
    args = parser.parse_args()
    report = run(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("corpus_sha256", "cases", "summary", "delta", "production_reranker_kept")}, indent=2))


if __name__ == "__main__":
    main()
