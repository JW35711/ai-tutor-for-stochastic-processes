import unittest

from src.agent import StochasticTutorAgent
from src.agents import AssessmentAgent, CurriculumAgent, TutorAgent, TutorContext
from src.curriculum import curriculum_catalog
from src.memory import LearnerMemory


class OfflineLLM:
    enabled = False

    def complete(self, system: str, user: str) -> str | None:
        return None


class MultiAgentBoundaryTests(unittest.TestCase):
    def test_curriculum_agent_uses_prerequisites_and_never_invents_ids(self) -> None:
        agent = CurriculumAgent(curriculum_catalog())
        decision = agent.decide(
            current_module_id="module05",
            current_concept_id="m05-stationary-distribution",
            profile={"modules": [{"module_id": "module05", "mastery": 0.1}]},
            recent_mistakes=[{"concept_id": "m05-stationary-distribution"}],
            learning_mode="review",
        )
        self.assertEqual(decision.target_concept, "m05-transition-matrix")
        self.assertIn(decision.target_concept, {item["id"] for item in agent.concepts.values()})

    def test_mastery_can_move_to_the_next_curriculum_point(self) -> None:
        agent = CurriculumAgent(curriculum_catalog())
        decision = agent.decide(
            current_module_id="module05",
            current_concept_id="m05-stationary-distribution",
            profile={"modules": [{"module_id": "module05", "mastery": 0.85}]},
        )
        self.assertEqual(decision.recommended_action, "continue_current_concept")
        self.assertEqual(decision.next_concept, "m05-absorption-and-ruin")

    def test_assessment_agent_evaluates_without_teaching(self) -> None:
        agent = AssessmentAgent()
        result = agent.evaluate(
            {
                "question_id": "q05",
                "module_id": "module05",
                "correct": False,
                "hints_used": 1,
            }
        )
        self.assertEqual(result.concept_id, "m05-stationary-distribution")
        self.assertTrue(result.needs_review)
        self.assertEqual(result.recommended_difficulty, "guided")
        self.assertNotIn("answer", result.to_dict())

    def test_tutor_obeys_answerability_before_synthesis(self) -> None:
        agent = TutorAgent()
        calls = {"synthesis": 0}

        def synthesize() -> str:
            calls["synthesis"] += 1
            return "unsupported answer"

        answer = agent.answer_concept(
            TutorContext(question="q", answerability_status="PARTIAL", sources=({"source": "a"},)),
            synthesise=synthesize,
            partial=lambda: "clarify",
            conflict=lambda: "conflict",
            none=lambda: "none",
            fallback=lambda: "fallback",
        )
        self.assertEqual(answer, "clarify")
        self.assertEqual(calls["synthesis"], 0)

    def test_normal_concept_skips_curriculum_and_assessment_agents(self) -> None:
        memory = LearnerMemory(":memory:")
        agent = StochasticTutorAgent(memory=memory)
        agent.llm = OfflineLLM()  # type: ignore[assignment]
        response = agent.answer("What is Brownian motion?", session_id="concept")
        self.assertEqual(response["observability"]["agents_invoked"], ["tutor"])
        self.assertEqual(response["observability"]["llm_call_count"], 0)
        self.assertFalse(response["tool_called"])
        memory.close()

    def test_quiz_handoff_updates_memory_curriculum_then_tutor(self) -> None:
        memory = LearnerMemory(":memory:")
        agent = StochasticTutorAgent(memory=memory)
        result = agent.handle_assessment(
            {
                "question_id": "q05",
                "module_id": "module05",
                "answer_index": 0,
                "correct": False,
                "correct_index": 1,
                "explanation": "Use πP=π.",
                "bank_sha256": "test",
            },
            "quiz-session",
        )
        self.assertEqual(
            result["graph"]["visited_nodes"],
            ["route", "assessment", "curriculum", "respond"],
        )
        self.assertEqual(
            result["observability"]["agents_invoked"],
            ["assessment", "curriculum", "tutor"],
        )
        self.assertTrue(result["assessment"]["needs_review"])
        self.assertEqual(memory.profile("quiz-session")["quiz_attempts"], 1)
        self.assertIn("review", result["answer"].lower())
        memory.close()


if __name__ == "__main__":
    unittest.main()
