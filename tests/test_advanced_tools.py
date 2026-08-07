import unittest

from src.processes import (
    analyze_reliability_system,
    simulate_batch_buffer,
    simulate_bernoulli_process,
    simulate_coalescing_particles,
    simulate_mm1_queue,
    simulate_nhpp_thinning,
    simulate_self_avoiding_walk,
)


class AdvancedToolTests(unittest.TestCase):
    def test_bernoulli_count_and_waiting_time_match_theory(self) -> None:
        result = simulate_bernoulli_process(
            slots=80, probability=0.25, paths=4_000, seed=21
        )
        self.assertLess(
            abs(result["empirical_count_mean"] - result["theoretical_count_mean"]),
            0.25,
        )
        self.assertLess(
            abs(
                result["empirical_waiting_mean"]
                - result["theoretical_waiting_mean"]
            ),
            0.15,
        )

    def test_reliability_system_matches_series_and_parallel_theory(self) -> None:
        result = analyze_reliability_system(samples=10_000, seed=22)
        self.assertLess(result["series_max_curve_error"], 0.025)
        self.assertLess(result["parallel_max_curve_error"], 0.025)
        self.assertGreater(
            result["empirical_parallel_mean_lifetime"],
            result["empirical_series_mean_lifetime"],
        )

    def test_batch_buffer_reports_arrival_drift(self) -> None:
        result = simulate_batch_buffer(
            steps=200, arrival_probability=0.6, paths=1_000, seed=23
        )
        self.assertLess(
            abs(
                result["empirical_arrivals_per_slot"]
                - result["theoretical_arrivals_per_slot"]
            ),
            0.03,
        )
        self.assertLess(result["theoretical_drift_when_busy"], 0.0)

    def test_mm1_stable_queue_matches_mean_customer_theory(self) -> None:
        result = simulate_mm1_queue(
            arrival_rate=0.75,
            service_rate=1.0,
            horizon=3_000,
            paths=30,
            seed=24,
        )
        self.assertTrue(result["stable"])
        self.assertLess(
            abs(
                result["empirical_mean_customers"]
                - result["theoretical_mean_customers"]
            ),
            0.4,
        )

    def test_mm1_unstable_queue_has_no_stationary_claim(self) -> None:
        result = simulate_mm1_queue(
            arrival_rate=1.1,
            service_rate=1.0,
            horizon=100,
            paths=5,
            seed=25,
        )
        self.assertFalse(result["stable"])
        self.assertIsNone(result["theoretical_state_probabilities"])
        self.assertIsNone(result["theoretical_mean_customers"])

    def test_nhpp_thinning_matches_integrated_intensity(self) -> None:
        result = simulate_nhpp_thinning(paths=500, seed=26)
        self.assertLess(result["absolute_error"], 1.5)
        self.assertGreaterEqual(result["candidate_count"], result["accepted_count"])
        self.assertGreater(result["acceptance_rate"], 0.0)
        self.assertLessEqual(result["acceptance_rate"], 1.0)

    def test_nhpp_rejects_peak_outside_horizon(self) -> None:
        with self.assertRaises(ValueError):
            simulate_nhpp_thinning(horizon=10, peak_center=11)

    def test_self_avoiding_walk_preserves_path_invariants(self) -> None:
        result = simulate_self_avoiding_walk(max_steps=1_000, runs=300, seed=27)
        self.assertTrue(result["sample_self_avoiding"])
        self.assertTrue(result["sample_nearest_neighbour"])
        self.assertEqual(result["trapped_runs"] + result["unfinished_runs"], 300)

    def test_coalescing_particles_preserve_cluster_invariant(self) -> None:
        result = simulate_coalescing_particles(
            circle_size=12, particles=9, runs=300, seed=28
        )
        self.assertTrue(result["sample_cluster_count_monotone"])
        self.assertEqual(result["completed_runs"] + result["unfinished_runs"], 300)
        self.assertEqual(result["sample_final_cluster_count"], 1)

    def test_coalescing_particles_reject_too_many_particles(self) -> None:
        with self.assertRaises(ValueError):
            simulate_coalescing_particles(circle_size=5, particles=6)


if __name__ == "__main__":
    unittest.main()
