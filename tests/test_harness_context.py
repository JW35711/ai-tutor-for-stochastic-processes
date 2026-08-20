from __future__ import annotations

import unittest

from src.harness.context import ContextBudget, compact_context


class HarnessContextTests(unittest.TestCase):
    def test_active_experiment_has_priority(self) -> None:
        snapshot = compact_context({
            "session_id": "learner-a",
            "active_experiment_id": "m04-brownian-increments",
            "active_parameters": {"steps": 100, "paths": 20},
            "module_id": "module04",
            "concept_id": "m04-brownian-increments",
            "question": "old",
        })
        self.assertEqual(snapshot.stable["active_experiment_id"], "m04-brownian-increments")
        self.assertEqual(snapshot.stable["active_parameters"]["steps"], 100)

    def test_arrays_and_secrets_are_not_carried(self) -> None:
        snapshot = compact_context({
            "active_parameters": {"steps": 4},
            "samples": list(range(100)),
            "raw_result": {"series": list(range(100))},
            "api_token": "do-not-copy",
            "password": "do-not-copy",
        })
        rendered = repr(snapshot.to_dict())
        self.assertNotIn("do-not-copy", rendered)
        self.assertNotIn("series", rendered)

    def test_recent_turns_are_bounded(self) -> None:
        turns = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
        snapshot = compact_context({"recent_turns": turns}, ContextBudget(max_recent_turns=3))
        self.assertEqual([item["question"] for item in snapshot.recent_turns], ["q17", "q18", "q19"])

    def test_evidence_locators_are_deduplicated(self) -> None:
        snapshot = compact_context({"sources": [{"source": "a#page-1"}, {"source": "a#page-1"}, {"source": "b#page-2"}]})
        self.assertEqual(snapshot.evidence_refs, ("a#page-1", "b#page-2"))

    def test_unicode_is_preserved(self) -> None:
        snapshot = compact_context({"session_id": "用户-å", "latest_result_summary": "平均值 λ=2"})
        self.assertIn("用户-å", snapshot.stable.values())
        self.assertIn("平均值 λ=2", snapshot.stable.values())

    def test_context_budget_is_enforced(self) -> None:
        snapshot = compact_context({"latest_result_summary": "x" * 2000, "sources": [{"source": f"s{i}"} for i in range(20)]}, ContextBudget(max_chars=300, max_evidence_refs=3))
        self.assertLessEqual(snapshot.after_chars, 300)
        self.assertLessEqual(len(snapshot.evidence_refs), 3)

    def test_snapshot_is_idempotent(self) -> None:
        first = compact_context({"module_id": "module04", "concept_id": "m04-brownian-increments", "recent_turns": [{"question": "q", "answer": "a"}]})
        second = compact_context(first.to_dict())
        self.assertEqual(first.stable, second.stable)
        self.assertEqual(first.recent_turns, second.recent_turns)
        self.assertEqual(first.evidence_refs, second.evidence_refs)

    def test_two_users_do_not_share_state(self) -> None:
        a = compact_context({"session_id": "a", "active_experiment_id": "exp-a"})
        b = compact_context({"session_id": "b", "active_experiment_id": "exp-b"})
        self.assertNotEqual(a.stable["session_id"], b.stable["session_id"])
        self.assertNotEqual(a.stable["active_experiment_id"], b.stable["active_experiment_id"])

    def test_assessed_state_is_kept_compact(self) -> None:
        snapshot = compact_context({"current_concept_mastery": {"status": "LEARNING", "mastery_score": 0.4}, "assessment_result": {"correctness": False}})
        self.assertEqual(snapshot.assessed_state["current_concept_mastery"]["status"], "LEARNING")

    def test_old_turns_drop_before_stable_context(self) -> None:
        snapshot = compact_context({"active_experiment_id": "exp", "recent_turns": [{"question": "x" * 500, "answer": "a" * 500} for _ in range(8)]}, ContextBudget(max_chars=500, max_recent_turns=8))
        self.assertEqual(snapshot.stable["active_experiment_id"], "exp")

    def test_source_content_is_not_serialized(self) -> None:
        snapshot = compact_context({"sources": [{"source": "notes#1", "content": "long private passage"}]})
        self.assertEqual(snapshot.evidence_refs, ("notes#1",))
        self.assertNotIn("long private passage", repr(snapshot.to_dict()))

    def test_empty_input_is_valid(self) -> None:
        snapshot = compact_context({})
        self.assertEqual(snapshot.stable, {})
        self.assertEqual(snapshot.after_chars, 70)

    def test_non_serializable_values_are_ignored(self) -> None:
        snapshot = compact_context({"active_parameters": {"value": object()}})
        self.assertNotIn("object at", repr(snapshot.to_dict()))


if __name__ == "__main__":
    unittest.main()
