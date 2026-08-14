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

    def test_kp_policy_uses_assessed_concept_and_teaching_mode(self) -> None:
        agent = CurriculumAgent(curriculum_catalog())
        state = {"knowledge_points": [{"concept_id": "m05-markov-property", "status": "NEEDS_REVIEW", "attempt_count": 1, "mastery_score": 0.0, "recent_misconceptions": [{"summary": "memory confusion"}]}]}
        decision = agent.decide(current_module_id="module05", current_concept_id="m05-markov-property", profile=state)
        self.assertEqual(decision.decision_type, "REVIEW")
        self.assertEqual(decision.teaching_mode, "REVIEW")

    def test_unassessed_prerequisite_is_not_called_weak(self) -> None:
        agent = CurriculumAgent(curriculum_catalog())
        decision = agent.decide(current_module_id="module05", current_concept_id="m05-stationary-distribution", profile={"knowledge_points": []})
        self.assertNotEqual(decision.decision_type, "REVIEW_PREREQUISITE")

    def test_practice_updates_only_target_kp(self) -> None:
        memory = LearnerMemory(":memory:")
        agent = StochasticTutorAgent(memory=memory)
        result = agent.handle_assessment({"question_id": "kp-m04-brownian-increments", "module_id": "module04", "concept_id": "m04-brownian-increments", "answer_index": 0, "correct": True, "explanation": "ok", "event_type": "PRACTICE_ANSWER"}, "target")
        rows = {item["concept_id"]: item for item in result["memory"]["knowledge_points"]}
        self.assertIn("m04-brownian-increments", rows)
        self.assertEqual(rows["m04-brownian-increments"]["attempt_count"], 1)
        self.assertNotIn("m04-terminal-distribution", rows)
        self.assertEqual(result["grading_method"], "deterministic_keyword_or_relation_check")
        memory.close()

    def test_assessed_progression_moves_recommendation_to_next_kp(self) -> None:
        memory = LearnerMemory(":memory:")
        agent = StochasticTutorAgent(memory=memory)
        for index in range(4):
            result = agent.handle_assessment({"question_id": "q05", "module_id": "module05", "answer_index": 1, "correct": True, "explanation": "ok", "event_type": "PRACTICE_ANSWER", "attempt_number": index + 1}, "progression")
        self.assertEqual(result["assessment"]["mastery"]["status"], "MASTERED")
        self.assertEqual(result["recommendation"]["concept_id"], "m05-absorption-and-ruin")
        self.assertEqual(result["curriculum_decision"]["decision_type"], "ADVANCE")
        memory.close()


if __name__ == "__main__":
    unittest.main()
