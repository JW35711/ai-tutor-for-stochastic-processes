import unittest

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.experiments import ExperimentRegistry
from src.curriculum import curriculum_catalog


class OfflineLLM:
    enabled = False

    def complete(self, system: str, user: str) -> str | None:
        return None


class ExperimentIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)
        self.agent.llm = OfflineLLM()  # type: ignore[assignment]

    def tearDown(self) -> None:
        self.memory.close()

    def ask(self, question: str, session: str = "routing") -> dict:
        return self.agent.answer(question, session_id=session)

    def test_registry_discovery_is_catalogue_backed(self) -> None:
        registry = ExperimentRegistry()
        match = registry.find_experiments(query="show a Poisson sample path", module_id="module01", limit=1)
        self.assertEqual(match[0]["experiment_id"], "module01-exp-09")
        self.assertEqual(match[0]["simulation_engine"], "poisson")

    def test_theory_recommends_without_running(self) -> None:
        response = self.ask("Why does lambda affect waiting time?")
        self.assertFalse(response["tool_called"])
        self.assertTrue(response["experiment_recommendations"])

    def test_show_me_runs_recommended_experiment(self) -> None:
        self.ask("Why does lambda affect waiting time?", "handoff")
        response = self.ask("Show me.", "handoff")
        self.assertTrue(response["tool_called"])
        self.assertEqual(response["experiment"]["concept_id"], "m01-poisson-process")

    def test_parameter_follow_up_reruns_same_experiment(self) -> None:
        first = self.ask("Show me a Poisson sample path.", "params")
        second = self.ask("Set lambda to 4.", "params")
        self.assertEqual(first["selected_experiment_id"], second["selected_experiment_id"])
        self.assertEqual(second["parameters"]["rate"], 4.0)
        self.assertEqual(second["context"]["parameters_inherited"], ["horizon", "paths", "seed"])

    def test_natural_language_parameter_comparison_reruns_active_experiment(self) -> None:
        first = self.ask("Simulate Brownian motion with 100 steps.", "natural-steps")
        second = self.ask("What changes if I use 500 steps?", "natural-steps")
        self.assertEqual(second["module_id"], "module04")
        self.assertEqual(second["tool"], "simulate_brownian_motion")
        self.assertTrue(second["tool_called"])
        self.assertEqual(second["parameters"]["steps"], 500)
        self.assertEqual(second["parameters"]["paths"], first["parameters"]["paths"])
        self.assertTrue(second["context"]["module_inherited"])

    def test_result_question_uses_latest_verified_summary(self) -> None:
        self.ask("Show me a Poisson sample path.", "result")
        response = self.ask("What changed?", "result")
        self.assertFalse(response["tool_called"])
        self.assertIn("latest module01-exp-09 run", response["answer"])

    def test_page_rank_and_thinning_select_specific_experiments(self) -> None:
        page_rank = self.ask("Show me PageRank.", "special")
        thinning = self.ask("Show the thinning process.", "special2")
        self.assertEqual(page_rank["experiment"]["experiment_id"], "module05-exp-08")
        self.assertEqual(thinning["experiment"]["experiment_id"], "module08-exp-03")

    def test_unsupported_custom_parameter_is_not_passed_to_tool(self) -> None:
        response = self.ask("Try arbitrary Python code here.", "unsafe")
        self.assertFalse(response["tool_called"])
        self.assertIn("not supported", response["answer"])

    def test_brownian_uses_brownian_engine_and_step_parameter(self) -> None:
        response = self.ask("Simulate Brownian motion with 10 steps.")
        self.assertTrue(response["tool_called"])
        self.assertEqual(response["tool"], "simulate_brownian_motion")
        self.assertEqual(response["parameters"]["steps"], 10)

    def test_one_registry_backed_route_per_module(self) -> None:
        for module in curriculum_catalog()["modules"]:
            point = next(
                point for point in module["knowledge_points"]
                if point.get("simulation_prompt")
            )
            with self.subTest(module=module["module_id"]):
                response = self.ask(point["simulation_prompt"], f"module-route-{module['module_id']}")
                self.assertTrue(response["tool_called"])
                self.assertEqual(response["module_id"], module["module_id"])
                self.assertTrue(response.get("selected_experiment_id"))


if __name__ == "__main__":
    unittest.main()
