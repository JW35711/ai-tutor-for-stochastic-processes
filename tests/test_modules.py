import unittest
from pathlib import Path

from src.knowledge import KnowledgeBase
from src.module_registry import MODULES, MODULE_BY_ID, module_catalog


class ModuleRegistryTests(unittest.TestCase):
    def test_registry_covers_module_00_to_10(self) -> None:
        self.assertEqual([module.number for module in MODULES], list(range(11)))
        self.assertEqual(len(MODULE_BY_ID), 11)

    def test_every_registered_notebook_exists(self) -> None:
        root = Path(__file__).resolve().parent.parent
        for module in MODULES:
            with self.subTest(module=module.module_id):
                self.assertTrue((root / module.notebook).is_file())

    def test_knowledge_base_has_one_card_per_module(self) -> None:
        entries = KnowledgeBase().entries
        module_ids = {entry["module_id"] for entry in entries if entry["module_id"]}
        self.assertTrue(set(MODULE_BY_ID).issubset(module_ids))

    def test_public_catalog_reports_tool_coverage(self) -> None:
        catalog = module_catalog()
        self.assertEqual(len(catalog), 11)
        self.assertEqual(sum(bool(item["tool_ready"]) for item in catalog), 11)
        self.assertTrue(all("keywords" not in item for item in catalog))


if __name__ == "__main__":
    unittest.main()
