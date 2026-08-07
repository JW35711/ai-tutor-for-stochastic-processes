import json
import unittest
from pathlib import Path

from evals.run_evaluation import evaluate


ROOT = Path(__file__).resolve().parent.parent


class EvaluationTests(unittest.TestCase):
    def test_thirty_case_acceptance_set_passes(self) -> None:
        cases = json.loads((ROOT / "evals" / "cases.json").read_text("utf-8"))
        self.assertEqual(len(cases), 30)
        report = evaluate(cases)
        self.assertEqual(report["passed"], 30)
        self.assertEqual(report["pass_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
