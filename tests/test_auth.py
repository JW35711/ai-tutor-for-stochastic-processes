import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.auth import hash_password, normalize_username, verify_password
from src.memory import LearnerMemory


class AuthPrimitiveTests(unittest.TestCase):
    def test_scrypt_hash_is_versioned_and_constant_time_verified(self) -> None:
        encoded = hash_password("correct horse battery staple")
        self.assertTrue(encoded.startswith("scrypt$v1$"))
        self.assertTrue(verify_password("correct horse battery staple", encoded))
        self.assertFalse(verify_password("wrong password", encoded))
        self.assertNotEqual(encoded, hash_password("correct horse battery staple"))

    def test_username_normalization_is_bounded(self) -> None:
        self.assertEqual(normalize_username("  Alpha_01 "), "alpha_01")
        with self.assertRaises(ValueError):
            normalize_username("bad space")

    def test_user_identity_and_auth_token_persist_in_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "learner.sqlite3"
            memory = LearnerMemory(path)
            user = memory.create_user("Alpha_01", "password123")
            token = "a" * 43
            expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            memory.create_auth_session(token, user["user_id"], expires)
            self.assertEqual(memory.user_for_auth_token(token)["username"], "alpha_01")
            self.assertEqual(memory.user_for_auth_token(token)["learner_session_id"], user["learner_session_id"])
            memory.close()
            reopened = LearnerMemory(path)
            try:
                self.assertEqual(reopened.user_for_auth_token(token)["user_id"], user["user_id"])
            finally:
                reopened.close()

    def test_expired_and_invalid_tokens_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = LearnerMemory(Path(directory) / "learner.sqlite3")
            user = memory.create_user("alpha_02", "password123")
            expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            memory.create_auth_session("expired-token", user["user_id"], expired)
            self.assertIsNone(memory.user_for_auth_token("expired-token"))
            self.assertIsNone(memory.user_for_auth_token("not-a-token"))
            memory.close()

    def test_retention_does_not_delete_registered_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = LearnerMemory(Path(directory) / "learner.sqlite3")
            user = memory.create_user("retained_user", "password123")
            old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
            with memory._lock, memory._connection:
                memory._connection.execute("UPDATE sessions SET updated_at=? WHERE session_id=?", (old, user["learner_session_id"]))
            self.assertEqual(memory.purge_stale(1), 0)
            self.assertIsNotNone(memory.user_with_identity(user["user_id"]))
            memory.close()
