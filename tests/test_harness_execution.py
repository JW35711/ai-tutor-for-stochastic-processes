from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.agent import StochasticTutorAgent
from src.harness.verification import verify_runtime
from src.memory import LearnerMemory


class _DisabledLLM:
    enabled = False

    def complete(self, *_args, **_kwargs):
        return None

    def last_request(self):
        return {"provider": None, "model": None, "status": "disabled", "retry_count": 0, "latency_ms": 0.0}


class HarnessExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = StochasticTutorAgent(memory=LearnerMemory(":memory:"))

    def test_concept_uses_graph_without_tool(self) -> None:
        response = self.agent.answer("What is Brownian motion?")
        harness = response["observability"]["harness"]
        self.assertEqual(harness["intent"], "concept")
        self.assertFalse(harness["tool_called"])
        self.assertIn("retrieve", harness["visited_nodes"])

    def test_simulation_keeps_python_tool_truth(self) -> None:
        response = self.agent.answer("Simulate Brownian motion with 20 steps.")
        harness = response["observability"]["harness"]
        self.assertEqual(harness["intent"], "simulation")
        self.assertTrue(harness["tool_called"])
        self.assertEqual(harness["tool"], "brownian_motion")

    def test_social_and_general_bypass_course_services(self) -> None:
        social = self.agent.answer("Thanks")
        general = self.agent.answer("What is Python?")
        self.assertEqual(social["intent"], "social_chat")
        self.assertEqual(general["intent"], "general_chat")
        self.assertEqual(social["sources"], [])
        self.assertEqual(general["sources"], [])
        self.assertFalse(social["observability"]["harness"]["tool_called"])

    def test_practice_handoff_stays_on_assessment_path(self) -> None:
        result = self.agent.handle_assessment({
            "question_id": "q04", "module_id": "module04",
            "concept_id": "m04-terminal-distribution", "answer_index": 0, "correct": True,
        }, "practice-user")
        self.assertIn("assessment", result["observability"]["harness"]["visited_nodes"])

    def test_disabled_llm_has_grounded_fallback_category(self) -> None:
        self.agent.llm = _DisabledLLM()
        response = self.agent.answer("What is Brownian motion?")
        self.assertFalse(response["llm_applied"])
        self.assertEqual(response["observability"]["harness"]["failure_category"], "LLM_DISABLED")
        self.assertNotIn("retrieved evidence", response["answer"].lower())

    def test_tool_validation_failure_is_classified(self) -> None:
        runtime = SimpleNamespace(intent="simulation", result={"error": "steps must be positive"}, tool_key="brownian_motion", verified=False, answerability_status="SUPPORTED", llm_metadata={}, llm_applied=False, answer="")
        result = verify_runtime(runtime)
        self.assertEqual(result.failure_category, "TOOL_VALIDATION_FAILED")

    def test_provider_and_output_failures_have_safe_categories(self) -> None:
        provider = SimpleNamespace(intent="concept", result={}, tool_key=None, verified=False, answerability_status="SUPPORTED", llm_metadata={"status": "failed"}, llm_applied=False, answer="fallback")
        output = SimpleNamespace(intent="concept", result={}, tool_key=None, verified=False, answerability_status="SUPPORTED", llm_metadata={"status": "success"}, llm_applied=False, answer="fallback")
        self.assertEqual(verify_runtime(provider).failure_category, "LLM_PROVIDER_FAILED")
        self.assertEqual(verify_runtime(output).failure_category, "LLM_OUTPUT_REJECTED")


if __name__ == "__main__":
    unittest.main()
