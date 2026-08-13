import re
import unittest

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


class OfflineLLM:
    enabled = False

    def complete(self, system: str, user: str) -> str | None:
        return None


class V1StabilizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)
        self.agent.llm = OfflineLLM()  # type: ignore[assignment]

    def tearDown(self) -> None:
        self.memory.close()

    def ask(self, question: str) -> dict:
        response = self.agent.answer(question)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", response["answer"]))
        return response

    def test_module_navigation_does_not_retrieve_or_run_a_tool(self) -> None:
        response = self.ask("What is Module 02?")
        self.assertEqual(response["intent"], "course_navigation")
        self.assertEqual(response["module_id"], "module02")
        self.assertFalse(response["tool_called"])
        self.assertEqual(response["sources"], [])

    def test_brownian_concept_is_grounded_without_a_tool(self) -> None:
        response = self.ask("What is Brownian motion?")
        self.assertEqual(response["intent"], "concept")
        self.assertEqual(response["module_id"], "module04")
        self.assertFalse(response["tool_called"])
        self.assertTrue(any(source["module_id"] == "module04" for source in response["sources"]))

    def test_curriculum_learn_prompt_routes_survival_hazard_to_module07(self) -> None:
        response = self.ask("Explain Survival and hazard functions using the course material.")
        self.assertEqual(response["intent"], "concept")
        self.assertEqual(response["module_id"], "module07")
        self.assertEqual(response["concept_id"], "m07-survival-and-hazard")
        self.assertFalse(response["tool_called"])
        self.assertNotEqual(response["answerability_status"], "OUT_OF_SCOPE")
        self.assertTrue(response["sources"])

    def test_stationarity_does_not_pick_survival_hazard(self) -> None:
        response = self.ask("Explain strict stationarity and weak stationarity.")
        self.assertEqual(response["intent"], "concept")
        self.assertIsNone(response["concept_id"])
        self.assertNotEqual(response["module_id"], "module07")
        self.assertFalse(response["tool_called"])

    def test_comparison_covers_both_walk_concepts(self) -> None:
        response = self.ask("Compare random walk and self-avoiding walk.")
        self.assertEqual(response["intent"], "concept")
        self.assertFalse(response["tool_called"])
        self.assertTrue({"module02", "module09"}.issubset(set(response["related_module_ids"])))
        self.assertTrue({"m02-random-walk-increments", "m09-self-avoidance"}.issubset(set(response["related_concept_ids"])))

    def test_explicit_brownian_simulation_uses_python_tool(self) -> None:
        response = self.ask("Simulate Brownian motion with 100 steps.")
        self.assertEqual(response["intent"], "simulation")
        self.assertEqual(response["module_id"], "module04")
        self.assertTrue(response["tool_called"])
        self.assertEqual(response["tool"], "simulate_brownian_motion")

    def test_all_regression_answers_are_english(self) -> None:
        questions = (
            "What is Module 02?",
            "What is Brownian motion?",
            "Explain strict stationarity and weak stationarity.",
            "Compare random walk and self-avoiding walk.",
            "Simulate Brownian motion with 100 steps.",
        )
        for question in questions:
            with self.subTest(question=question):
                response = self.ask(question)
                self.assertNotRegex(response["answer"], r"[\u4e00-\u9fff]")

    def test_llm_disabled_fallback_is_short_and_does_not_dump_pdf(self) -> None:
        response = self.ask("What is Brownian motion?")
        self.assertFalse(response["llm_enabled"])
        self.assertFalse(response["llm_applied"])
        self.assertLessEqual(len(response["answer"].split()), 180)
        self.assertNotIn("retrieved", response["answer"].lower())
        self.assertNotIn("lectnotes_technmath.pdf", response["answer"])

    def test_debug_contract_fields_are_present_in_backend_response(self) -> None:
        response = self.ask("What is Brownian motion?")
        for field in ("llm_enabled", "llm_applied", "workflow", "trace", "sources"):
            self.assertIn(field, response)

    def test_poisson_definition_and_explanation_use_different_sub_intents(self) -> None:
        definition = self.ask("Poisson process")
        explanation = self.ask("Why does a Poisson process have exponential waiting times?")
        self.assertEqual(definition["concept_sub_intent"], "definition")
        self.assertEqual(explanation["concept_sub_intent"], "why/explanation")
        self.assertFalse(definition["tool_called"])
        self.assertFalse(explanation["tool_called"])
        self.assertNotEqual(definition["answer"], explanation["answer"])
        self.assertIn("exponential waiting", explanation["answer"].lower())
        self.assertIn("n(t)", explanation["answer"].lower())
        self.assertIn("p(t", explanation["answer"].lower())

    def test_memoryless_question_is_explanation_not_scope_chat(self) -> None:
        response = self.ask("Why is the exponential distribution memoryless?")
        self.assertEqual(response["intent"], "concept")
        self.assertEqual(response["concept_sub_intent"], "why/explanation")
        self.assertFalse(response["tool_called"])
        self.assertIn("memoryless", response["answer"].lower())

    def test_stationary_distribution_hint_stays_a_hint(self) -> None:
        response = self.ask("Give me a hint for finding a stationary distribution.")
        self.assertEqual(response["intent"], "concept")
        self.assertEqual(response["concept_sub_intent"], "hint")
        self.assertFalse(response["tool_called"])
        self.assertRegex(response["answer"].lower(), r"balance|normalization")

    def test_query_language_is_independent_from_ui_language(self) -> None:
        response = self.agent.answer("为什么泊松过程的等待时间服从指数分布？", ui_language="en")
        self.assertEqual(response["detected_query_language"], "zh")
        self.assertEqual(response["response_language"], "zh")
        self.assertEqual(response["module_id"], "module01")
        self.assertEqual(response["concept_id"], "m01-poisson-process")
        self.assertTrue(response["translation_applied"])
        self.assertIn("泊松过程", response["answer"])
        self.assertTrue(any("lectnotes" in source["source"] or "ipynb" in source["source"] for source in response["sources"]))

    def test_swedish_query_returns_swedish_with_stationary_formula(self) -> None:
        response = self.agent.answer("Vad betyder pi P = pi för en Markovkedja?", ui_language="en")
        self.assertEqual(response["detected_query_language"], "sv")
        self.assertEqual(response["response_language"], "sv")
        self.assertEqual(response["module_id"], "module05")
        self.assertEqual(response["concept_id"], "m05-stationary-distribution")
        self.assertIn("stationär", response["answer"])
        self.assertIn("\\pi P=\\pi", response["answer"])


if __name__ == "__main__":
    unittest.main()
