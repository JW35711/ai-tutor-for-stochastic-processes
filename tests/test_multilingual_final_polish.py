import re
import unittest
from pathlib import Path

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.messages import MESSAGES
from src.recommendation import recommend_next


class OfflineLLM:
    enabled = False

    def complete(self, *args, **kwargs):
        return None


class MultilingualFinalPolishTests(unittest.TestCase):
    def setUp(self):
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)
        self.agent.llm = OfflineLLM()

    def tearDown(self):
        self.memory.close()

    def test_query_language_overrides_ui_language(self):
        cases = (
            ("Explain the Markov property", "sv", "en", "module05"),
            ("Vad är Markovegenskapen?", "en", "sv", "module05"),
            ("什么是泊松过程？", "zh", "zh", "module01"),
        )
        for question, ui, response_language, module_id in cases:
            with self.subTest(question=question):
                result = self.agent.answer(question, ui_language=ui)
                self.assertEqual(result["detected_query_language"], response_language)
                self.assertEqual(result["response_language"], response_language)
                self.assertEqual(result["module_id"], module_id)

    def test_swedish_experiment_follow_up_keeps_context_and_parameter(self):
        session = "sv-polish"
        first = self.agent.answer("Varför är väntetiden exponentialfördelad?", session_id=session, ui_language="sv")
        shown = self.agent.answer("Visa mig.", session_id=session, ui_language="sv")
        updated = self.agent.answer("Sätt lambda till 4.", session_id=session, ui_language="sv")
        changed = self.agent.answer("Vad ändrades?", session_id=session, ui_language="sv")
        self.assertEqual(first["response_language"], "sv")
        self.assertEqual(shown["response_language"], "sv")
        self.assertTrue(shown["tool_called"])
        self.assertEqual(updated["active_experiment_id"], shown["active_experiment_id"])
        self.assertEqual(updated["parameters"]["rate"], 4.0)
        self.assertEqual(changed["active_experiment_id"], updated["active_experiment_id"])
        self.assertEqual(changed["response_language"], "sv")
        self.assertNotRegex(changed["answer"], r"\b(?:The|empirical|versus|absolute error)\b")

    def test_localized_recommendations_cover_all_languages(self):
        for language in ("en", "zh", "sv"):
            recommendation = recommend_next({"modules": []}, language)
            self.assertTrue(recommendation["suggested_question"])
        sv = recommend_next({"modules": []}, "sv")
        self.assertNotIn("What is", sv["suggested_question"])

    def test_system_message_catalog_has_all_locales(self):
        for key, translations in MESSAGES.items():
            self.assertEqual(set(translations), {"en", "zh", "sv"}, key)

    def test_frontend_actions_are_localized_and_keep_stable_ids(self):
        javascript = (Path(__file__).parents[1] / "web" / "app.js").read_text(encoding="utf-8")
        for phrase in ("Vad är ${title}?", "Ge mig en övning om", "Visa mig en simulering som hjälper mig att förstå", "Testa min förståelse av"):
            self.assertIn(phrase, javascript)
        self.assertIn("pendingTutorAction = { action_type: \"learn\", concept_id: chosen.id }", javascript)
        self.assertIn("experiment_id: experiment?.experiment_id", javascript)

    def test_math_renderer_contract_covers_four_delimiter_families(self):
        javascript = (Path(__file__).parents[1] / "web" / "app.js").read_text(encoding="utf-8")
        for pattern in (r"\$\$([\s\S]*?)\$\$", r"\\\[([\s\S]*?)\\\]", r"\\\(([\s\S]*?)\\\)", r"\$([^$\n]+)\$"):
            self.assertIn(pattern, javascript)
        self.assertIn("window.katex.render", javascript)


if __name__ == "__main__":
    unittest.main()
