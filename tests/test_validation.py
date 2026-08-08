import unittest

from src.validation import MAX_QUESTION_CHARS, validate_question, validate_session_id


class SharedValidationTests(unittest.TestCase):
    def test_optional_and_required_session_contract(self) -> None:
        self.assertIsNone(validate_session_id(None))
        self.assertEqual(validate_session_id(" learner "), "learner")
        with self.assertRaisesRegex(ValueError, "required"):
            validate_session_id(None, required=True)

    def test_question_contract_normalizes_and_bounds_core_input(self) -> None:
        self.assertEqual(validate_question(" simulate "), "simulate")
        for invalid in (None, 123, "   ", "x" * (MAX_QUESTION_CHARS + 1)):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(ValueError):
                    validate_question(invalid)


if __name__ == "__main__":
    unittest.main()
