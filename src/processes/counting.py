"""Counting-process tools for Bernoulli and nonhomogeneous Poisson models."""

from __future__ import annotations

import math
import random
from typing import Any

from .simulations import _compress_series, _positive_float, _positive_int, _probability


def _geometric_wait(probability: float, rng: random.Random) -> int:
    if probability == 1.0:
        return 1
    return math.floor(math.log1p(-rng.random()) / math.log1p(-probability)) + 1


def simulate_bernoulli_process(
    slots: int = 100,
    probability: float = 0.3,
    paths: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate Bernoulli counting paths and geometric waiting times."""

    slots = _positive_int(slots, "slots", 50_000)
    probability = _probability(probability, "probability", allow_zero=False)
    paths = _positive_int(paths, "paths", 5_000)
    if slots * paths > 2_000_000:
        raise ValueError("requested Bernoulli experiment is too large")

    rng = random.Random(seed)
    counts: list[int] = []
    waits: list[int] = []
    sample_series: list[dict[str, Any]] = []
    for path_index in range(paths):
        count = 0
        counting_path = [0]
        for _ in range(slots):
            count += rng.random() < probability
            counting_path.append(count)
        counts.append(count)
        waits.append(_geometric_wait(probability, rng))
        if path_index < 5:
            sample_series.append(
                {
                    "name": f"path {path_index + 1}",
                    "values": _compress_series(counting_path),
                }
            )

    empirical_mean = sum(counts) / paths
    empirical_variance = sum((value - empirical_mean) ** 2 for value in counts) / paths
    empirical_wait = sum(waits) / paths
    theoretical_mean = slots * probability
    theoretical_variance = slots * probability * (1.0 - probability)
    comparison_ps = [0.1, 0.3, 0.6]
    comparison_slots = min(slots, 240)
    comparison_panels: list[dict[str, Any]] = []
    comparison_rng = random.Random(seed + 11)
    for panel_probability in comparison_ps:
        panel_counts = [
            sum(comparison_rng.random() < panel_probability for _ in range(comparison_slots))
            for _ in range(min(paths, 400))
        ]
        support = list(range(comparison_slots + 1))
        empirical = [panel_counts.count(k) / len(panel_counts) for k in support]
        exact = [
            math.comb(comparison_slots, k) * panel_probability**k * (1 - panel_probability) ** (comparison_slots - k)
            for k in support
        ]
        waiting_support = list(range(1, 61))
        waiting_exact = [(1 - panel_probability) ** (k - 1) * panel_probability for k in waiting_support]
        waiting_samples = [_geometric_wait(panel_probability, comparison_rng) for _ in range(min(paths, 400))]
        waiting_empirical = [waiting_samples.count(k) / len(waiting_samples) for k in waiting_support]
        comparison_panels.append({
            "parameter": {"probability": panel_probability},
            "count_distribution": {"x": support, "empirical": empirical, "theoretical": exact},
            "waiting_time_distribution": {"x": waiting_support, "empirical": waiting_empirical, "theoretical": waiting_exact},
        })
    return {
        "topic": "bernoulli",
        "parameters": {
            "slots": slots,
            "probability": probability,
            "paths": paths,
            "seed": seed,
        },
        "empirical_count_mean": round(empirical_mean, 6),
        "theoretical_count_mean": round(theoretical_mean, 6),
        "empirical_count_variance": round(empirical_variance, 6),
        "theoretical_count_variance": round(theoretical_variance, 6),
        "empirical_waiting_mean": round(empirical_wait, 6),
        "theoretical_waiting_mean": round(1.0 / probability, 6),
        "counts": counts[:200],
        "waiting_times": waits[:200],
        "series": sample_series,
        "panels": comparison_panels,
        "visualizations": [
            {"id": "module01-viz-04", "renderer": "multi_panel", "panels": [p["count_distribution"] for p in comparison_panels]},
            {"id": "module01-viz-07", "renderer": "multi_panel", "panels": [p["waiting_time_distribution"] for p in comparison_panels]},
        ],
        "chart": {"x_label": "slot", "y_label": "number of events", "step": "post"},
    }


def _gaussian_intensity(
    time: float,
    base_rate: float,
    peak_rate: float,
    peak_center: float,
    peak_width: float,
) -> float:
    z = (time - peak_center) / peak_width
    return base_rate + peak_rate * math.exp(-0.5 * z * z)


def _integrated_gaussian_intensity(
    horizon: float,
    base_rate: float,
    peak_rate: float,
    peak_center: float,
    peak_width: float,
) -> float:
    scale = math.sqrt(2.0) * peak_width
    gaussian_area = (
        peak_rate
        * peak_width
        * math.sqrt(math.pi / 2.0)
        * (
            math.erf((horizon - peak_center) / scale)
            - math.erf(-peak_center / scale)
        )
    )
    return base_rate * horizon + gaussian_area


def simulate_nhpp_thinning(
    horizon: float = 24.0,
    base_rate: float = 2.0,
    peak_rate: float = 6.0,
    peak_center: float = 13.0,
    peak_width: float = 4.0,
    paths: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate a Gaussian-peak nonhomogeneous Poisson process by thinning."""

    horizon = _positive_float(horizon, "horizon", 1_000.0)
    base_rate = float(base_rate)
    peak_rate = float(peak_rate)
    peak_center = float(peak_center)
    peak_width = _positive_float(peak_width, "peak_width", 1_000.0)
    paths = _positive_int(paths, "paths", 5_000)
    if any(
        not math.isfinite(value) or value < 0.0
        for value in (base_rate, peak_rate, peak_center)
    ):
        raise ValueError("base_rate, peak_rate and peak_center must be non-negative")
    if peak_center > horizon:
        raise ValueError("peak_center must lie inside the observation interval")
    dominating_rate = base_rate + peak_rate
    if dominating_rate <= 0.0:
        raise ValueError("the intensity must be positive somewhere")
    if dominating_rate * horizon * paths > 3_000_000:
        raise ValueError("requested thinning experiment is too large")

    rng = random.Random(seed)
    accepted_counts: list[int] = []
    candidate_total = 0
    accepted_total = 0
    sample_series: list[dict[str, Any]] = []
    first_candidates: list[float] = []
    first_accepted: list[float] = []
    first_rejected: list[float] = []
    raster_event_times: list[list[float]] = []
    pooled_event_times: list[float] = []

    for path_index in range(paths):
        time = 0.0
        candidates: list[float] = []
        accepted: list[float] = []
        rejected: list[float] = []
        while True:
            time += rng.expovariate(dominating_rate)
            if time > horizon:
                break
            candidates.append(time)
            local_rate = _gaussian_intensity(
                time, base_rate, peak_rate, peak_center, peak_width
            )
            if rng.random() <= local_rate / dominating_rate:
                accepted.append(time)
            else:
                rejected.append(time)

        candidate_total += len(candidates)
        accepted_total += len(accepted)
        accepted_counts.append(len(accepted))
        if path_index < 8:
            raster_event_times.append(accepted[:])
        if len(pooled_event_times) < 2_000:
            pooled_event_times.extend(accepted[: max(0, 2_000 - len(pooled_event_times))])
        if path_index == 0:
            first_candidates = candidates
            first_accepted = accepted
            first_rejected = rejected
        if path_index < 5:
            x_values = [0.0, *accepted, horizon]
            count_values = list(range(len(accepted) + 1)) + [len(accepted)]
            sample_series.append(
                {
                    "name": f"path {path_index + 1}",
                    "x": _compress_series(x_values),
                    "values": _compress_series(count_values),
                }
            )

    empirical_mean = sum(accepted_counts) / paths
    theoretical_mean = _integrated_gaussian_intensity(
        horizon, base_rate, peak_rate, peak_center, peak_width
    )
    grid = [index * horizon / 120 for index in range(121)]
    intensity_values = [
        _gaussian_intensity(time, base_rate, peak_rate, peak_center, peak_width)
        for time in grid
    ]
    # Bernoulli-to-Poisson convergence panels from the notebook.
    convergence_panels: list[dict[str, Any]] = []
    for n_value in (10, 50, 200):
        m = int(n_value * min(horizon, 2.0))
        p = min(1.0, base_rate / max(n_value, 1))
        support = list(range(0, 21))
        binomial = [
            math.comb(m, k) * p**k * (1 - p) ** (m - k) if k <= m else 0.0
            for k in support
        ]
        poisson = [
            math.exp(-base_rate * min(horizon, 2.0))
            * (base_rate * min(horizon, 2.0)) ** k
            / math.factorial(k)
            for k in support
        ]
        convergence_panels.append({"parameter": {"n": n_value}, "x": support, "binomial": binomial, "poisson": poisson})
    return {
        "topic": "nonhomogeneous_poisson",
        "parameters": {
            "horizon": horizon,
            "base_rate": base_rate,
            "peak_rate": peak_rate,
            "peak_center": peak_center,
            "peak_width": peak_width,
            "paths": paths,
            "seed": seed,
        },
        "dominating_rate": round(dominating_rate, 6),
        "empirical_mean_count": round(empirical_mean, 6),
        "theoretical_mean_count": round(theoretical_mean, 6),
        "absolute_error": round(abs(empirical_mean - theoretical_mean), 6),
        "candidate_count": candidate_total,
        "accepted_count": accepted_total,
        "acceptance_rate": round(accepted_total / candidate_total, 6)
        if candidate_total
        else 0.0,
        "first_candidate_times": [round(value, 6) for value in first_candidates],
        "first_accepted_times": [round(value, 6) for value in first_accepted],
        "first_rejected_times": [round(value, 6) for value in first_rejected],
        "intensity_grid": [round(value, 6) for value in grid],
        "intensity_values": [round(value, 6) for value in intensity_values],
        "raster_event_times": raster_event_times,
        "pooled_event_times": [round(value, 6) for value in pooled_event_times],
        "series": sample_series,
        "candidate_events": [{"time": value, "accepted": value in first_accepted} for value in first_candidates],
        "accepted_events": first_accepted,
        "rejected_events": first_rejected,
        "intensity_curve": {"x": grid, "values": intensity_values},
        "panels": convergence_panels,
        "visualizations": [
            {"id": "module08-viz-03", "renderer": "thinning", "candidate_events": first_candidates, "accepted_events": first_accepted, "rejected_events": first_rejected, "intensity_curve": {"x": grid, "values": intensity_values}},
            {"id": "module08-viz-05", "renderer": "event_raster", "event_times": raster_event_times, "pooled_event_times": pooled_event_times, "intensity_curve": {"x": grid, "values": intensity_values}},
        ],
        "chart": {"x_label": "time", "y_label": "N(t)", "step": "post"},
    }
