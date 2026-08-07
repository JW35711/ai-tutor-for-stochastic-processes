"""Reliability, buffer and queueing tools used by Module 07."""

from __future__ import annotations

import math
import random
from typing import Any

from .simulations import (
    _compress_series,
    _positive_float,
    _positive_int,
    _step_series,
)


def analyze_reliability_system(
    failure_rate_1: float = 0.8,
    failure_rate_2: float = 1.2,
    horizon: float = 6.0,
    samples: int = 5_000,
    points: int = 120,
    seed: int = 42,
) -> dict[str, Any]:
    """Compare two-component series and parallel exponential systems."""

    failure_rate_1 = _positive_float(failure_rate_1, "failure_rate_1", 100.0)
    failure_rate_2 = _positive_float(failure_rate_2, "failure_rate_2", 100.0)
    horizon = _positive_float(horizon, "horizon", 1_000.0)
    samples = _positive_int(samples, "samples", 100_000)
    points = _positive_int(points, "points", 500)
    if points < 2:
        raise ValueError("points must be at least 2")
    if samples * points > 3_000_000:
        raise ValueError("requested reliability experiment is too large")

    rng = random.Random(seed)
    component_1 = [rng.expovariate(failure_rate_1) for _ in range(samples)]
    component_2 = [rng.expovariate(failure_rate_2) for _ in range(samples)]
    series_lifetimes = [min(a, b) for a, b in zip(component_1, component_2, strict=True)]
    parallel_lifetimes = [max(a, b) for a, b in zip(component_1, component_2, strict=True)]
    grid = [index * horizon / (points - 1) for index in range(points)]

    empirical_series = [
        sum(lifetime > time for lifetime in series_lifetimes) / samples
        for time in grid
    ]
    empirical_parallel = [
        sum(lifetime > time for lifetime in parallel_lifetimes) / samples
        for time in grid
    ]
    theory_series = [
        math.exp(-(failure_rate_1 + failure_rate_2) * time) for time in grid
    ]
    theory_parallel = [
        1.0
        - (1.0 - math.exp(-failure_rate_1 * time))
        * (1.0 - math.exp(-failure_rate_2 * time))
        for time in grid
    ]
    empirical_series_mean = sum(series_lifetimes) / samples
    empirical_parallel_mean = sum(parallel_lifetimes) / samples
    theory_series_mean = 1.0 / (failure_rate_1 + failure_rate_2)
    theory_parallel_mean = (
        1.0 / failure_rate_1
        + 1.0 / failure_rate_2
        - 1.0 / (failure_rate_1 + failure_rate_2)
    )
    return {
        "topic": "reliability",
        "parameters": {
            "failure_rate_1": failure_rate_1,
            "failure_rate_2": failure_rate_2,
            "horizon": horizon,
            "samples": samples,
            "points": points,
            "seed": seed,
        },
        "empirical_series_mean_lifetime": round(empirical_series_mean, 6),
        "theoretical_series_mean_lifetime": round(theory_series_mean, 6),
        "empirical_parallel_mean_lifetime": round(empirical_parallel_mean, 6),
        "theoretical_parallel_mean_lifetime": round(theory_parallel_mean, 6),
        "series_max_curve_error": round(
            max(abs(a - b) for a, b in zip(empirical_series, theory_series, strict=True)),
            6,
        ),
        "parallel_max_curve_error": round(
            max(
                abs(a - b)
                for a, b in zip(empirical_parallel, theory_parallel, strict=True)
            ),
            6,
        ),
        "series": [
            {"name": "series simulation", "x": grid, "values": empirical_series},
            {"name": "series theory", "x": grid, "values": theory_series},
            {"name": "parallel simulation", "x": grid, "values": empirical_parallel},
            {"name": "parallel theory", "x": grid, "values": theory_parallel},
        ],
        "chart": {"x_label": "time", "y_label": "reliability"},
    }


def _geometric_batch(probability: float, rng: random.Random) -> int:
    if probability == 1.0:
        return 0
    return math.floor(math.log1p(-rng.random()) / math.log1p(-probability))


