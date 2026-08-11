import unittest
from unittest.mock import patch

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.workflow import AgentState


class AnswerabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)

    def tearDown(self) -> None:
        self.memory.close()

    def test_relevant_and_sufficient_poisson_evidence_is_supported(self) -> None:
        response = self.agent.answer("Why does a Poisson process have exponential waiting times?")
        self.assertEqual(response["answerability_status"], "SUPPORTED")
        self.assertFalse(response["tool_called"])

    def test_exact_hitting_time_without_conditions_is_partial(self) -> None:
        response = self.agent.answer("What is the exact hitting time result for a random walk?")
        self.assertEqual(response["answerability_status"], "PARTIAL")
        self.assertIn("initial state", response["missing_requirements"])
        self.assertNotIn("simulation", response["answer"].lower())

    def test_related_topic_does_not_support_external_policy_claim(self) -> None:
        response = self.agent.answer(
            "Does a Poisson process answer whether an external contractor can claim travel expenses?"
        )
        self.assertEqual(response["answerability_status"], "PARTIAL")
        self.assertIn("external-contractor eligibility", response["missing_requirements"])
        self.assertNotIn("exponential waiting", response["answer"].lower())

    def test_out_of_scope_question_does_not_retrieve(self) -> None:
        response = self.agent.answer("Can an external contractor claim travel expenses?")
        self.assertEqual(response["answerability_status"], "OUT_OF_SCOPE")
        self.assertEqual(response["sources"], [])

    def test_conflicting_sources_are_not_silently_selected(self) -> None:
        state = AgentState(question="Why is the exponential distribution memoryless?", session_id="test")
        state.intent = "concept"
        state.question_requirements = self.agent._analyze_question_requirements(state.question)
        state.sources = [
            {
                "source": "source-a",
                "content": "The exponential distribution is memoryless.",
                "claim_key": "memoryless",
                "claim_polarity": "positive",
            },
            {
                "source": "source-b",
                "content": "The exponential distribution is not memoryless.",
                "claim_key": "memoryless",
                "claim_polarity": "negative",
            },
        ]
        self.agent._update_answerability(state)
        self.assertEqual(state.answerability_status, "CONFLICT")
        self.assertEqual(set(state.conflicting_source_locators), {"source-a", "source-b"})

    def test_supplementary_retrieval_can_complete_evidence(self) -> None:
        first = [
            {
                "source": "first",
                "title": "Poisson process",
                "content": "A Poisson process counts arrivals with independent increments.",
                "module_id": "module01",
                "concept_id": "m01-poisson-process",
                "retrieval_mode": "hybrid",
            }
        ]
        second = [
            {
                "source": "second",
                "title": "Exponential waiting time",
                "content": "The waiting time to the next arrival is exponential.",
                "module_id": "module01",
                "concept_id": "m01-poisson-process",
                "retrieval_mode": "hybrid",
            }
        ]
        with patch.object(self.agent.knowledge, "retrieve", side_effect=[first, second]):
            response = self.agent.answer("Why does a Poisson process have exponential waiting times?")
        self.assertEqual(response["answerability_status"], "SUPPORTED")
        self.assertEqual(response["retrieval_rounds"], 2)
        self.assertIn("second", response["supporting_source_locators"])


if __name__ == "__main__":
    unittest.main()
