import unittest

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.tool_catalog import build_tool_catalog


class ToolCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)

    def tearDown(self) -> None:
        self.memory.close()

    def test_catalog_exposes_all_tools_and_modules(self) -> None:
        catalogue = build_tool_catalog(self.agent.tools)
        self.assertEqual(len(catalogue), 15)
        self.assertEqual(len({item["key"] for item in catalogue}), 15)
        covered = {
            module_id
            for item in catalogue
            for module_id in item["module_ids"]
        }
        self.assertEqual(covered, {f"module{index:02d}" for index in range(11)})

    def test_catalog_parameters_are_json_ready(self) -> None:
        catalogue = build_tool_catalog(self.agent.tools)
        poisson = next(item for item in catalogue if item["key"] == "poisson")
        rate = next(item for item in poisson["parameters"] if item["name"] == "rate")
        self.assertEqual(
            rate,
            {
                "name": "rate",
                "type": "number",
                "required": False,
                "default": 2.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
