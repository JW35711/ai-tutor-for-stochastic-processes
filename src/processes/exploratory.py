"""Executable tools for the two path-dependent exploratory modules."""

from __future__ import annotations

import math
import random
import statistics
from typing import Any

from .simulations import _compress_series, _positive_int


NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _self_avoiding_path(
    max_steps: int, rng: random.Random
) -> tuple[list[tuple[int, int]], bool]:
    path = [(0, 0)]
    visited = {(0, 0)}
    for _ in range(max_steps):
        x, y = path[-1]
        available = [
            (x + dx, y + dy)
            for dx, dy in NEIGHBOURS
            if (x + dx, y + dy) not in visited
        ]
        if not available:
            return path, True
        next_site = rng.choice(available)
        path.append(next_site)
        visited.add(next_site)
    return path, False


def simulate_self_avoiding_walk(
    max_steps: int = 1_000,
    runs: int = 1_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Repeat growing self-avoiding walks and record true trapping events."""

    max_steps = _positive_int(max_steps, "max_steps", 20_000)
    runs = _positive_int(runs, "runs", 10_000)
    if max_steps * runs > 3_000_000:
        raise ValueError("requested self-avoiding-walk experiment is too large")

    rng = random.Random(seed)
    trapped_lengths: list[int] = []
    trapped_distances: list[float] = []
    unfinished_runs = 0
    sample_path: list[tuple[int, int]] = []
    sample_trapped = False
    for run in range(runs):
        path, trapped = _self_avoiding_path(max_steps, rng)
        if run == 0:
            sample_path = path
            sample_trapped = trapped
        if trapped:
            trapped_lengths.append(len(path) - 1)
            x, y = path[-1]
            trapped_distances.append(math.hypot(x, y))
        else:
            unfinished_runs += 1

    visited = set(sample_path)
    nearest_neighbour = all(
        abs(x2 - x1) + abs(y2 - y1) == 1
        for (x1, y1), (x2, y2) in zip(sample_path, sample_path[1:])
    )
    return {
        "topic": "self_avoiding_walk",
        "parameters": {"max_steps": max_steps, "runs": runs, "seed": seed},
        "trapped_runs": len(trapped_lengths),
        "unfinished_runs": unfinished_runs,
        "trapping_rate": round(len(trapped_lengths) / runs, 6),
        "average_stopping_length": (
            round(sum(trapped_lengths) / len(trapped_lengths), 6)
            if trapped_lengths
            else None
        ),
        "median_stopping_length": (
            round(float(statistics.median(trapped_lengths)), 6)
            if trapped_lengths
            else None
        ),
        "average_final_distance": (
            round(sum(trapped_distances) / len(trapped_distances), 6)
            if trapped_distances
            else None
        ),
        "sample_completed_steps": len(sample_path) - 1,
        "sample_trapped": sample_trapped,
        "sample_self_avoiding": len(visited) == len(sample_path),
        "sample_nearest_neighbour": nearest_neighbour,
        "stopping_lengths": trapped_lengths[:500],
        "series": [
            {
                "name": "sample path",
                "x": _compress_series([point[0] for point in sample_path]),
                "values": _compress_series([point[1] for point in sample_path]),
            }
        ],
        "chart": {"x_label": "x", "y_label": "y"},
    }


def _coalescing_run(
    circle_size: int,
    particles: int,
    max_steps: int,
    rng: random.Random,
) -> tuple[list[int], list[int], int | None]:
    positions = set(rng.sample(range(circle_size), particles))
    initial_positions = sorted(positions)
    cluster_counts = [len(positions)]
    for step in range(1, max_steps + 1):
        if len(positions) == 1:
            return initial_positions, cluster_counts, step - 1
        old_position = rng.choice(sorted(positions))
        direction = rng.choice((-1, 1))
        new_position = (old_position + direction) % circle_size
        positions.remove(old_position)
        positions.add(new_position)
        cluster_counts.append(len(positions))
    if len(positions) == 1:
        return initial_positions, cluster_counts, max_steps
    return initial_positions, cluster_counts, None


def simulate_coalescing_particles(
    circle_size: int = 12,
    particles: int = 9,
    runs: int = 500,
    max_steps: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate spatially coalescing particle clusters on a finite circle."""

    circle_size = _positive_int(circle_size, "circle_size", 500)
    particles = _positive_int(particles, "particles", circle_size)
    runs = _positive_int(runs, "runs", 5_000)
    max_steps = _positive_int(max_steps, "max_steps", 100_000)
    if particles > circle_size:
        raise ValueError("particles must not exceed circle_size")
    if runs * max_steps > 5_000_000:
        raise ValueError("requested coalescing-particle experiment is too large")

    rng = random.Random(seed)
    completion_times: list[int] = []
    unfinished_runs = 0
    sample_initial: list[int] = []
    sample_counts: list[int] = []
    sample_time: int | None = None
    for run in range(runs):
        initial, counts, completion_time = _coalescing_run(
            circle_size, particles, max_steps, rng
        )
        if run == 0:
            sample_initial = initial
            sample_counts = counts
            sample_time = completion_time
        if completion_time is None:
            unfinished_runs += 1
        else:
            completion_times.append(completion_time)

    monotone = all(
        later <= earlier for earlier, later in zip(sample_counts, sample_counts[1:])
    )
    return {
        "topic": "coalescing_particles",
        "parameters": {
            "circle_size": circle_size,
            "particles": particles,
            "runs": runs,
            "max_steps": max_steps,
            "seed": seed,
        },
        "completed_runs": len(completion_times),
        "unfinished_runs": unfinished_runs,
        "completion_rate": round(len(completion_times) / runs, 6),
        "average_coalescence_time": (
            round(sum(completion_times) / len(completion_times), 6)
            if completion_times
            else None
        ),
        "median_coalescence_time": (
            round(float(statistics.median(completion_times)), 6)
            if completion_times
            else None
        ),
        "minimum_coalescence_time": min(completion_times) if completion_times else None,
        "maximum_coalescence_time": max(completion_times) if completion_times else None,
        "sample_initial_positions": sample_initial,
        "sample_coalescence_time": sample_time,
        "sample_final_cluster_count": sample_counts[-1],
        "sample_cluster_count_monotone": monotone,
        "coalescence_times": completion_times[:500],
        "series": [
            {
                "name": "cluster count",
                "values": _compress_series(sample_counts),
            }
        ],
        "chart": {"x_label": "step", "y_label": "clusters", "step": "post"},
    }
