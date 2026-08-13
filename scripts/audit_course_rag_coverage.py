#!/usr/bin/env python3
"""Emit a machine-readable coverage matrix for all 40 curriculum KPs."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.curriculum import load_curriculum
from src.knowledge import KnowledgeBase


def audit() -> dict[str, object]:
    curriculum = load_curriculum()
    knowledge = KnowledgeBase()
    matrix: list[dict[str, object]] = []
    for module in curriculum["modules"]:
        for point in module["knowledge_points"]:
            concept_id = point["id"]
            entries = [entry for entry in knowledge.entries if entry.get("concept_id") == concept_id]
            module_entries = [entry for entry in knowledge.entries if entry.get("module_id") == module["module_id"]]
            types = Counter(entry.get("content_type") for entry in entries)
            queries = [
                f"What is {point['title']}?",
                f"Why is {point['title']} important?",
                f"How is {point['title']} interpreted in the course examples?",
            ]
            successful = []
            failures = []
            for query in queries:
                results = knowledge.retrieve(query, module_id=module["module_id"], concept_id=concept_id, limit=3)
                if any(result.get("concept_id") == concept_id or result.get("module_id") == module["module_id"] for result in results):
                    successful.append(query)
                else:
                    failures.append({"query": query, "stage": "RETRIEVAL_RECALL_FAILURE"})
            matrix.append({
                "module_id": module["module_id"],
                "concept_id": concept_id,
                "title": point["title"],
                "curated_entries": sum(entry.get("kind") == "curated" for entry in entries),
                "notebook_chunks": sum(entry.get("kind") == "notebook_cell" for entry in entries),
                "textbook_chunks": sum(entry.get("kind") == "textbook_chunk" for entry in entries),
                "reference_chunks": sum(entry.get("kind") == "reference_chunk" for entry in entries),
                "module_evidence_count": len(module_entries),
                "source_locators": list(dict.fromkeys(str(entry.get("source")) for entry in entries)),
                "content_type_counts": dict(types),
                "benchmark_queries": queries,
                "successful_retrieval_queries": successful,
                "answerable_queries": successful,
                "failures_by_stage": failures,
            })
    return {
        "knowledge_points": len(matrix),
        "entries": knowledge.stats(),
        "coverage_rate": round(sum(bool(item["successful_retrieval_queries"]) for item in matrix) / len(matrix), 4),
        "matrix": matrix,
    }


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts" / "course_rag_coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = audit()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"knowledge_points": report["knowledge_points"], "coverage_rate": report["coverage_rate"], "output": str(output)}))
