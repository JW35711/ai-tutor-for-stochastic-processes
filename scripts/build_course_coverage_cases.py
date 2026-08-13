#!/usr/bin/env python3
"""Build the grounded three-question-per-KP course retrieval benchmark.

The benchmark is generated from the checked curriculum and the current local
course corpus.  It refuses to count a KP when no indexed source can provide a
verified locator, so the file cannot silently grow from invented evidence.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.curriculum import load_curriculum
from src.knowledge import KnowledgeBase

OUTPUT = ROOT / "evals" / "course_coverage_cases.json"


def _phrase(entry: dict[str, object]) -> str:
    title = str(entry.get("title") or "").strip()
    if len(title) >= 8 and not title.lower().startswith("notebook teaching note"):
        return title
    content = re.sub(r"\s+", " ", str(entry.get("content") or "")).strip()
    words = content.split()
    # Short PDF extraction fragments are useful locators but poor evidence
    # phrases.  Prefer a stable title/heading, and skip noise-only fragments.
    if len(words) < 4 or any(token in {"contents", "figure", "example", "exercises"} for token in words[:2]):
        return ""
    return " ".join(words[: min(8, len(words))])


def _case_phrases(point: dict[str, object], mapped: list[dict[str, object]]) -> list[str]:
    """Use source headings plus curriculum aliases as verified query anchors."""
    phrases = [str(item) for item in point.get("title", "").split("|") if str(item).strip()]
    for entry in mapped[:8]:
        phrase = _phrase(entry)
        if phrase:
            phrases.append(phrase)
    return list(dict.fromkeys(phrases))


def build() -> list[dict[str, object]]:
    curriculum = load_curriculum()
    knowledge = KnowledgeBase()
    cases: list[dict[str, object]] = []
    unverified: list[dict[str, object]] = []
    for module in curriculum["modules"]:
        module_id = module["module_id"]
        for point in module["knowledge_points"]:
            concept_id = point["id"]
            source_refs = [str(ref) for ref in point.get("source_refs", [])]
            mapped = [
                entry for entry in knowledge.entries
                if entry.get("source") and any(
                    str(entry["source"]) == ref or str(entry["source"]).startswith(ref + "#")
                    for ref in source_refs
                )
            ]
            if not mapped:
                mapped = [entry for entry in knowledge.entries if entry.get("concept_id") == concept_id]
            mapped.sort(key=lambda entry: (0 if entry.get("kind") == "notebook_cell" else 1, str(entry.get("source"))))
            locators = list(dict.fromkeys(source_refs or [str(entry["source"]) for entry in mapped[:5]]))
            phrases = _case_phrases(point, mapped)
            verified = bool(locators and mapped)
            templates = (
                ("definition", f"What is {point['title']} in this course?"),
                ("why", f"Why does the course study {point['title']}?"),
                ("application", f"How does the course use {point['title']} in an example?"),
            )
            for index, (question_type, question) in enumerate(templates, start=1):
                case = {
                    "case_id": f"coverage-{concept_id}-{index}",
                    "module_id": module_id,
                    "concept_id": concept_id,
                    "question": question,
                    "question_type": question_type,
                    "gold_source_locators": locators,
                    "gold_evidence_phrases": phrases,
                    "required_claims": [point["summary"]],
                    "verified": verified,
                }
                cases.append(case)
            if not verified:
                unverified.append({"concept_id": concept_id, "module_id": module_id})
    if unverified:
        raise RuntimeError(f"unverified KPs cannot enter the benchmark: {unverified}")
    OUTPUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return cases


if __name__ == "__main__":
    result = build()
    print(json.dumps({"cases": len(result), "knowledge_points": len(result) // 3, "output": str(OUTPUT)}))
