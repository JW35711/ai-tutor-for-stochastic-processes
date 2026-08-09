import unittest

from src.recommendation import recommend_next


class RecommendationTests(unittest.TestCase):
    def test_new_learner_starts_with_monte_carlo(self) -> None:
        recommendation = recommend_next({"modules": []})
        self.assertEqual(recommendation["module_id"], "module00")
        self.assertEqual(recommendation["reason_code"], "start_foundation")
        self.assertEqual(recommendation["review_interval_days"], "1")

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
        self.assertEqual(recommendation["review_interval_days"], "1")

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
        self.assertEqual(recommendation["review_interval_days"], "1")

    def test_stronger_practice_evidence_gets_longer_review_interval(self) -> None:
        recommendation = recommend_next(
            {
                "modules": [
                    {
                        "module_id": f"module{index:02d}",
                        "mastery": 0.85,
                        "quiz_attempts": 2,
                    }
                    for index in range(11)
                ]
            }
        )
        self.assertEqual(recommendation["reason_code"], "boundary_challenge")
        self.assertEqual(recommendation["review_interval_days"], "7")


if __name__ == "__main__":
    unittest.main()
