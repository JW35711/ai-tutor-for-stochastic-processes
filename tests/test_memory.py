import tempfile
import unittest
import sqlite3
from concurrent.futures import ThreadPoolExecutor
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
            parameters={"horizon": 1.0, "paths": 500},
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
                parameters={"horizon": 1.0},
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
            parameters={"rate": 2.0},
            verified=True,
            misconceptions=[],
        )
        self.memory.reset("to-reset")
        self.assertEqual(self.memory.profile("to-reset")["turns"], 0)

    def test_history_restores_structured_tool_parameters(self) -> None:
        self.memory.record_turn(
            session_id="context-user",
            question="模拟泊松过程",
            module_id="module01",
            topic="poisson",
            tool="poisson",
            parameters={"rate": 3.0, "horizon": 4.0},
            verified=True,
            misconceptions=[],
        )
        turn = self.memory.history("context-user", limit=1)[0]
        self.assertEqual(turn["parameters"], {"rate": 3.0, "horizon": 4.0})
        self.assertTrue(turn["verified"])

    def test_concurrent_turns_are_serialized_without_loss(self) -> None:
        def record(index: int) -> None:
            self.memory.record_turn(
                session_id="concurrent-learner",
                question=f"实验 {index}",
                module_id="module02",
                topic="discrete_random_walk",
                tool="random_walk",
                parameters={"steps": index + 1},
                verified=True,
                misconceptions=[],
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(record, range(40)))
        profile = self.memory.profile("concurrent-learner")
        self.assertEqual(profile["turns"], 40)
        self.assertEqual(profile["modules"][0]["successful_runs"], 40)

    def test_retention_purges_only_stale_whole_sessions(self) -> None:
        for session_id in ("stale", "active"):
            self.memory.record_turn(
                session_id=session_id,
                question="模拟布朗运动",
                module_id="module04",
                topic="brownian_motion",
                tool="brownian_motion",
                parameters={"horizon": 1.0},
                verified=True,
                misconceptions=[],
            )
        with self.memory._lock, self.memory._connection:
            self.memory._connection.execute(
                "UPDATE sessions SET updated_at=? WHERE session_id=?",
                ("2000-01-01T00:00:00+00:00", "stale"),
            )
        self.assertEqual(self.memory.purge_stale(30), 1)
        self.assertEqual(self.memory.profile("stale")["turns"], 0)
        self.assertEqual(self.memory.profile("active")["turns"], 1)

    def test_retention_rejects_disabled_or_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.memory.purge_stale(0)

    def test_existing_first_version_database_is_migrated_in_place(self) -> None:
        legacy_path = Path(self.directory.name) / "legacy.sqlite3"
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            """
            CREATE TABLE turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                module_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                tool TEXT,
                verified INTEGER NOT NULL,
                misconceptions TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        connection.close()
        migrated = LearnerMemory(legacy_path)
        columns = {
            row["name"]
            for row in migrated._connection.execute("PRAGMA table_info(turns)")
        }
        self.assertIn("parameters", columns)
        migrated.close()


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
