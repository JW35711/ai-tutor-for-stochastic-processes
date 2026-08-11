import unittest

from evals.run_retrieval_evaluation import evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_curated_retrieval_suite_has_full_hit_at_three(self) -> None:
        report = evaluate()
        self.assertEqual(report["total"], 44)
        self.assertRegex(report["corpus_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(report["hit_at_3"], 1.0)
        self.assertGreaterEqual(report["mrr"], 0.9)
        self.assertEqual(report["failures"], [])
        self.assertEqual(len(report["case_results"]), 44)
        self.assertTrue(
            all(1 <= item["rank"] <= 3 for item in report["case_results"])
        )
        self.assertTrue(
            all(item["matched_phrase"] for item in report["case_results"])
        )
        self.assertRegex(report["cases_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
