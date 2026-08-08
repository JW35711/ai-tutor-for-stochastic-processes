import unittest

from src.validation import validate_session_id


class SharedValidationTests(unittest.TestCase):
    def test_optional_and_required_session_contract(self) -> None:
        self.assertIsNone(validate_session_id(None))
        self.assertEqual(validate_session_id(" learner "), "learner")
        with self.assertRaisesRegex(ValueError, "required"):
            validate_session_id(None, required=True)


if __name__ == "__main__":
    unittest.main()
