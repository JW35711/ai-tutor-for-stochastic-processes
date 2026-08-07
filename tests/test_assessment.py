import tempfile
import unittest
from pathlib import Path

from src.assessment import AssessmentEngine
from src.memory import LearnerMemory


class AssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AssessmentEngine()

    def test_all_eleven_modules_have_a_question(self) -> None:
        self.assertEqual(set(self.engine.by_module), {f"module{i:02d}" for i in range(11)})

    def test_public_question_does_not_leak_answer(self) -> None:
        question = self.engine.question("module04")
        self.assertNotIn("correct_index", question)
        self.assertNotIn("explanation", question)

    def test_grade_returns_explanation(self) -> None:
        result = self.engine.grade("q04", 2)
        self.assertTrue(result["correct"])
        self.assertIn("方差为 T", result["explanation"])

    def test_quiz_changes_persistent_mastery_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = LearnerMemory(Path(directory) / "memory.sqlite3")
            memory.record_assessment(
                session_id="quiz-user",
                question_id="q04",
                module_id="module04",
                answer_index=2,
                correct=True,
            )
            profile = memory.profile("quiz-user")
            self.assertEqual(profile["quiz_correct"], 1)
            self.assertEqual(profile["modules"][0]["quiz_attempts"], 1)
            self.assertGreater(profile["modules"][0]["mastery"], 0.1)
            memory.close()


if __name__ == "__main__":
    unittest.main()
