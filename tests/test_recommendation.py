import unittest

from src.recommendation import recommend_next


class RecommendationTests(unittest.TestCase):
    def test_new_learner_starts_with_monte_carlo(self) -> None:
        recommendation = recommend_next({"modules": []})
        self.assertEqual(recommendation["module_id"], "module00")
        self.assertEqual(recommendation["reason_code"], "start_foundation")

    def test_low_evidence_module_is_revisited_transparently(self) -> None:
        recommendation = recommend_next(
            {
                "modules": [
                    {
                        "module_id": "module04",
                        "mastery": 0.45,
                        "quiz_attempts": 0,
                    }
                ]
            }
        )
        self.assertEqual(recommendation["module_id"], "module04")
        self.assertEqual(recommendation["reason_code"], "strengthen_evidence")
        self.assertIn("概念题", recommendation["reason"])

    def test_next_uncovered_module_follows_course_order(self) -> None:
        modules = [
            {
                "module_id": f"module{index:02d}",
                "mastery": 0.8,
                "quiz_attempts": 1,
            }
            for index in range(3)
        ]
        recommendation = recommend_next({"modules": modules})
        self.assertEqual(recommendation["module_id"], "module03")
        self.assertEqual(recommendation["reason_code"], "expand_coverage")


if __name__ == "__main__":
    unittest.main()