def simulate_batch_buffer(
    steps: int = 120,
    arrival_probability: float = 0.6,
    paths: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate a discrete buffer with geometric batch arrivals and unit service."""

    steps = _positive_int(steps, "steps", 100_000)
    paths = _positive_int(paths, "paths", 5_000)
    arrival_probability = float(arrival_probability)
    if not math.isfinite(arrival_probability) or not 0.0 < arrival_probability <= 1.0:
        raise ValueError("arrival_probability must be in (0, 1]")
    if steps * paths > 2_000_000:
        raise ValueError("requested buffer experiment is too large")

    rng = random.Random(seed)
    final_sizes: list[int] = []
    maximum_sizes: list[int] = []
    arrivals: list[int] = []
    sample_series: list[dict[str, Any]] = []
    for path_index in range(paths):
        queue = 0
        path = [queue]
        path_arrivals = 0
        for _ in range(steps):
            arrival = _geometric_batch(arrival_probability, rng)
            path_arrivals += arrival
            queue += arrival
            if queue > 0:
                queue -= 1
            path.append(queue)
        final_sizes.append(queue)
        maximum_sizes.append(max(path))
        arrivals.append(path_arrivals)
        if path_index < 5:
            sample_series.append(
                {"name": f"path {path_index + 1}", "values": _compress_series(path)}
            )

    theoretical_arrival_mean = (1.0 - arrival_probability) / arrival_probability
    return {
        "topic": "buffer",
        "parameters": {
            "steps": steps,
            "arrival_probability": arrival_probability,
            "paths": paths,
            "seed": seed,
        },
        "empirical_arrivals_per_slot": round(sum(arrivals) / (steps * paths), 6),
        "theoretical_arrivals_per_slot": round(theoretical_arrival_mean, 6),
        "theoretical_drift_when_busy": round(theoretical_arrival_mean - 1.0, 6),
        "empirical_mean_final_buffer": round(sum(final_sizes) / paths, 6),
        "empirical_mean_max_buffer": round(sum(maximum_sizes) / paths, 6),
        "final_sizes": final_sizes[:200],
        "series": sample_series,
        "chart": {"x_label": "slot", "y_label": "buffer size", "step": "post"},
    }


def simulate_mm1_queue(
    arrival_rate: float = 0.9,
    service_rate: float = 1.0,
    horizon: float = 2_000.0,
    paths: int = 20,
    max_state: int = 50,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate M/M/1 paths and compare stable queues with geometric theory."""

    arrival_rate = _positive_float(arrival_rate, "arrival_rate", 1_000.0)
    service_rate = _positive_float(service_rate, "service_rate", 1_000.0)
    horizon = _positive_float(horizon, "horizon", 100_000.0)
    paths = _positive_int(paths, "paths", 1_000)
    max_state = _positive_int(max_state, "max_state", 1_000)
    if (arrival_rate + service_rate) * horizon * paths > 3_000_000:
        raise ValueError("requested M/M/1 experiment is too large")

    rng = random.Random(seed)
    time_in_state = [0.0] * (max_state + 1)
    overflow_time = 0.0
    weighted_state_time = 0.0
    sample_series: list[dict[str, Any]] = []
    maximum_observed = 0

    for path_index in range(paths):
        time = 0.0
        state = 0
        times = [time]
        states = [state]
        while time < horizon:
            total_rate = arrival_rate + (service_rate if state > 0 else 0.0)
            holding_time = rng.expovariate(total_rate)
            next_time = min(time + holding_time, horizon)
            duration = next_time - time
            weighted_state_time += state * duration
            if state <= max_state:
                time_in_state[state] += duration
            else:
                overflow_time += duration
            if time + holding_time > horizon:
                break

            time = next_time
            if rng.random() < arrival_rate / total_rate:
                state += 1
            else:
                state -= 1
            maximum_observed = max(maximum_observed, state)
            times.append(time)
            states.append(state)

        if path_index < 5:
            sample_series.append(
                _step_series(times, states, horizon, f"path {path_index + 1}")
            )

    total_time = horizon * paths
    empirical = [value / total_time for value in time_in_state]
    traffic_intensity = arrival_rate / service_rate
    stable = traffic_intensity < 1.0
    theoretical = (
        [(1.0 - traffic_intensity) * traffic_intensity**state for state in range(max_state + 1)]
        if stable
        else None
    )
    empirical_mean = weighted_state_time / total_time
    return {
        "topic": "mm1_queue",
        "parameters": {
            "arrival_rate": arrival_rate,
            "service_rate": service_rate,
            "horizon": horizon,
            "paths": paths,
            "max_state": max_state,
            "seed": seed,
        },
        "traffic_intensity": round(traffic_intensity, 6),
        "stable": stable,
        "empirical_state_probabilities": [round(value, 6) for value in empirical],
        "theoretical_state_probabilities": (
            [round(value, 6) for value in theoretical] if theoretical else None
        ),
        "empirical_mean_customers": round(empirical_mean, 6),
        "theoretical_mean_customers": (
            round(traffic_intensity / (1.0 - traffic_intensity), 6)
            if stable
            else None
        ),
        "displayed_state_l1_error": (
            round(sum(abs(a - b) for a, b in zip(empirical, theoretical, strict=True)), 6)
            if theoretical
            else None
        ),
        "overflow_time_fraction": round(overflow_time / total_time, 6),
        "maximum_observed_state": maximum_observed,
        "series": sample_series,
        "chart": {"x_label": "time", "y_label": "customers", "step": "post"},
    }
