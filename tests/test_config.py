import os
import unittest
from unittest.mock import patch

from src.config import env_float, env_int


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


if __name__ == "__main__":
    unittest.main()
