#!/usr/bin/env python3
"""Run the independent natural-question holdout without a live LLM."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.credibility_metrics import answerability_metrics, ir_metrics  # noqa: E402
from evals.run_course_coverage_evaluation import OfflineLLM, _one_case  # noqa: E402
from src.agent import StochasticTutorAgent  # noqa: E402
from src.knowledge import KnowledgeBase  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402

CASES = ROOT / "evals" / "course_holdout_cases.json"


def run() -> dict:
    cases = json.loads(CASES.read_text("utf-8"))
    kb = KnowledgeBase()
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    agent.llm = OfflineLLM()  # type: ignore[assignment]
    try:
        rows = [_one_case(kb, agent, case) for case in cases]
    finally:
        memory.close()
    grounded = [row for row in rows if row.get("module_id") or row.get("concept_id")]
    report = {
        "suite": "course_holdout",
        "corpus_sha256": kb.corpus_sha256,
        "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
        "total": len(rows),
        "passed": sum(row["failure_stage"] == "PASS" for row in rows),
        "routing_module_accuracy": round(sum(row["module_id"] is None or row["module_id"] in {row["routed_module_id"], *row["related_module_ids"]} for row in rows) / len(rows), 4),
        "routing_concept_accuracy": round(sum(row["concept_id"] is None or row["concept_id"] in {row["routed_concept_id"], *row["related_concept_ids"]} for row in rows) / len(rows), 4),
        "retrieval": ir_metrics(row["real_rank"] for row in grounded),
        "answerability": answerability_metrics({"expected_status": row["expected_status"], "actual_status": row["actual_status"]} for row in rows),
        "quality_gate": {
            "module_accuracy_at_least_0_90": False,
            "retrieval_hit_at_3_at_least_0_90": False,
            "unsupported_answer_rate_zero": False,
        },
        "cases": rows,
    }
    report["quality_gate"] = {
        "module_accuracy_at_least_0_90": report["routing_module_accuracy"] >= 0.90,
        "retrieval_hit_at_3_at_least_0_90": report["retrieval"]["hit_at_3"] >= 0.90,
        "unsupported_answer_rate_zero": report["answerability"]["unsupported_answer_rate"] == 0.0,
    }
    report["quality_gate_passed"] = all(report["quality_gate"].values())
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, "utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "routing_module_accuracy", "routing_concept_accuracy", "retrieval", "answerability", "quality_gate_passed")}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["quality_gate_passed"] else 1)
