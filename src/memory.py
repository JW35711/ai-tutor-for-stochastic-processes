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

from .config import env_int


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
SCHEMA_VERSION = 5


class LearnerMemory:
    """Store turns and derive a compact per-module learner profile."""

    def __init__(
        self,
        path: Path | str = DEFAULT_MEMORY_PATH,
        max_events_per_session: int | None = None,
    ) -> None:
        self.path = Path(path)
        configured_limit = (
            env_int(
                "MAX_SESSION_EVENTS",
                1000,
                minimum=1,
                maximum=1_000_000,
            )
            if max_events_per_session is None
            else max_events_per_session
        )
        if (
            isinstance(configured_limit, bool)
            or not isinstance(configured_limit, int)
            or configured_limit < 1
        ):
            raise ValueError("max_events_per_session must be a positive integer")
        self.max_events_per_session = configured_limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA busy_timeout=5000")
        if str(self.path) != ":memory:":
            self._connection.execute("PRAGMA journal_mode=WAL")
        try:
            self._create_schema()
        except Exception:
            self._connection.close()
            raise

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            existing_version = self._connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            if existing_version > SCHEMA_VERSION:
                raise RuntimeError(
                    "learner database schema is newer than this application"
                )
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

                CREATE TABLE IF NOT EXISTS concept_mastery (
                    session_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    mastery_score REAL NOT NULL DEFAULT 0,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    correct_count INTEGER NOT NULL DEFAULT 0,
                    hint_count INTEGER NOT NULL DEFAULT 0,
                    recent_misconceptions TEXT NOT NULL DEFAULT '[]',
                    last_practiced_at TEXT,
                    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                    PRIMARY KEY(session_id, concept_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    concept_id TEXT,
                    question_id TEXT,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS learning_events_session_index
                    ON learning_events(session_id, id);

                CREATE TABLE IF NOT EXISTS tutor_context (
                    session_id TEXT PRIMARY KEY,
                    active_experiment_id TEXT,
                    active_visualization_id TEXT,
                    active_parameters TEXT NOT NULL DEFAULT '{}',
                    latest_result_reference TEXT,
                    latest_result_summary TEXT,
                    related_concept_id TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );
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
            context_columns = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(tutor_context)"
                ).fetchall()
            }
            if context_columns and "latest_result_summary" not in context_columns:
                self._connection.execute(
                    "ALTER TABLE tutor_context ADD COLUMN latest_result_summary TEXT"
                )
            self._connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @property
    def schema_version(self) -> int:
        with self._lock:
            return int(
                self._connection.execute("PRAGMA user_version").fetchone()[0]
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
            self._prune_session_events("assessments", session_id)

    def record_learning_event(
        self,
        *,
        session_id: str,
        event_type: str,
        concept_id: str | None = None,
        question_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO sessions(session_id, created_at, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at",
                (session_id, now, now),
            )
            self._connection.execute(
                "INSERT INTO learning_events(session_id, event_type, concept_id, question_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, event_type, concept_id, question_id, json.dumps(payload or {}, ensure_ascii=False), now),
            )
            self._prune_session_events("learning_events", session_id)

    def record_hint_used(
        self,
        *,
        session_id: str,
        concept_id: str,
        question_id: str | None = None,
        hint_level: int = 1,
    ) -> None:
        """Persist a hint event without changing mastery score or status."""

        self.record_learning_event(
            session_id=session_id,
            event_type="HINT_USED",
            concept_id=concept_id,
            question_id=question_id,
            payload={"hint_level": max(1, min(int(hint_level), 3))},
        )

    def update_concept_mastery(self, *, session_id: str, state: dict[str, Any]) -> None:
        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO sessions(session_id, created_at, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at",
                (session_id, now, now),
            )
            self._connection.execute(
                """INSERT INTO concept_mastery(session_id, concept_id, mastery_score, attempt_count, correct_count, hint_count, recent_misconceptions, last_practiced_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, concept_id) DO UPDATE SET mastery_score=excluded.mastery_score, attempt_count=excluded.attempt_count, correct_count=excluded.correct_count, hint_count=excluded.hint_count, recent_misconceptions=excluded.recent_misconceptions, last_practiced_at=excluded.last_practiced_at, status=excluded.status""",
                (session_id, state["concept_id"], state.get("mastery_score", 0), state.get("attempt_count", 0), state.get("correct_count", 0), state.get("hint_count", 0), json.dumps(state.get("recent_misconceptions", []), ensure_ascii=False), state.get("last_practiced_at"), state.get("status", "NOT_STARTED")),
            )

    def concept_mastery(self, session_id: str, concept_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM concept_mastery WHERE session_id=?"
        params: list[Any] = [session_id]
        if concept_id:
            query += " AND concept_id=?"
            params.append(concept_id)
        query += " ORDER BY concept_id"
        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item.pop("session_id", None)
            item["recent_misconceptions"] = json.loads(item["recent_misconceptions"])
            result.append(item)
        return result

    def learning_events(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), self.max_events_per_session))
        with self._lock:
            rows = self._connection.execute("SELECT event_type, concept_id, question_id, payload, created_at FROM learning_events WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, safe_limit)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in reversed(rows)]

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
            self._prune_session_events("turns", session_id)

    def context(self, session_id: str) -> dict[str, Any]:
        """Return compact active-experiment state, never raw arrays."""

        with self._lock:
            row = self._connection.execute(
                "SELECT active_experiment_id, active_visualization_id, active_parameters, latest_result_reference, latest_result_summary, related_concept_id FROM tutor_context WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if row is None:
            return {}
        item = dict(row)
        item["active_parameters"] = json.loads(item.pop("active_parameters") or "{}")
        return item

    def save_context(
        self,
        *,
        session_id: str,
        active_experiment_id: str | None,
        active_visualization_id: str | None,
        active_parameters: dict[str, Any] | None,
        latest_result_reference: str | None,
        latest_result_summary: str | None = None,
        related_concept_id: str | None,
    ) -> None:
        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO sessions(session_id, created_at, updated_at) VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at",
                (session_id, now, now),
            )
            self._connection.execute(
                """INSERT INTO tutor_context(session_id, active_experiment_id, active_visualization_id, active_parameters, latest_result_reference, latest_result_summary, related_concept_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET active_experiment_id=excluded.active_experiment_id, active_visualization_id=excluded.active_visualization_id, active_parameters=excluded.active_parameters, latest_result_reference=excluded.latest_result_reference, latest_result_summary=excluded.latest_result_summary, related_concept_id=excluded.related_concept_id, updated_at=excluded.updated_at""",
                (session_id, active_experiment_id, active_visualization_id, json.dumps(active_parameters or {}, ensure_ascii=False), latest_result_reference, latest_result_summary, related_concept_id, now),
            )

    def _prune_session_events(self, table: str, session_id: str) -> None:
        if table not in {"turns", "assessments", "learning_events"}:
            raise ValueError("unsupported learner event table")
        # The table name is selected only from the internal allowlist above.
        self._connection.execute(
            f"""
            DELETE FROM {table}
            WHERE session_id=? AND id NOT IN (
                SELECT id FROM {table}
                WHERE session_id=? ORDER BY id DESC LIMIT ?
            )
            """,
            (session_id, session_id, self.max_events_per_session),
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
        concept_rows = self.concept_mastery(session_id)
        with self._lock:
            hint_rows = self._connection.execute(
                "SELECT concept_id, COUNT(*) AS count FROM learning_events WHERE session_id=? AND event_type='HINT_USED' AND concept_id IS NOT NULL GROUP BY concept_id",
                (session_id,),
            ).fetchall()
        hint_counts = {str(row["concept_id"]): int(row["count"]) for row in hint_rows}
        for concept in concept_rows:
            concept["hint_count"] = max(int(concept.get("hint_count", 0) or 0), hint_counts.get(str(concept["concept_id"]), 0))

        modules: dict[str, dict[str, Any]] = {}
        module_question_ids: dict[str, set[str]] = {}
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
                    "distinct_quiz_questions": 0,
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
                    "distinct_quiz_questions": 0,
                },
            )
            module["quiz_attempts"] += 1
            module["quiz_correct"] += int(row["correct"])
            module_question_ids.setdefault(row["module_id"], set()).add(
                row["question_id"]
            )

        # Tool execution is evidence of practice, not proof of full mastery.
        # The score therefore grows conservatively and is capped below 1.
        for module in modules.values():
            distinct_questions = len(
                module_question_ids.get(module["module_id"], set())
            )
            module["distinct_quiz_questions"] = distinct_questions
            practice_evidence = min(module["successful_runs"] / 3, 1.0)
            quiz_evidence = 0.0
            if module["quiz_attempts"]:
                quiz_accuracy = module["quiz_correct"] / module["quiz_attempts"]
                quiz_exposure = min(distinct_questions / 2, 1.0)
                quiz_evidence = quiz_accuracy * quiz_exposure
            module["mastery"] = round(
                min(1.0, 0.1 + 0.35 * practice_evidence + 0.55 * quiz_evidence),
                2,
            )

        ordered_modules = sorted(modules.values(), key=lambda item: item["module_id"])
        concept_by_module: dict[str, list[dict[str, Any]]] = {}
        for concept in concept_rows:
            prefix = concept["concept_id"].split("-", 1)[0]
            module_id = f"module{prefix[1:]}" if prefix.startswith("m") else prefix
            concept_by_module.setdefault(module_id, []).append(concept)
            modules.setdefault(
                module_id,
                {
                    "module_id": module_id,
                    "topic": "knowledge_point",
                    "attempts": 0,
                    "successful_runs": 0,
                    "mastery": 0.0,
                    "quiz_attempts": 0,
                    "quiz_correct": 0,
                    "distinct_quiz_questions": 0,
                },
            )
        ordered_modules = sorted(modules.values(), key=lambda item: item["module_id"])
        for module in ordered_modules:
            children = concept_by_module.get(module["module_id"], [])
            if children:
                module["knowledge_points"] = children
                module["mastery"] = round(sum(float(item["mastery_score"]) for item in children) / len(children), 2)
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
            "knowledge_points": concept_rows,
        }

    def history(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), self.max_events_per_session))
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

        safe_limit = max(1, min(int(limit), self.max_events_per_session))
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

    def snapshot(self, session_id: str) -> dict[str, Any]:
        """Export all retained learner-owned records for one session."""

        return {
            "schema_version": 1,
            "session_id": session_id,
            "profile": self.profile(session_id),
            "turns": self.history(session_id, self.max_events_per_session),
            "assessments": self.assessment_history(
                session_id, self.max_events_per_session
            ),
            "knowledge_points": self.concept_mastery(session_id),
            "learning_events": self.learning_events(session_id, self.max_events_per_session),
        }

    def reset(self, session_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
            self._connection.execute(
                "DELETE FROM assessments WHERE session_id=?", (session_id,)
            )
            self._connection.execute("DELETE FROM concept_mastery WHERE session_id=?", (session_id,))
            self._connection.execute("DELETE FROM learning_events WHERE session_id=?", (session_id,))
            self._connection.execute("DELETE FROM tutor_context WHERE session_id=?", (session_id,))
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
                self._connection.execute("DELETE FROM concept_mastery WHERE session_id=?", (session_id,))
                self._connection.execute("DELETE FROM learning_events WHERE session_id=?", (session_id,))
                self._connection.execute(
                    "DELETE FROM sessions WHERE session_id=?", (session_id,)
                )
        return len(session_ids)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def is_ready(self) -> bool:
        """Check whether the learner store can serve a query."""

        try:
            with self._lock:
                return self._connection.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False
