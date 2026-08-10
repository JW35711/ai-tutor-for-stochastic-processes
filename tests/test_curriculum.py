import unittest

from src.curriculum import load_curriculum


class CurriculumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.curriculum = load_curriculum()
        self.modules = self.curriculum["modules"]
        self.points = [
            point
            for module in self.modules
            for point in module["knowledge_points"]
        ]

    def test_all_eleven_modules_are_present(self) -> None:
        self.assertEqual(
            {module["module_id"] for module in self.modules},
            {f"module{index:02d}" for index in range(11)},
        )

    def test_knowledge_point_ids_are_unique(self) -> None:
        identifiers = [point["id"] for point in self.points]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_prerequisites_reference_existing_concepts(self) -> None:
        identifiers = {point["id"] for point in self.points}
        for point in self.points:
            with self.subTest(concept=point["id"]):
                self.assertTrue(set(point["prerequisites"]) <= identifiers)

    def test_module05_contains_markov_property_and_stationary_distribution(self) -> None:
        module05 = next(module for module in self.modules if module["module_id"] == "module05")
        titles = {point["title"] for point in module05["knowledge_points"]}
        self.assertIn("Markov Property", titles)
        self.assertIn("Stationary Distribution", titles)


if __name__ == "__main__":
    unittest.main()
