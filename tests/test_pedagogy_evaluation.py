import unittest

from evals.run_pedagogy_evaluation import evaluate


class PedagogyEvaluationTests(unittest.TestCase):
    def test_misconception_and_structure_suite_passes(self) -> None:
        report = evaluate()
        self.assertEqual(report["total"], 10)
        self.assertEqual(report["pass_rate"], 1.0)
        self.assertEqual(report["structured_answer_rate"], 1.0)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
