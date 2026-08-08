import unittest

from evals.run_safety_evaluation import evaluate


class SafetyEvaluationTests(unittest.TestCase):
    def test_all_bounded_agent_safety_cases_pass(self) -> None:
        report = evaluate()
        self.assertEqual(report["total"], 10)
        self.assertEqual(report["passed"], report["total"])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
