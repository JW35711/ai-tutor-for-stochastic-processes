import os
import unittest
from unittest.mock import patch

from src.config import RuntimeConfig, env_float, env_int


class ConfigurationTests(unittest.TestCase):
    def test_integer_uses_default_and_accepts_boundary(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env_int("EXAMPLE_INT", 7, minimum=1, maximum=10), 7)
        with patch.dict(os.environ, {"EXAMPLE_INT": "10"}):
            self.assertEqual(env_int("EXAMPLE_INT", 7, minimum=1, maximum=10), 10)

    def test_integer_names_invalid_variable(self) -> None:
        for value in ("nope", "0", "11"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"EXAMPLE_INT": value}
            ):
                with self.assertRaisesRegex(ValueError, "EXAMPLE_INT"):
                    env_int("EXAMPLE_INT", 7, minimum=1, maximum=10)

    def test_float_rejects_non_finite_and_out_of_bounds(self) -> None:
        for value in ("nan", "inf", "-1", "11", "not-a-number"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"EXAMPLE_FLOAT": value}
            ):
                with self.assertRaisesRegex(ValueError, "EXAMPLE_FLOAT"):
                    env_float("EXAMPLE_FLOAT", 2.5, minimum=0, maximum=10)

    def test_runtime_config_supports_primary_timeout_and_retrieval_limits(self) -> None:
        environment = {
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "LLM_BASE_URL": "http://localhost:9000/v1",
            "LLM_TIMEOUT": "4.5",
            "LLM_MAX_RETRIES": "1",
            "RETRIEVAL_TOP_K": "5",
            "ANSWER_MAX_WORDS": "200",
            "EVIDENCE_MAX_CHARS": "1200",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = RuntimeConfig.from_env(load_local=False)
        self.assertEqual(config.llm_timeout, 4.5)
        self.assertEqual(config.llm_max_retries, 1)
        self.assertEqual(config.retrieval_top_k, 5)
        self.assertEqual(config.evidence_max_chars, 1200)

    def test_runtime_config_rejects_bad_endpoint_and_partial_credentials(self) -> None:
        with patch.dict(os.environ, {"LLM_BASE_URL": "not a url"}, clear=True):
            with self.assertRaisesRegex(ValueError, "LLM_BASE_URL"):
                RuntimeConfig.from_env(load_local=False)
        with patch.dict(os.environ, {"LLM_API_KEY": "secret"}, clear=True):
            with self.assertRaisesRegex(ValueError, "LLM_MODEL"):
                RuntimeConfig.from_env(load_local=False)


if __name__ == "__main__":
    unittest.main()
