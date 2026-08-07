import unittest

from evals.run_latency_benchmark import (
    benchmark,
    percentile,
    representative_cases,
    summary,
)


class LatencyBenchmarkTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(percentile(values, 50), 2.0)
        self.assertEqual(percentile(values, 95), 4.0)
        self.assertEqual(summary(values)["mean_ms"], 2.5)

    def test_representative_cases_requires_all_eleven_modules(self) -> None:
        incomplete = [
            {
                "id": "only-one",
                "question": "Monte Carlo",
                "expected_module": "module00",
            }
        ]
        with self.assertRaisesRegex(ValueError, "module00 through module10"):
            representative_cases(incomplete)

    def test_invalid_percentile_and_repetitions_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            percentile([], 50)
        with self.assertRaises(ValueError):
            percentile([1.0], 0)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            benchmark([], repetitions=0)


if __name__ == "__main__":
    unittest.main()
