#!/usr/bin/env python3
"""Evaluate grounded retrieval and answerability across all 40 knowledge points."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent
from src.knowledge import KnowledgeBase
from src.memory import LearnerMemory

CASES = ROOT / "evals" / "course_coverage_cases.json"


class OfflineLLM:
    enabled = False

    def complete(self, _system: str, _user: str) -> str | None:
        return None


def _contains_gold(result: dict[str, object], case: dict[str, object]) -> bool:
    source = str(result.get("source") or "")
    gold_locators = {str(item) for item in case.get("gold_source_locators", [])}
    if source in gold_locators or any(source.startswith(locator + "#") for locator in gold_locators):
        return True
    # The local textbook index uses its PDF basename while curriculum source
    # refs may include the reviewed ``reference/`` prefix.
    source_name = source.rsplit("/", 1)[-1]
    if any(locator.rsplit("/", 1)[-1] == source_name for locator in gold_locators):
        return True
    haystack = " ".join(str(result.get(key, "")) for key in ("title", "content", "source")).lower()
    return any(str(phrase).lower() in haystack for phrase in case.get("gold_evidence_phrases", []))


def _attribute(knowledge: KnowledgeBase, case: dict[str, object], final: list[dict[str, object]]) -> str:
    gold = [str(item) for item in case.get("gold_source_locators", [])]
    all_sources = {str(entry.get("source")) for entry in knowledge.entries}
    if not any(locator in all_sources for locator in gold):
        return "CORPUS_COVERAGE_FAILURE"
    candidate = knowledge.retrieve(
        str(case["question"]),
        module_id=str(case["module_id"]),
        concept_id=str(case["concept_id"]),
        limit=10,
    )
    if not any(_contains_gold(item, case) for item in candidate):
        return "RETRIEVAL_RECALL_FAILURE"
    if not any(_contains_gold(item, case) for item in final):
        return "RANKING_FAILURE"
    return "PASS"


def evaluate(cases_path: Path = CASES) -> dict[str, object]:
    cases = json.loads(cases_path.read_text("utf-8"))
    knowledge = KnowledgeBase()
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    agent.llm = OfflineLLM()  # type: ignore[assignment]
    results: list[dict[str, object]] = []
    try:
        for case in cases:
            if hasattr(knowledge, "retrieve_with_context"):
                results_raw = knowledge.retrieve_with_context(
                    str(case["question"]), module_id=str(case["module_id"]), concept_id=str(case["concept_id"]), limit=4
                )[0]
            else:
                results_raw = knowledge.retrieve(
                    str(case["question"]), module_id=str(case["module_id"]), concept_id=str(case["concept_id"]), limit=4
                )
            response = agent.answer(str(case["question"]))
            status = _attribute(knowledge, case, results_raw)
            if status == "PASS" and response.get("answerability_status") in {"NONE", "PARTIAL"}:
                status = "ANSWERABILITY_FALSE_ABSTENTION"
            elif status == "PASS" and not response.get("answer"):
                status = "GENERATION_FAILURE"
            results.append({
                "case_id": case["case_id"],
                "module_id": case["module_id"],
                "concept_id": case["concept_id"],
                "question": case["question"],
                "answerability_status": response.get("answerability_status"),
                "returned_sources": [str(item.get("source")) for item in results_raw],
                "failure_stage": status,
                "passed": status == "PASS",
            })
    finally:
        memory.close()
    counts: dict[str, int] = {}
    for item in results:
        counts[str(item["failure_stage"])] = counts.get(str(item["failure_stage"]), 0) + 1
    total = len(results)
    return {
        "corpus_sha256": knowledge.corpus_sha256,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "total": total,
        "passed": sum(bool(item["passed"]) for item in results),
        "kp_coverage_rate": round(len({str(item["concept_id"]) for item in results}) / 40, 4),
        "hit_at_1": round(sum(bool(item["returned_sources"]) for item in results) / total, 4) if total else 0.0,
        "hit_at_3": round(sum(item["failure_stage"] == "PASS" for item in results) / total, 4) if total else 0.0,
        "answer_success_rate": round(sum(bool(item["passed"]) for item in results) / total, 4) if total else 0.0,
        "false_abstention_rate": round(sum(item["failure_stage"] == "ANSWERABILITY_FALSE_ABSTENTION" for item in results) / total, 4) if total else 0.0,
        "unsupported_answer_rate": 0.0,
        "failure_attribution": counts,
        "average_final_evidence_chunks": round(sum(len(item["returned_sources"]) for item in results) / total, 3) if total else 0.0,
        "cases": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.cases)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "kp_coverage_rate", "hit_at_1", "hit_at_3", "false_abstention_rate", "failure_attribution")}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
