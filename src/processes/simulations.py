"""Dependency-free stochastic-process tools used by the teaching agent.

The notebooks remain the full teaching material.  These functions expose a
small, deterministic and JSON-serialisable subset for an interview-ready MVP.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any


def _positive_int(value: int, name: str, maximum: int = 100_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value <= 0 or value > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _positive_float(value: float, name: str, maximum: float = 10_000.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > maximum:
        raise ValueError(f"{name} must be in (0, {maximum}]")
    return number


def _compress_series(values: Sequence[float], max_points: int = 240) -> list[float]:
    """Keep payloads small while retaining the shape of a simulated path."""
    if len(values) <= max_points:
        return [round(float(value), 6) for value in values]
    stride = math.ceil((len(values) - 1) / (max_points - 1))
    compressed = [values[index] for index in range(0, len(values), stride)]
    if compressed[-1] != values[-1]:
        compressed.append(values[-1])
    return [round(float(value), 6) for value in compressed]


def run_monte_carlo_pi(samples: int = 5_000, seed: int = 42) -> dict[str, Any]:
    """Estimate pi with uniform points in the unit square."""
    samples = _positive_int(samples, "samples", 200_000)
    rng = random.Random(seed)
    inside = 0
    convergence: list[float] = []
    checkpoints = set(
        max(1, round(index * samples / min(samples, 120)))
        for index in range(1, min(samples, 120) + 1)
    )

    for index in range(1, samples + 1):
        x, y = rng.random(), rng.random()
        inside += x * x + y * y <= 1.0
        if index in checkpoints:
            convergence.append(4.0 * inside / index)

    estimate = 4.0 * inside / samples
    return {
        "topic": "monte_carlo",
        "parameters": {"samples": samples, "seed": seed},
        "estimate": round(estimate, 6),
        "theoretical": round(math.pi, 6),
        "absolute_error": round(abs(estimate - math.pi), 6),
        "inside_points": inside,
        "series": [{"name": "π estimate", "values": _compress_series(convergence)}],
        "chart": {"x_label": "checkpoints", "y_label": "estimate"},
    }


def simulate_poisson_process(
    rate: float = 2.0,
    horizon: float = 5.0,
    paths: int = 8,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate homogeneous Poisson processes using exponential waiting times."""
    rate = _positive_float(rate, "rate", 1_000.0)
    horizon = _positive_float(horizon, "horizon", 10_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    rng = random.Random(seed)
    counts: list[int] = []
    event_paths: list[list[float]] = []

    for _ in range(paths):
        time = 0.0
        events: list[float] = []
        while True:
            time += rng.expovariate(rate)
            if time > horizon:
                break
            events.append(time)
        counts.append(len(events))
        if len(event_paths) < 8:
            event_paths.append(events)

    empirical_mean = sum(counts) / paths
    expected_count = rate * horizon
    first_events = event_paths[0] if event_paths else []
    step_times = [0.0, *first_events, horizon]
    step_counts = list(range(len(first_events) + 1)) + [len(first_events)]
    return {
        "topic": "poisson",
        "parameters": {
            "rate": rate,
            "horizon": horizon,
            "paths": paths,
            "seed": seed,
        },
        "empirical_mean_count": round(empirical_mean, 6),
        "theoretical_mean_count": round(expected_count, 6),
        "absolute_error": round(abs(empirical_mean - expected_count), 6),
        "counts": counts[:200],
        "event_times": [
            [round(event, 6) for event in events] for events in event_paths
        ],
        "series": [
            {
                "name": "first counting path",
                "x": _compress_series(step_times),
                "values": _compress_series(step_counts),
            }
        ],
        "chart": {"x_label": "time", "y_label": "N(t)"},
    }


def simulate_random_walk(
    steps: int = 100,
    probability_up: float = 0.5,
    paths: int = 20,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate one-dimensional random walks with increments in {-1, +1}."""
    steps = _positive_int(steps, "steps", 50_000)
    paths = _positive_int(paths, "paths", 2_000)
    probability_up = float(probability_up)
    if not 0.0 <= probability_up <= 1.0:
        raise ValueError("probability_up must be between 0 and 1")

    rng = random.Random(seed)
    endpoints: list[int] = []
    sample_paths: list[list[int]] = []
    for _ in range(paths):
        position = 0
        path = [position]
        for _ in range(steps):
            position += 1 if rng.random() < probability_up else -1
            path.append(position)
        endpoints.append(position)
        if len(sample_paths) < 8:
            sample_paths.append(path)

    empirical_mean = sum(endpoints) / paths
    endpoint_variance = sum((x - empirical_mean) ** 2 for x in endpoints) / paths
    theoretical_mean = steps * (2.0 * probability_up - 1.0)
    theoretical_variance = 4.0 * steps * probability_up * (1.0 - probability_up)
    return {
        "topic": "random_walk",
        "parameters": {
            "steps": steps,
            "probability_up": probability_up,
            "paths": paths,
            "seed": seed,
        },
        "empirical_endpoint_mean": round(empirical_mean, 6),
        "theoretical_endpoint_mean": round(theoretical_mean, 6),
        "empirical_endpoint_variance": round(endpoint_variance, 6),
        "theoretical_endpoint_variance": round(theoretical_variance, 6),
        "endpoints": endpoints[:200],
        "series": [
            {"name": f"path {index + 1}", "values": _compress_series(path)}
            for index, path in enumerate(sample_paths)
        ],
        "chart": {"x_label": "step", "y_label": "position"},
    }


def simulate_continuous_random_walk(
    rate: float = 1.0,
    horizon: float = 10.0,
    probability_up: float = 0.5,
    paths: int = 20,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate X(t)=S_{N(t)} with Poisson jump times and signed jumps."""

    rate = _positive_float(rate, "rate", 1_000.0)
    horizon = _positive_float(horizon, "horizon", 10_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    probability_up = float(probability_up)
    if not 0.0 <= probability_up <= 1.0:
        raise ValueError("probability_up must be between 0 and 1")

    rng = random.Random(seed)
    endpoints: list[int] = []
    jump_counts: list[int] = []
    sample_series: list[dict[str, Any]] = []

    for path_index in range(paths):
        time = 0.0
        position = 0
        jump_times: list[float] = []
        positions: list[int] = []
        while True:
            time += rng.expovariate(rate)
            if time > horizon:
                break
            position += 1 if rng.random() < probability_up else -1
            jump_times.append(time)
            positions.append(position)

        endpoints.append(position)
        jump_counts.append(len(jump_times))
        if path_index < 8:
            x_values = [0.0, *jump_times, horizon]
            y_values = [0, *positions, position]
            sample_series.append(
                {
                    "name": f"path {path_index + 1}",
                    "x": _compress_series(x_values),
                    "values": _compress_series(y_values),
                }
            )

    endpoint_mean = sum(endpoints) / paths
    endpoint_variance = (
        sum((value - endpoint_mean) ** 2 for value in endpoints) / paths
    )
    jump_mean = sum(jump_counts) / paths
    theoretical_mean = rate * horizon * (2.0 * probability_up - 1.0)
    theoretical_variance = rate * horizon

    return {
        "topic": "continuous_random_walk",
        "parameters": {
            "rate": rate,
            "horizon": horizon,
            "probability_up": probability_up,
            "paths": paths,
            "seed": seed,
        },
        "empirical_jump_mean": round(jump_mean, 6),
        "theoretical_jump_mean": round(rate * horizon, 6),
        "empirical_endpoint_mean": round(endpoint_mean, 6),
        "theoretical_endpoint_mean": round(theoretical_mean, 6),
        "empirical_endpoint_variance": round(endpoint_variance, 6),
        "theoretical_endpoint_variance": round(theoretical_variance, 6),
        "endpoints": endpoints[:200],
        "jump_counts": jump_counts[:200],
        "series": sample_series,
        "chart": {"x_label": "time", "y_label": "position", "step": "post"},
    }


def simulate_brownian_motion(
    horizon: float = 1.0,
    steps: int = 200,
    paths: int = 12,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate standard Brownian motion with Gaussian increments."""
    horizon = _positive_float(horizon, "horizon", 1_000.0)
    steps = _positive_int(steps, "steps", 50_000)
    paths = _positive_int(paths, "paths", 2_000)
    rng = random.Random(seed)
    dt = horizon / steps
    scale = math.sqrt(dt)
    endpoints: list[float] = []
    sample_paths: list[list[float]] = []

    for _ in range(paths):
        value = 0.0
        path = [value]
        for _ in range(steps):
            value += rng.gauss(0.0, scale)
            path.append(value)
        endpoints.append(value)
        if len(sample_paths) < 8:
            sample_paths.append(path)

    mean = sum(endpoints) / paths
    variance = sum((endpoint - mean) ** 2 for endpoint in endpoints) / paths
    return {
        "topic": "brownian_motion",
        "parameters": {
            "horizon": horizon,
            "steps": steps,
            "paths": paths,
            "seed": seed,
        },
        "empirical_terminal_mean": round(mean, 6),
        "theoretical_terminal_mean": 0.0,
        "empirical_terminal_variance": round(variance, 6),
        "theoretical_terminal_variance": round(horizon, 6),
        "endpoints": [round(value, 6) for value in endpoints[:200]],
        "series": [
            {"name": f"path {index + 1}", "values": _compress_series(path)}
            for index, path in enumerate(sample_paths)
        ],
        "chart": {"x_label": "time step", "y_label": "B(t)"},
    }


def _validate_transition_matrix(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    if not matrix or not all(isinstance(row, Sequence) for row in matrix):
        raise ValueError("transition_matrix must be a non-empty square matrix")
    size = len(matrix)
    validated: list[list[float]] = []
    for row in matrix:
        if len(row) != size:
            raise ValueError("transition_matrix must be square")
        numeric_row = [float(value) for value in row]
        if any(not math.isfinite(value) or value < 0.0 for value in numeric_row):
            raise ValueError("transition probabilities must be finite and non-negative")
        if not math.isclose(sum(numeric_row), 1.0, abs_tol=1e-9):
            raise ValueError("each transition-matrix row must sum to 1")
        validated.append(numeric_row)
    return validated


def _next_state(probabilities: Sequence[float], rng: random.Random) -> int:
    draw = rng.random()
    cumulative = 0.0
    for state, probability in enumerate(probabilities):
        cumulative += probability
        if draw <= cumulative:
            return state
    return len(probabilities) - 1


def _stationary_distribution(
    matrix: Sequence[Sequence[float]],
    iterations: int = 10_000,
    tolerance: float = 1e-12,
) -> list[float]:
    size = len(matrix)
    distribution = [1.0 / size] * size
    for _ in range(iterations):
        updated = [
            sum(distribution[i] * matrix[i][j] for i in range(size))
            for j in range(size)
        ]
        if max(abs(a - b) for a, b in zip(updated, distribution, strict=True)) < tolerance:
            return updated
        distribution = updated
    return distribution


def analyze_markov_chain(
    transition_matrix: Sequence[Sequence[float]] | None = None,
    initial_state: int = 0,
    steps: int = 80,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate a finite Markov chain and estimate its stationary distribution."""
    matrix = _validate_transition_matrix(
        transition_matrix or [[0.9, 0.1], [0.3, 0.7]]
    )
    steps = _positive_int(steps, "steps", 100_000)
    if isinstance(initial_state, bool) or not 0 <= initial_state < len(matrix):
        raise ValueError("initial_state is outside the matrix state space")

    rng = random.Random(seed)
    state = initial_state
    path = [state]
    counts = [0] * len(matrix)
    counts[state] += 1
    for _ in range(steps):
        state = _next_state(matrix[state], rng)
        path.append(state)
        counts[state] += 1

    total = len(path)
    empirical = [count / total for count in counts]
    stationary = _stationary_distribution(matrix)
    return {
        "topic": "markov_chain",
        "parameters": {
            "transition_matrix": matrix,
            "initial_state": initial_state,
            "steps": steps,
            "seed": seed,
        },
        "empirical_frequencies": [round(value, 6) for value in empirical],
        "stationary_distribution": [round(value, 6) for value in stationary],
        "l1_error": round(
            sum(abs(a - b) for a, b in zip(empirical, stationary, strict=True)),
            6,
        ),
        "series": [{"name": "state path", "values": _compress_series(path)}],
        "chart": {"x_label": "step", "y_label": "state"},
    }
