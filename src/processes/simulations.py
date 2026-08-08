"""Dependency-free stochastic-process tools used by the teaching agent.

The notebooks remain the full teaching material.  These functions expose a
small, deterministic and JSON-serialisable subset for an interview-ready MVP.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any


MAX_RECORDED_TRANSITIONS = 500


def _positive_int(value: int, name: str, maximum: int = 100_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value <= 0 or value > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _positive_float(
    value: float,
    name: str,
    maximum: float = 10_000.0,
    minimum: float = 1e-12,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < minimum or number > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _probability(value: float, name: str, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    lower_ok = number >= 0.0 if allow_zero else number >= 1e-12
    if not math.isfinite(number) or not lower_ok or number > 1.0:
        interval = "[0, 1]" if allow_zero else "[1e-12, 1]"
        raise ValueError(f"{name} must be in {interval}")
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
    paths: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate homogeneous Poisson processes using exponential waiting times."""
    rate = _positive_float(rate, "rate", 1_000.0)
    horizon = _positive_float(horizon, "horizon", 10_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    if rate * horizon * paths > 3_000_000:
        raise ValueError("requested Poisson experiment is too large")
    rng = random.Random(seed)
    counts: list[int] = []
    event_paths: list[list[float]] = []

    event_times_truncated = False
    for path_index in range(paths):
        time = 0.0
        events: list[float] = []
        count = 0
        while True:
            time += rng.expovariate(rate)
            if time > horizon:
                break
            count += 1
            if path_index < 8 and len(events) < MAX_RECORDED_TRANSITIONS:
                events.append(time)
            elif path_index < 8:
                event_times_truncated = True
        counts.append(count)
        if path_index < 8:
            event_paths.append(events)

    empirical_mean = sum(counts) / paths
    expected_count = rate * horizon
    first_events = event_paths[0] if event_paths else []
    step_times = [0.0, *first_events, horizon]
    step_counts = list(range(len(first_events) + 1)) + [counts[0]]
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
        "event_times_truncated": event_times_truncated,
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
    paths: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate one-dimensional random walks with increments in {-1, +1}."""
    steps = _positive_int(steps, "steps", 50_000)
    paths = _positive_int(paths, "paths", 2_000)
    probability_up = _probability(probability_up, "probability_up")
    if steps * paths > 3_000_000:
        raise ValueError("requested random-walk experiment is too large")

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
    paths: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate X(t)=S_{N(t)} with Poisson jump times and signed jumps."""

    rate = _positive_float(rate, "rate", 1_000.0)
    horizon = _positive_float(horizon, "horizon", 10_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    probability_up = _probability(probability_up, "probability_up")
    if rate * horizon * paths > 3_000_000:
        raise ValueError("requested continuous random-walk experiment is too large")

    rng = random.Random(seed)
    endpoints: list[int] = []
    jump_counts: list[int] = []
    sample_series: list[dict[str, Any]] = []
    series_truncated = False

    for path_index in range(paths):
        time = 0.0
        position = 0
        record_path = path_index < 8
        jump_times: list[float] = []
        positions: list[int] = []
        jump_count = 0
        while True:
            time += rng.expovariate(rate)
            if time > horizon:
                break
            position += 1 if rng.random() < probability_up else -1
            jump_count += 1
            if record_path and len(jump_times) < MAX_RECORDED_TRANSITIONS:
                jump_times.append(time)
                positions.append(position)
            elif record_path:
                series_truncated = True

        endpoints.append(position)
        jump_counts.append(jump_count)
        if record_path:
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
        "series_truncated": series_truncated,
        "series": sample_series,
        "chart": {"x_label": "time", "y_label": "position", "step": "post"},
    }


def simulate_brownian_motion(
    horizon: float = 1.0,
    steps: int = 200,
    paths: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate standard Brownian motion with Gaussian increments."""
    horizon = _positive_float(horizon, "horizon", 1_000.0)
    steps = _positive_int(steps, "steps", 50_000)
    paths = _positive_int(paths, "paths", 2_000)
    if steps * paths > 3_000_000:
        raise ValueError("requested Brownian-motion experiment is too large")
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
    if size > 50:
        raise ValueError("transition_matrix must have at most 50 states")
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


def _step_series(
    times: Sequence[float], states: Sequence[int], horizon: float, name: str
) -> dict[str, Any]:
    """Return a compact right-continuous state path ending at the horizon."""

    x_values = [float(value) for value in times]
    y_values = [int(value) for value in states]
    if x_values[-1] < horizon:
        x_values.append(horizon)
        y_values.append(y_values[-1])
    return {
        "name": name,
        "x": _compress_series(x_values),
        "values": _compress_series(y_values),
    }


def simulate_two_state_ctmc(
    failure_rate: float = 0.25,
    repair_rate: float = 0.15,
    horizon: float = 200.0,
    paths: int = 200,
    initial_state: int = 0,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate a working/repair CTMC and compare holding-time theory."""

    failure_rate = _positive_float(failure_rate, "failure_rate", 100.0)
    repair_rate = _positive_float(repair_rate, "repair_rate", 100.0)
    horizon = _positive_float(horizon, "horizon", 1_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    if isinstance(initial_state, bool) or initial_state not in {0, 1}:
        raise ValueError("initial_state must be 0 (working) or 1 (repair)")
    if max(failure_rate, repair_rate) * horizon * paths > 2_000_000:
        raise ValueError("requested CTMC experiment is too large")

    rng = random.Random(seed)
    occupancy = [0.0, 0.0]
    holding_sums = [0.0, 0.0]
    holding_counts = [0, 0]
    sample_series: list[dict[str, Any]] = []
    transition_count = 0
    series_truncated = False

    for path_index in range(paths):
        time = 0.0
        state = initial_state
        record_path = path_index < 5
        times = [time]
        states = [state]
        path_truncated = False
        while time < horizon:
            leaving_rate = failure_rate if state == 0 else repair_rate
            holding_time = rng.expovariate(leaving_rate)
            next_time = min(time + holding_time, horizon)
            occupancy[state] += next_time - time
            if time + holding_time > horizon:
                time = horizon
                break

            holding_sums[state] += holding_time
            holding_counts[state] += 1
            time = next_time
            state = 1 - state
            transition_count += 1
            if record_path and len(times) <= MAX_RECORDED_TRANSITIONS:
                times.append(time)
                states.append(state)
            elif record_path:
                path_truncated = True

        if record_path:
            if path_truncated:
                times.append(horizon)
                states.append(state)
                series_truncated = True
            sample_series.append(
                _step_series(times, states, horizon, f"path {path_index + 1}")
            )

    total_time = horizon * paths
    empirical = [value / total_time for value in occupancy]
    denominator = failure_rate + repair_rate
    stationary = [repair_rate / denominator, failure_rate / denominator]
    theoretical_holding = [1.0 / failure_rate, 1.0 / repair_rate]
    empirical_holding = [
        round(total / count, 6) if count else None
        for total, count in zip(holding_sums, holding_counts, strict=True)
    ]

    return {
        "topic": "ctmc",
        "model": "two_state_machine",
        "parameters": {
            "failure_rate": failure_rate,
            "repair_rate": repair_rate,
            "horizon": horizon,
            "paths": paths,
            "initial_state": initial_state,
            "seed": seed,
        },
        "generator_matrix": [
            [-failure_rate, failure_rate],
            [repair_rate, -repair_rate],
        ],
        "empirical_state_probabilities": [round(value, 6) for value in empirical],
        "stationary_distribution": [round(value, 6) for value in stationary],
        "l1_error": round(
            sum(abs(a - b) for a, b in zip(empirical, stationary, strict=True)),
            6,
        ),
        "empirical_mean_holding_times": empirical_holding,
        "theoretical_mean_holding_times": [
            round(value, 6) for value in theoretical_holding
        ],
        "transition_count": transition_count,
        "series_truncated": series_truncated,
        "series": sample_series,
        "chart": {"x_label": "time", "y_label": "state", "step": "post"},
    }


def _birth_death_stationary(
    birth_rate: float, death_rate: float, capacity: int
) -> list[float]:
    ratio = birth_rate / death_rate
    if ratio >= 1.0:
        # Scale relative to the largest state so no positive power can overflow.
        weights = [ratio ** (state - capacity) for state in range(capacity + 1)]
    else:
        weights = [ratio**state for state in range(capacity + 1)]
    normalizer = sum(weights)
    return [weight / normalizer for weight in weights]


def simulate_birth_death_process(
    birth_rate: float = 0.35,
    death_rate: float = 0.30,
    capacity: int = 6,
    horizon: float = 500.0,
    paths: int = 200,
    initial_state: int = 2,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate a finite birth-death CTMC with constant interior rates."""

    birth_rate = _positive_float(birth_rate, "birth_rate", 100.0)
    death_rate = _positive_float(death_rate, "death_rate", 100.0)
    capacity = _positive_int(capacity, "capacity", 100)
    horizon = _positive_float(horizon, "horizon", 1_000.0)
    paths = _positive_int(paths, "paths", 2_000)
    if (
        isinstance(initial_state, bool)
        or not isinstance(initial_state, int)
        or not 0 <= initial_state <= capacity
    ):
        raise ValueError("initial_state must be between 0 and capacity")
    if (birth_rate + death_rate) * horizon * paths > 2_000_000:
        raise ValueError("requested birth-death experiment is too large")

    rng = random.Random(seed)
    occupancy = [0.0] * (capacity + 1)
    sample_series: list[dict[str, Any]] = []
    birth_count = 0
    death_count = 0
    series_truncated = False

    for path_index in range(paths):
        time = 0.0
        state = initial_state
        record_path = path_index < 5
        times = [time]
        states = [state]
        path_truncated = False
        while time < horizon:
            up_rate = birth_rate if state < capacity else 0.0
            down_rate = death_rate if state > 0 else 0.0
            leaving_rate = up_rate + down_rate
            holding_time = rng.expovariate(leaving_rate)
            next_time = min(time + holding_time, horizon)
            occupancy[state] += next_time - time
            if time + holding_time > horizon:
                time = horizon
                break

            time = next_time
            if rng.random() < up_rate / leaving_rate:
                state += 1
                birth_count += 1
            else:
                state -= 1
                death_count += 1
            if record_path and len(times) <= MAX_RECORDED_TRANSITIONS:
                times.append(time)
                states.append(state)
            elif record_path:
                path_truncated = True

        if record_path:
            if path_truncated:
                times.append(horizon)
                states.append(state)
                series_truncated = True
            sample_series.append(
                _step_series(times, states, horizon, f"path {path_index + 1}")
            )

    total_time = horizon * paths
    empirical = [value / total_time for value in occupancy]
    stationary = _birth_death_stationary(birth_rate, death_rate, capacity)
    generator: list[list[float]] = []
    for state in range(capacity + 1):
        row = [0.0] * (capacity + 1)
        if state < capacity:
            row[state + 1] = birth_rate
        if state > 0:
            row[state - 1] = death_rate
        row[state] = -sum(row)
        generator.append(row)

    empirical_mean = sum(
        state * probability for state, probability in enumerate(empirical)
    )
    theoretical_mean = sum(
        state * probability for state, probability in enumerate(stationary)
    )
    return {
        "topic": "birth_death",
        "model": "finite_birth_death",
        "parameters": {
            "birth_rate": birth_rate,
            "death_rate": death_rate,
            "capacity": capacity,
            "horizon": horizon,
            "paths": paths,
            "initial_state": initial_state,
            "seed": seed,
        },
        "generator_matrix": generator,
        "empirical_state_probabilities": [round(value, 6) for value in empirical],
        "stationary_distribution": [round(value, 6) for value in stationary],
        "empirical_mean_state": round(empirical_mean, 6),
        "theoretical_mean_state": round(theoretical_mean, 6),
        "l1_error": round(
            sum(abs(a - b) for a, b in zip(empirical, stationary, strict=True)),
            6,
        ),
        "birth_count": birth_count,
        "death_count": death_count,
        "series_truncated": series_truncated,
        "series": sample_series,
        "chart": {"x_label": "time", "y_label": "state", "step": "post"},
    }
