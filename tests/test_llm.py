import json
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from threading import Event
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


class FakeClock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


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
            "先保留经过验证的结果：\n"
            f"{self.draft}\n"
            "接下来可以讨论为什么经验值与理论值不同。"
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

    def test_rejects_semantic_reversal_even_when_numbers_survive(self) -> None:
        verified = (
            "交通强度 ρ=1.2≥1，不存在稳定的几何平稳分布；"
            "经验平均客户数为 4.0。"
        )
        source = "notebooks/07_Markov_Chain_Part3.ipynb#cell-56"
        candidate = (
            "交通强度 ρ=1.2≥1，队列稳定并且存在几何平稳分布；"
            f"经验平均客户数为 4.0。{source}"
        )
        self.assertFalse(
            preserves_verified_facts(
                candidate,
                verified,
                [{"source": source}],
            )
        )

    def test_number_must_be_a_complete_token(self) -> None:
        self.assertFalse(
            preserves_verified_facts(
                "经验均值 11.25。source",
                "经验均值 1.25。",
                [{"source": "source"}],
            )
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

    def test_provider_failure_circuit_skips_then_recovers(self) -> None:
        environment = {"LLM_API_KEY": "test-key", "LLM_MODEL": "test-model"}
        clock = FakeClock()
        with patch.dict("os.environ", environment, clear=False):
            client = OpenAICompatibleLLM(failure_cooldown=60, clock=clock)
        recovered_body = json.dumps(
            {"choices": [{"message": {"content": "recovered"}}]}
        ).encode("utf-8")
        with patch(
            "urllib.request.urlopen",
            side_effect=[
                urllib.error.URLError("provider unavailable"),
                ByteResponse(recovered_body),
            ],
        ) as call:
            self.assertIsNone(client.complete("system", "first"))
            self.assertIsNone(client.complete("system", "skipped"))
            self.assertEqual(call.call_count, 1)
            self.assertEqual(client.stats()["state"], "open")
            self.assertEqual(client.stats()["skips"], 1)
            clock.now += 61
            self.assertEqual(client.complete("system", "probe"), "recovered")
            self.assertEqual(call.call_count, 2)
        stats = client.stats()
        self.assertEqual(stats["state"], "closed")
        self.assertEqual(stats["attempts"], 2)
        self.assertEqual(stats["successes"], 1)
        self.assertEqual(stats["failures"], 1)
        self.assertIsNone(stats["last_failure"])

    def test_disabled_provider_reports_disabled_without_attempt(self) -> None:
        with patch.dict(
            "os.environ",
            {"LLM_API_KEY": "", "LLM_MODEL": ""},
            clear=False,
        ):
            client = OpenAICompatibleLLM()
        self.assertIsNone(client.complete("system", "user"))
        self.assertEqual(client.stats()["state"], "disabled")
        self.assertEqual(client.stats()["attempts"], 0)

    def test_http_failure_reports_status_without_provider_body(self) -> None:
        environment = {"LLM_API_KEY": "test-key", "LLM_MODEL": "test-model"}
        with patch.dict("os.environ", environment, clear=False):
            client = OpenAICompatibleLLM()
        error = urllib.error.HTTPError(
            "https://api.openai.com/v1/chat/completions",
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=error):
            self.assertIsNone(client.complete("system", "user"))
        self.assertEqual(client.stats()["last_failure"], "HTTP_401")

    def test_concurrent_provider_calls_do_not_amplify_work(self) -> None:
        environment = {"LLM_API_KEY": "test-key", "LLM_MODEL": "test-model"}
        with patch.dict("os.environ", environment, clear=False):
            client = OpenAICompatibleLLM()
        entered = Event()
        release = Event()
        body = json.dumps(
            {"choices": [{"message": {"content": "verified rewrite"}}]}
        ).encode("utf-8")

        def delayed_response(*_args, **_kwargs):
            entered.set()
            self.assertTrue(release.wait(timeout=2))
            return ByteResponse(body)

        with patch("urllib.request.urlopen", side_effect=delayed_response):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(client.complete, "system", "first")
                self.assertTrue(entered.wait(timeout=2))
                self.assertIsNone(client.complete("system", "second"))
                release.set()
                self.assertEqual(first.result(timeout=2), "verified rewrite")
        stats = client.stats()
        self.assertEqual(stats["attempts"], 1)
        self.assertEqual(stats["successes"], 1)
        self.assertEqual(stats["skips"], 1)


if __name__ == "__main__":
    unittest.main()
