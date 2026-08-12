import unittest

from langgraph.graph.state import CompiledStateGraph

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory


class LangGraphWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)

    def tearDown(self) -> None:
        self.memory.close()

    def test_agent_uses_official_compiled_state_graph(self) -> None:
        self.assertIsInstance(self.agent.workflow, CompiledStateGraph)
        nodes = set(self.agent.workflow.get_graph().nodes)
        self.assertTrue(
            {
                "route",
                "navigation",
                "retrieve",
                "evidence",
                "supplement",
                "plan",
                "tool",
                "diagnose",
                "memory",
                "respond",
                "out_of_scope",
            }.issubset(nodes)
        )

    def test_conditional_paths_keep_legacy_api_trace(self) -> None:
        navigation = self.agent.answer("What is Module 02?")
        self.assertEqual(navigation["workflow"]["nodes"], ["classify", "respond"])
        self.assertEqual(navigation["graph"]["route_taken"], "course_navigation")

        concept = self.agent.answer("What is Brownian motion?")
        self.assertEqual(concept["workflow"]["nodes"], ["classify", "retrieve", "respond"])
        self.assertFalse(concept["tool_called"])
        self.assertIn("evidence", concept["graph"]["visited_nodes"])

        simulation = self.agent.answer("Simulate Brownian motion with 20 steps.")
        self.assertTrue(simulation["tool_called"])
        self.assertEqual(simulation["workflow"]["nodes"][2:6], ["plan", "tool", "diagnose", "memory"])
        self.assertEqual(simulation["graph"]["route_taken"], "simulation")

    def test_supplementary_retrieval_is_bounded(self) -> None:
        calls = 0
        original = self.agent._retrieve_for_state

        def incomplete(state, query):
            nonlocal calls
            calls += 1
            return original(state, query)

        self.agent._retrieve_for_state = incomplete  # type: ignore[method-assign]
        self.agent.answer("Why does a Poisson process have exponential waiting times?")
        self.assertLessEqual(calls, 3)


if __name__ == "__main__":
    unittest.main()
