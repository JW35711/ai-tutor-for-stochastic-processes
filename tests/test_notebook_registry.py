import json
import unittest
from pathlib import Path

from scripts.audit_notebook_visualizations import (
    CURRICULUM_PATH,
    NOTEBOOK_DIR,
    REGISTRY_PATH,
    audit,
    build_registry,
    detect_notebook_targets,
    SUPPORTED_RENDERERS,
)
from src.processes.counting import simulate_bernoulli_process, simulate_nhpp_thinning
from src.processes.exploratory import simulate_coalescing_particles, simulate_self_avoiding_walk
from src.processes.simulations import analyze_markov_chain, simulate_brownian_motion, simulate_poisson_process


ROOT = Path(__file__).resolve().parent.parent


class NotebookRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text("utf-8"))
        cls.curriculum = json.loads(CURRICULUM_PATH.read_text("utf-8"))
        cls.targets = detect_notebook_targets(NOTEBOOK_DIR)

    def test_registry_ids_are_unique(self) -> None:
        experiment_ids = [item["experiment_id"] for item in self.registry["experiments"]]
        visualization_ids = [item["visualization_id"] for item in self.registry["visualizations"]]
        self.assertEqual(len(experiment_ids), len(set(experiment_ids)))
        self.assertEqual(len(visualization_ids), len(set(visualization_ids)))

    def test_modules_concepts_notebooks_and_cells_are_valid(self) -> None:
        modules = {item["module_id"] for item in self.curriculum["modules"]}
        concepts = {point["id"] for module in self.curriculum["modules"] for point in module["knowledge_points"]}
        for item in self.registry["experiments"]:
            self.assertIn(item["module_id"], modules)
            if item.get("concept_id"):
                self.assertIn(item["concept_id"], concepts)
            path = ROOT / item["source_notebook"]
            self.assertTrue(path.exists())
            notebook = json.loads(path.read_text("utf-8"))
            for index in item["source_cell_indices"]:
                self.assertGreaterEqual(index, 0)
                self.assertLess(index, len(notebook["cells"]))

    def test_declared_tools_are_reusable_catalogue_tools(self) -> None:
        allowed = {"monte_carlo", "bernoulli", "poisson", "random_walk", "continuous_random_walk", "brownian_motion", "markov_chain", "ctmc", "birth_death", "reliability", "buffer", "mm1_queue", "nhpp", "self_avoiding_walk", "coalescing_particles"}
        for item in self.registry["experiments"]:
            if item.get("simulation_engine"):
                self.assertIn(item["simulation_engine"], allowed)

    def test_visualization_references_and_detection_are_closed(self) -> None:
        experiment_ids = {item["experiment_id"] for item in self.registry["experiments"]}
        visualization_ids = {item["visualization_id"] for item in self.registry["visualizations"]}
        self.assertTrue(all(item["experiment_id"] in experiment_ids for item in self.registry["visualizations"]))
        self.assertTrue(all(item["visualization_id"] in visualization_ids for item in self.targets))
        report = audit(self.registry, NOTEBOOK_DIR)
        self.assertEqual(report["unregistered_ids"], [])
        self.assertEqual(report["orphan_registered_ids"], [])
        self.assertEqual(report["coverage_percent"], 100.0)

    def test_registry_generation_is_deterministic(self) -> None:
        first = build_registry(detect_notebook_targets(NOTEBOOK_DIR))
        second = build_registry(detect_notebook_targets(NOTEBOOK_DIR))
        self.assertEqual(first, second)

    def test_former_partial_targets_have_structured_payloads(self) -> None:
        payloads = {
            "module01": simulate_bernoulli_process(slots=20, paths=20),
            "module01_poisson": simulate_poisson_process(rate=1.5, horizon=4, paths=20),
            "module04": simulate_brownian_motion(steps=20, paths=20),
            "module05": analyze_markov_chain(steps=20),
            "module08": simulate_nhpp_thinning(horizon=24, paths=20),
            "module09": simulate_self_avoiding_walk(max_steps=30, runs=20),
            "module10": simulate_coalescing_particles(circle_size=12, particles=5, runs=20, max_steps=100),
        }
        former_partial = {
            item["visualization_id"]
            for item in self.registry["visualizations"]
            if item["visualization_id"] in {
                "module01-viz-04", "module01-viz-07", "module01-viz-08",
                "module04-viz-05", "module04-viz-06", "module05-viz-02", "module05-viz-03",
                "module05-viz-08", "module08-viz-03", "module08-viz-05", "module09-viz-02",
                "module09-viz-04", "module09-viz-05", "module10-viz-02", "module10-viz-03",
            }
        }
        exposed = {item["id"] for payload in payloads.values() for item in payload.get("visualizations", [])}
        self.assertTrue(former_partial.issubset(exposed))

    def test_counting_comparison_panels_keep_parameter_labels(self) -> None:
        result = simulate_bernoulli_process(slots=20, paths=20)
        visualizations = {item["id"]: item for item in result["visualizations"]}
        for visualization_id in ("module01-viz-04", "module01-viz-07"):
            panels = visualizations[visualization_id]["panels"]
            self.assertEqual([panel["parameter"]["probability"] for panel in panels], [0.1, 0.3, 0.6])
            self.assertTrue(all(len(panel["x"]) == len(panel["empirical"]) == len(panel["theoretical"]) for panel in panels))

    def test_all_registry_renderers_are_supported(self) -> None:
        self.assertTrue(
            all(item.get("renderer") in SUPPORTED_RENDERERS for item in self.registry["visualizations"])
        )


if __name__ == "__main__":
    unittest.main()
