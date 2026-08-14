"""Regression contracts for browser-confirmed student assessment fixes.

The full interaction walkthrough is run with Chromium/Playwright during QA;
these fast checks keep the high-risk DOM/API contracts in the normal pytest
suite as well.
"""

import re
import unittest
from pathlib import Path

from src.assessment import AssessmentEngine


ROOT = Path(__file__).resolve().parent.parent


class StudentUxRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.javascript = (ROOT / "web" / "app.js").read_text("utf-8")
        cls.styles = (ROOT / "web" / "styles.css").read_text("utf-8")
        cls.html = (ROOT / "web" / "index.html").read_text("utf-8")
        cls.engine = AssessmentEngine()

    def test_practice_is_a_free_text_projection_even_when_quiz_exists(self) -> None:
        practice = self.engine.practice_for_concept("m02-drift-variance")
        quiz = self.engine.question_for_concept("m02-drift-variance")
        self.assertEqual(practice["question_type"], "free_text")
        self.assertEqual(practice["choices"], [])
        self.assertNotEqual(practice["question"], quiz["question"])

    def test_practice_feedback_keeps_retry_and_reference_controls(self) -> None:
        for marker in (
            "practice-correct",
            "practice-incorrect",
            "practice-incomplete",
            'assessmentText("retry")',
            'assessmentText("showReference")',
            'assessmentText("empty")',
            "reference_shown",
        ):
            self.assertIn(marker, self.javascript)
        # Reference disclosure must not remove the action container: a later
        # retry needs a stable mount point for the next state.
        self.assertIn("Keep the action container in the DOM", self.javascript)

    def test_quiz_feedback_marks_selected_and_correct_options(self) -> None:
        self.assertIn('selected.classList.add("incorrect-answer")', self.javascript)
        self.assertIn('buttons[result.correct_index].classList.add("correct-answer")', self.javascript)
        self.assertIn(".quiz-choices button.incorrect-answer", self.styles)
        self.assertIn(".quiz-choices button.correct-answer", self.styles)

    def test_mobile_navigation_is_present_and_cache_busted(self) -> None:
        self.assertIn('data-view="overviewView"', self.html)
        self.assertEqual(len(re.findall(r'class="nav-item', self.html)), 5)
        self.assertIn("@media (max-width: 900px)", self.styles)
        self.assertIn('/app.js?v=student-ux', self.html)

    def test_experiment_metadata_is_cleaned_before_catalogue_render(self) -> None:
        self.assertIn("function cleanExperimentText", self.javascript)
        self.assertIn("cleanExperimentText(experiment.teaching_purpose", self.javascript)
        self.assertIn("cleanExperimentText(experiment.theory_connection", self.javascript)


if __name__ == "__main__":
    unittest.main()
