import unittest

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


class DisabledLLM:
    enabled = False

    def complete(self, system: str, user: str) -> str | None:
        return None


class ConversationalRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)
        # Keep these tests deterministic and independent of provider
        # credentials.  Production still uses the configured provider.
        self.agent.llm = DisabledLLM()

    def tearDown(self) -> None:
        self.memory.close()

    def test_social_acknowledgements_bypass_course_pipeline(self) -> None:
        def no_retrieval(*args, **kwargs):
            raise AssertionError("social chat must not call retrieval")

        self.agent.knowledge.retrieve = no_retrieval  # type: ignore[method-assign]
        for question in ("OK you are smart", "Thanks", "Got it"):
            with self.subTest(question=question):
                response = self.agent.answer(question, ui_language="en")
                self.assertEqual(response["intent"], "social_chat")
                self.assertFalse(response["tool_called"])
                self.assertEqual(response["sources"], [])
                self.assertNotIn("outside the scope", response["answer"].lower())
                self.assertEqual(response["memory"]["turns"], 0)

    def test_general_chat_bypasses_retrieval(self) -> None:
        def no_retrieval(*args, **kwargs):
            raise AssertionError("general chat must not call retrieval")

        self.agent.knowledge.retrieve = no_retrieval  # type: ignore[method-assign]
        response = self.agent.answer("What is Python?")
        self.assertEqual(response["intent"], "general_chat")
        self.assertEqual(response["sources"], [])

    def test_contextual_followups_keep_the_previous_course_concept(self) -> None:
        first = self.agent.answer("What is Brownian motion?", session_id="context")
        confirmation = self.agent.answer("Are you sure?", session_id="context")
        simpler = self.agent.answer("Explain that more simply", session_id="context")
        self.assertEqual(first["intent"], "concept")
        self.assertEqual(confirmation["intent"], "concept")
        self.assertEqual(simpler["intent"], "concept")
        self.assertEqual(confirmation["module_id"], first["module_id"])
        self.assertEqual(simpler["module_id"], first["module_id"])
        self.assertEqual(confirmation["concept_id"], first["concept_id"])
        self.assertFalse(confirmation["tool_called"])
        self.assertFalse(simpler["tool_called"])
        self.assertNotIn("outside the scope", simpler["answer"].lower())

    def test_general_chat_has_no_fake_course_evidence(self) -> None:
        response = self.agent.answer("What is Python?")
        self.assertEqual(response["intent"], "general_chat")
        self.assertEqual(response["module_id"], "general")
        self.assertEqual(response["sources"], [])
        self.assertFalse(response["tool_called"])
        self.assertIn("Python", response["answer"])
        self.assertEqual(response["memory"]["turns"], 0)

        capabilities = self.agent.answer("What can you do?")
        self.assertEqual(capabilities["intent"], "general_chat")
        self.assertEqual(capabilities["sources"], [])
        self.assertFalse(capabilities["tool_called"])

    def test_social_response_language_follows_the_query(self) -> None:
        cases = (("谢谢", "zh", "不客气"), ("Tack", "sv", "Varsågod"), ("Thanks", "en", "welcome"))
        for question, language, expected in cases:
            with self.subTest(question=question):
                response = self.agent.answer(question, ui_language="en")
                self.assertEqual(response["intent"], "social_chat")
                self.assertEqual(response["response_language"], language)
                self.assertIn(expected.lower(), response["answer"].lower())

    def test_out_of_scope_safety_refusal_is_preserved(self) -> None:
        response = self.agent.answer("Can an external contractor claim travel expenses?")
        self.assertEqual(response["intent"], "unsupported")
        self.assertEqual(response["answerability_status"], "OUT_OF_SCOPE")
        self.assertEqual(response["sources"], [])
        self.assertIn("outside the scope", response["answer"].lower())


if __name__ == "__main__":
    unittest.main()
