import json
import unittest
from unittest.mock import patch

from src.llm import OpenAICompatibleLLM, preserves_verified_facts


class ByteResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]


class LLMGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.draft = (
            "经验均值 1.25，理论值 1.5。\n"
            "来源：notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.sources = [
            {"source": "notebooks/04_Random_Walk_Part3.ipynb#cell-4"}
        ]

    def test_accepts_rewrite_that_preserves_numbers_and_source(self) -> None:
        candidate = (
            "理论值 1.5，而本次经验均值为 1.25。\n"
            "notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.assertTrue(
            preserves_verified_facts(candidate, self.draft, self.sources)
        )

    def test_rejects_changed_number(self) -> None:
        candidate = (
            "经验均值 1.20，理论值 1.5。\n"
            "notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.assertFalse(
            preserves_verified_facts(candidate, self.draft, self.sources)
        )

    def test_rejects_missing_source(self) -> None:
        self.assertFalse(
            preserves_verified_facts(
                "经验均值 1.25，理论值 1.5。",
                self.draft,
                self.sources,
            )
        )

    def test_incidental_numbers_outside_result_summary_are_not_anchors(self) -> None:
        candidate = (
            "经验均值 1.25。\n"
            "notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.assertTrue(
            preserves_verified_facts(
                candidate,
                "经验均值 1.25。",
                self.sources,
            )
        )

    def test_provider_response_over_limit_falls_back_offline(self) -> None:
        environment = {
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "test-model",
            "LLM_MAX_RESPONSE_BYTES": "1024",
        }
        with patch.dict("os.environ", environment, clear=False):
            client = OpenAICompatibleLLM()
        with patch(
            "urllib.request.urlopen",
            return_value=ByteResponse(b"x" * 1025),
        ):
            self.assertIsNone(client.complete("system", "user"))

    def test_provider_content_over_character_limit_falls_back_offline(self) -> None:
        environment = {
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "test-model",
            "LLM_MAX_CONTENT_CHARS": "256",
        }
        with patch.dict("os.environ", environment, clear=False):
            client = OpenAICompatibleLLM()
        body = json.dumps(
            {"choices": [{"message": {"content": "x" * 257}}]}
        ).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=ByteResponse(body)):
            self.assertIsNone(client.complete("system", "user"))

    def test_provider_content_limit_configuration_is_bounded(self) -> None:
        with patch.dict(
            "os.environ",
            {"LLM_MAX_CONTENT_CHARS": "255"},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "LLM_MAX_CONTENT_CHARS"):
                OpenAICompatibleLLM()


if __name__ == "__main__":
    unittest.main()
