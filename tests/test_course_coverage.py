from __future__ import annotations

import json
from pathlib import Path

from src.curriculum import load_curriculum
from src.knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


def test_course_coverage_has_three_grounded_cases_per_knowledge_point() -> None:
    curriculum = load_curriculum()
    expected = {
        point["id"]
        for module in curriculum["modules"]
        for point in module["knowledge_points"]
    }
    cases = json.loads((ROOT / "evals" / "course_coverage_cases.json").read_text("utf-8"))
    assert len(expected) == 40
    assert len(cases) == 120
    assert {case["concept_id"] for case in cases} == expected
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(case["verified"] and case["gold_source_locators"] for case in cases)


def test_all_gold_locators_exist_in_the_loaded_course_corpus() -> None:
    knowledge = KnowledgeBase()
    sources = [str(entry.get("source") or "") for entry in knowledge.entries]
    cases = json.loads((ROOT / "evals" / "course_coverage_cases.json").read_text("utf-8"))
    for case in cases:
        for locator in case["gold_source_locators"]:
            basename = Path(locator.split("#", 1)[0]).name
            assert any(
                source == locator
                or source.startswith(locator)
                or Path(source.split("#", 1)[0]).name == basename
                for source in sources
            ), (case["case_id"], locator)
