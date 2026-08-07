"""Persistent learner memory for the teaching agent.

The store deliberately uses SQLite from the Python standard library.  It keeps
the interview demo useful without an external database while making the
learning state survive a server restart.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any


DEFAULT_MEMORY_PATH = (
    Path(
        os.getenv(
            "TUTOR_MEMORY_PATH",
            str(
                Path(__file__).resolve().parent.parent
                / "artifacts"
                / "tutor_memory.sqlite3"
            ),
        )
    )
)


class LearnerMemory:
    """Store turns and derive a compact per-module learner profile."""

    def __init__(self, path: Path | str = DEFAULT_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA busy_timeout=5000")
        if str(self.path) != ":memory:":
            self._connection.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    tool TEXT,
                    parameters TEXT NOT NULL DEFAULT '{}',
                    verified INTEGER NOT NULL,
                    misconceptions TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS turns_session_index
                    ON turns(session_id, id);

                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    answer_index INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    bank_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS assessments_session_index
                    ON assessments(session_id, id);
                """
            )
            # Existing local demos may have created the first schema version.
            # Add new columns in place so a server upgrade never loses history.
            columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(turns)").fetchall()
            }
            if "parameters" not in columns:
                self._connection.execute(
                    "ALTER TABLE turns ADD COLUMN parameters TEXT NOT NULL DEFAULT '{}'"
                )
            assessment_columns = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(assessments)"
                ).fetchall()
            }
            if "bank_sha256" not in assessment_columns:
                self._connection.execute(
                    "ALTER TABLE assessments ADD COLUMN bank_sha256 TEXT"
                )

    def record_assessment(
        self,
        *,
        session_id: str,
        question_id: str,
        module_id: str,
        answer_index: int,
        correct: bool,
        bank_sha256: str | None = None,
    ) -> None:
        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sessions(session_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at
                """,
                (session_id, now, now),
            )
            self._connection.execute(
                """
                INSERT INTO assessments(
                    session_id, question_id, module_id, answer_index, correct,
                    bank_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    question_id,
                    module_id,
                    answer_index,
                    int(correct),
                    bank_sha256,
                    now,
                ),
            )

    def record_turn(
        self,
        *,
        session_id: str,
        question: str,
        module_id: str,
        topic: str,
        tool: str | None,
        parameters: dict[str, Any] | None,
        verified: bool,
        misconceptions: list[dict[str, str]],
    ) -> None:
        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sessions(session_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at
                """,
                (session_id, now, now),
            )
            self._connection.execute(
                """
                INSERT INTO turns(
                    session_id, question, module_id, topic, tool, parameters,
                    verified, misconceptions, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    question,
                    module_id,
                    topic,
                    tool,
                    json.dumps(parameters or {}, ensure_ascii=False),
                    int(verified),
                    json.dumps(misconceptions, ensure_ascii=False),
                    now,
                ),
            )

    def profile(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT module_id, topic, verified, misconceptions
                FROM turns WHERE session_id=? ORDER BY id
                """,
                (session_id,),
            ).fetchall()
            assessment_rows = self._connection.execute(
                """
                SELECT question_id, module_id, correct
                FROM assessments WHERE session_id=? ORDER BY id
                """,
                (session_id,),
            ).fetchall()

        modules: dict[str, dict[str, Any]] = {}
        misconception_counts: dict[str, dict[str, Any]] = {}
        for row in rows:
            module = modules.setdefault(
                row["module_id"],
                {
                    "module_id": row["module_id"],
                    "topic": row["topic"],
                    "attempts": 0,
                    "successful_runs": 0,
                    "mastery": 0.0,
                    "quiz_attempts": 0,
                    "quiz_correct": 0,
                },
            )
            module["attempts"] += 1
            module["successful_runs"] += int(row["verified"])

            for item in json.loads(row["misconceptions"]):
                code = item["code"]
                aggregate = misconception_counts.setdefault(
                    code,
                    {**item, "count": 0, "module_id": row["module_id"]},
                )
                aggregate["count"] += 1

        for row in assessment_rows:
            module = modules.setdefault(
                row["module_id"],
                {
                    "module_id": row["module_id"],
                    "topic": "assessment",
                    "attempts": 0,
                    "successful_runs": 0,
                    "mastery": 0.0,
                    "quiz_attempts": 0,
                    "quiz_correct": 0,
                },
            )
            module["quiz_attempts"] += 1
            module["quiz_correct"] += int(row["correct"])

        # Tool execution is evidence of practice, not proof of full mastery.
        # The score therefore grows conservatively and is capped below 1.
        for module in modules.values():
            practice_evidence = min(module["successful_runs"] / 3, 1.0)
            quiz_evidence = 0.0
            if module["quiz_attempts"]:
                quiz_accuracy = module["quiz_correct"] / module["quiz_attempts"]
                quiz_exposure = min(module["quiz_attempts"] / 2, 1.0)
                quiz_evidence = quiz_accuracy * quiz_exposure
            module["mastery"] = round(
                min(1.0, 0.1 + 0.35 * practice_evidence + 0.55 * quiz_evidence),
                2,
            )

        ordered_modules = sorted(modules.values(), key=lambda item: item["module_id"])
        weak_modules = [
            item["module_id"]
            for item in ordered_modules
            if item["mastery"] < 0.55
        ]
        return {
            "session_id": session_id,
            "turns": len(rows),
            "quiz_attempts": len(assessment_rows),
            "quiz_correct": sum(int(row["correct"]) for row in assessment_rows),
            "modules": ordered_modules,
            "covered_modules": [item["module_id"] for item in ordered_modules],
            "weak_modules": weak_modules,
            "misconceptions": sorted(
                misconception_counts.values(),
                key=lambda item: (-item["count"], item["code"]),
            ),
        }

    def history(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT question, module_id, topic, tool, parameters, verified, created_at
                FROM turns WHERE session_id=? ORDER BY id DESC LIMIT ?
                """,
                (session_id, safe_limit),
            ).fetchall()
        history: list[dict[str, Any]] = []
        for row in reversed(rows):
            item = dict(row)
            item["parameters"] = json.loads(item["parameters"])
            item["verified"] = bool(item["verified"])
            history.append(item)
        return history

    def assessment_history(
        self, session_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return recent quiz attempts with their content-version provenance."""

        safe_limit = max(1, min(int(limit), 100))
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT question_id, module_id, answer_index, correct,
                       bank_sha256, created_at
                FROM assessments WHERE session_id=? ORDER BY id DESC LIMIT ?
                """,
                (session_id, safe_limit),
            ).fetchall()
        attempts: list[dict[str, Any]] = []
        for row in reversed(rows):
            item = dict(row)
            item["correct"] = bool(item["correct"])
            attempts.append(item)
        return attempts

    def reset(self, session_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
            self._connection.execute(
                "DELETE FROM assessments WHERE session_id=?", (session_id,)
            )
            self._connection.execute(
                "DELETE FROM sessions WHERE session_id=?", (session_id,)
            )

    def purge_stale(self, retention_days: int) -> int:
        """Delete whole sessions older than the configured retention period."""

        if (
            isinstance(retention_days, bool)
            or not isinstance(retention_days, int)
            or retention_days < 1
        ):
            raise ValueError("retention_days must be a positive integer")
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=retention_days)
        ).isoformat(timespec="seconds")
        with self._lock, self._connection:
            rows = self._connection.execute(
                "SELECT session_id FROM sessions WHERE updated_at < ?",
                (cutoff,),
            ).fetchall()
            session_ids = [row["session_id"] for row in rows]
            for session_id in session_ids:
                self._connection.execute(
                    "DELETE FROM turns WHERE session_id=?", (session_id,)
                )
                self._connection.execute(
                    "DELETE FROM assessments WHERE session_id=?", (session_id,)
                )
                self._connection.execute(
                    "DELETE FROM sessions WHERE session_id=?", (session_id,)
                )
        return len(session_ids)

    def close(self) -> None:
        with self._lock:
            self._connection.close()
