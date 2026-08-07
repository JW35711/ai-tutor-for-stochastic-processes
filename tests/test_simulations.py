import math
import unittest

from src.processes import (
    analyze_markov_chain,
    run_monte_carlo_pi,
    simulate_brownian_motion,
    simulate_birth_death_process,
    simulate_continuous_random_walk,
    simulate_poisson_process,
    simulate_random_walk,
    simulate_two_state_ctmc,
)


class SimulationToolTests(unittest.TestCase):
    def test_monte_carlo_is_reproducible(self) -> None:
        first = run_monte_carlo_pi(samples=20_000, seed=7)
        second = run_monte_carlo_pi(samples=20_000, seed=7)
        self.assertEqual(first["estimate"], second["estimate"])
        self.assertLess(first["absolute_error"], 0.06)

    def test_poisson_mean_tracks_lambda_t(self) -> None:
        result = simulate_poisson_process(rate=2.0, horizon=3.0, paths=2_000, seed=8)
        self.assertLess(
            abs(result["empirical_mean_count"] - result["theoretical_mean_count"]),
            0.25,
        )

    def test_random_walk_theory(self) -> None:
        result = simulate_random_walk(
            steps=100, probability_up=0.6, paths=2_000, seed=9
        )
        self.assertEqual(result["theoretical_endpoint_mean"], 20.0)
        self.assertLess(abs(result["empirical_endpoint_mean"] - 20.0), 1.5)

    def test_brownian_terminal_variance(self) -> None:
        result = simulate_brownian_motion(
            horizon=2.0, steps=100, paths=2_000, seed=10
        )
        self.assertLess(abs(result["empirical_terminal_variance"] - 2.0), 0.2)

    def test_continuous_random_walk_tracks_compound_poisson_moments(self) -> None:
        result = simulate_continuous_random_walk(
            rate=2.0,
            horizon=3.0,
            probability_up=0.6,
            paths=2_000,
            seed=12,
        )
        self.assertLess(abs(result["empirical_jump_mean"] - 6.0), 0.2)
        self.assertLess(abs(result["empirical_endpoint_mean"] - 1.2), 0.2)
        self.assertLess(abs(result["empirical_endpoint_variance"] - 6.0), 0.4)

    def test_continuous_random_walk_rejects_invalid_probability(self) -> None:
        with self.assertRaises(ValueError):
            simulate_continuous_random_walk(probability_up=-0.1)

    def test_markov_stationary_distribution(self) -> None:
        result = analyze_markov_chain(
            [[0.9, 0.1], [0.3, 0.7]], steps=10_000, seed=11
        )
        stationary = result["stationary_distribution"]
        self.assertTrue(math.isclose(stationary[0], 0.75, abs_tol=1e-5))
        self.assertTrue(math.isclose(sum(stationary), 1.0, abs_tol=1e-6))

    def test_invalid_transition_matrix_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_markov_chain([[0.9, 0.2], [0.3, 0.7]])

    def test_invalid_probability_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            simulate_random_walk(probability_up=1.2)

    def test_two_state_ctmc_matches_holding_time_and_stationary_theory(self) -> None:
        result = simulate_two_state_ctmc(
            failure_rate=0.25,
            repair_rate=0.15,
            horizon=160.0,
            paths=800,
            seed=13,
        )
        self.assertEqual(result["stationary_distribution"], [0.375, 0.625])
        self.assertLess(result["l1_error"], 0.04)
        self.assertLess(
            abs(result["empirical_mean_holding_times"][0] - 4.0), 0.2
        )
        self.assertLess(
            abs(result["empirical_mean_holding_times"][1] - 20.0 / 3.0),
            0.3,
        )
        self.assertEqual(result["chart"]["step"], "post")

    def test_birth_death_process_matches_stationary_distribution(self) -> None:
        result = simulate_birth_death_process(
            birth_rate=0.35,
            death_rate=0.30,
            capacity=6,
            horizon=500.0,
            paths=800,
            seed=14,
        )
        stationary = result["stationary_distribution"]
        self.assertTrue(math.isclose(sum(stationary), 1.0, abs_tol=1e-5))
        self.assertTrue(
            math.isclose(
                stationary[1] / stationary[0],
                0.35 / 0.30,
                rel_tol=1e-5,
            )
        )
        self.assertLess(result["l1_error"], 0.05)
        self.assertEqual(len(result["generator_matrix"]), 7)

    def test_birth_death_rejects_state_outside_capacity(self) -> None:
        with self.assertRaises(ValueError):
            simulate_birth_death_process(capacity=3, initial_state=4)


if __name__ == "__main__":
    unittest.main()
