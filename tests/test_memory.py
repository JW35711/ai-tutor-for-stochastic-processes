import tempfile
import unittest
from pathlib import Path

from src.memory import LearnerMemory
from src.pedagogy import adaptive_note, diagnose


class LearnerMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.memory = LearnerMemory(Path(self.directory.name) / "memory.sqlite3")

    def tearDown(self) -> None:
        self.memory.close()
        self.directory.cleanup()

    def test_memory_survives_a_new_store_instance(self) -> None:
        self.memory.record_turn(
            session_id="learner-1",
            question="模拟布朗运动",
            module_id="module04",
            topic="brownian_motion",
            tool="brownian_motion",
            verified=True,
            misconceptions=[],
        )
        self.memory.close()
        self.memory = LearnerMemory(Path(self.directory.name) / "memory.sqlite3")
        profile = self.memory.profile("learner-1")
        self.assertEqual(profile["turns"], 1)
        self.assertEqual(profile["covered_modules"], ["module04"])

    def test_profile_aggregates_practice_and_misconceptions(self) -> None:
        misconception = {
            "code": "brownian_variance_sqrt_t",
            "explanation": "混淆方差与标准差。",
            "correction": "方差为T。",
        }
        for _ in range(2):
            self.memory.record_turn(
                session_id="learner-2",
                question="方差是根号T吗",
                module_id="module04",
                topic="brownian_motion",
                tool="brownian_motion",
                verified=True,
                misconceptions=[misconception],
            )
        profile = self.memory.profile("learner-2")
        self.assertEqual(profile["modules"][0]["attempts"], 2)
        self.assertEqual(profile["misconceptions"][0]["count"], 2)

    def test_reset_removes_one_session(self) -> None:
        self.memory.record_turn(
            session_id="to-reset",
            question="泊松过程",
            module_id="module01",
            topic="poisson",
            tool="poisson",
            verified=True,
            misconceptions=[],
        )
        self.memory.reset("to-reset")
        self.assertEqual(self.memory.profile("to-reset")["turns"], 0)


class PedagogyTests(unittest.TestCase):
    def test_detects_brownian_variance_misconception(self) -> None:
        findings = diagnose("布朗运动的方差是根号T，对吗？", "module04")
        self.assertEqual(findings[0]["code"], "brownian_variance_sqrt_t")

    def test_does_not_diagnose_unstated_misconception(self) -> None:
        self.assertEqual(diagnose("请模拟布朗运动", "module04"), [])

    def test_adaptive_note_changes_after_repeated_practice(self) -> None:
        profile = {
            "modules": [
                {"module_id": "module02", "attempts": 4, "mastery": 0.7}
            ]
        }
        self.assertIn("边界情形", adaptive_note(profile, "module02"))


if __name__ == "__main__":
    unittest.main()
