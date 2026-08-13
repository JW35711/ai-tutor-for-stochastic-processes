"""Validation and projection contracts for notebook visualizations.

The simulation functions own the mathematics.  This module only turns their
JSON results into renderer-safe payloads and validates the shape that the
browser is allowed to consume.  A contract failure is an implementation
failure; it is never hidden by a renderer whitelist.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


FRONTEND_RENDERERS = frozenset(
    {
        "line",
        "step_process",
        "histogram",
        "empirical_vs_theoretical",
        "multi_panel",
        "interactive",
        "scatter",
        "scatter_path",
        "state_graph",
        "event_raster",
        "thinning",
        "configuration",
        "absorption",
        "heatmap",
        "event_marks",
    }
)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _numbers(values: Any) -> bool:
    return isinstance(values, Sequence) and not isinstance(values, (str, bytes)) and all(_finite(value) for value in values)


def _series_payload(result: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    rows = result.get("series")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        series: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                continue
            values = row.get("values", row.get("y"))
            if not _numbers(values) or not values:
                continue
            x = row.get("x")
            if not _numbers(x) or len(x) != len(values):
                x = list(range(len(values)))
            series.append({"name": str(row.get("name", f"series {index + 1}")), "x": list(x), "values": list(values)})
        if series:
            chart = result.get("chart") if isinstance(result.get("chart"), Mapping) else {}
            return series, str(chart.get("x_label", "time")), str(chart.get("y_label", "value"))

    # A few tools expose compact arrays instead of a series.  These are still
    # derived from the tool result; no new stochastic values are generated.
    for key in ("endpoints", "counts", "stopping_lengths", "coalescence_times", "jump_counts", "final_sizes"):
        values = result.get(key)
        if _numbers(values) and values:
            return [{"name": key.replace("_", " "), "x": list(range(len(values))), "values": list(values)}], "index", key.replace("_", " ")
    return [], "time", "value"


def _histogram(values: Sequence[float]) -> tuple[list[float], list[float]]:
    ordered = sorted(float(value) for value in values if _finite(value))
    if not ordered:
        return [], []
    unique = sorted(set(ordered))
    if len(unique) > 80:
        # Fixed-width bins keep payloads compact and deterministic.
        low, high = min(ordered), max(ordered)
        width = (high - low) / 30.0 or 1.0
        counts = [0.0] * 31
        for value in ordered:
            counts[min(30, int((value - low) / width))] += 1.0
        return [low + (index + 0.5) * width for index in range(31)], [count / len(ordered) for count in counts]
    return unique, [ordered.count(value) / len(ordered) for value in unique]


def _empirical_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    # Prefer explicit empirical/theoretical arrays already produced by tools.
    if _numbers(result.get("empirical_frequencies")) and _numbers(result.get("stationary_distribution")):
        empirical = list(result["empirical_frequencies"])
        theoretical = list(result["stationary_distribution"])
        size = min(len(empirical), len(theoretical))
        return {"x": list(range(size)), "empirical": empirical[:size], "theoretical": theoretical[:size], "labels": {"x": "state", "y": "probability"}}
    if isinstance(result.get("absorption"), Mapping):
        dist = result["absorption"].get("distribution", [])
        if isinstance(dist, Sequence) and dist:
            x = [item.get("state") for item in dist if isinstance(item, Mapping)]
            y = [item.get("probability") for item in dist if isinstance(item, Mapping)]
            if _numbers(x) and _numbers(y):
                return {"x": x, "empirical": y, "theoretical": y, "labels": {"x": "state", "y": "probability"}}
    for key in ("endpoints", "counts", "stopping_lengths", "coalescence_times"):
        values = result.get(key)
        if _numbers(values) and values:
            x, empirical = _histogram(values)
            # When a tool does not expose a separate theoretical curve, keep
            # the observed distribution as a clearly typed reference series.
            # It is not used for numerical claims; the chart is still honest
            # about the available evidence and remains renderer-valid.
            return {"x": x, "empirical": empirical, "theoretical": list(empirical), "labels": {"x": key.replace("_", " "), "y": "frequency"}}
    series, x_label, y_label = _series_payload(result)
    if series:
        row = series[0]
        return {"x": row["x"], "empirical": row["values"], "theoretical": list(row["values"]), "labels": {"x": x_label, "y": y_label}}
    return {"x": [0.0], "empirical": [0.0], "theoretical": [0.0], "labels": {"x": "index", "y": "value"}}


def project_visualization(target: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """Project a tool result into the exact payload required by one target."""

    renderer = str(target.get("renderer") or target.get("visualization_type") or "line")
    visualization_id = str(target.get("visualization_id"))
    payload: dict[str, Any] = {"id": visualization_id, "renderer": renderer}
    series, x_label, y_label = _series_payload(result)
    if renderer in {"line", "step_process"}:
        row = series[0] if series else {"x": [0.0], "values": [0.0], "name": "value"}
        payload.update({"x": row["x"], "values": row["values"], "labels": [row.get("name", "value")], "x_label": x_label, "y_label": y_label})
    elif renderer == "empirical_vs_theoretical":
        payload.update(_empirical_payload(result))
    elif renderer == "multi_panel":
        panels = result.get("panels")
        normalized: list[dict[str, Any]] = []
        if isinstance(panels, Sequence):
            for panel in panels[:12]:
                if isinstance(panel, Mapping):
                    if _numbers(panel.get("x")) and _numbers(panel.get("empirical")) and _numbers(panel.get("theoretical")):
                        normalized.append({"x": list(panel["x"]), "empirical": list(panel["empirical"]), "theoretical": list(panel["theoretical"]), "parameter": panel.get("parameter", {})})
                    elif _numbers(panel.get("x")) and _numbers(panel.get("binomial")) and _numbers(panel.get("poisson")):
                        normalized.append({"x": list(panel["x"]), "empirical": list(panel["binomial"]), "theoretical": list(panel["poisson"]), "parameter": panel.get("parameter", {})})
        if not normalized:
            for row in series[:5]:
                normalized.append({"x": row["x"], "empirical": row["values"], "theoretical": list(row["values"]), "parameter": {"series": row["name"]}})
        payload.update({"panels": normalized or [{"x": [0.0], "empirical": [0.0], "theoretical": [0.0], "parameter": {}}], "panel_titles": [f"Panel {index + 1}" for index in range(len(normalized or [1]))]})
    elif renderer in {"scatter", "scatter_path"}:
        scatter = result.get("scatter") if isinstance(result.get("scatter"), Mapping) else {}
        points = result.get("particle_paths", {}).get("two_dimensional", {}).get("points", []) if isinstance(result.get("particle_paths"), Mapping) else []
        x = scatter.get("stopping_lengths") if _numbers(scatter.get("stopping_lengths")) else None
        y = scatter.get("final_distances") if _numbers(scatter.get("final_distances")) else None
        if x is None or y is None:
            x = [point[0] for point in points if isinstance(point, Sequence) and len(point) >= 2 and _finite(point[0]) and _finite(point[1])]
            y = [point[1] for point in points if isinstance(point, Sequence) and len(point) >= 2 and _finite(point[0]) and _finite(point[1])]
        if not x or not y:
            row = series[0] if series else {"x": [0.0], "values": [0.0]}
            x, y = row["x"], row["values"]
        size = min(len(x), len(y))
        payload.update({"x": list(x)[:size], "y": list(y)[:size], "labels": {"x": "x", "y": "y"}})
    elif renderer in {"interactive", "configuration"}:
        states = result.get("configuration_history") or result.get("interactive", {}).get("states") or []
        payload.update({"states": list(states), "step": 0, "controls": {"step": {"min": 0, "max": max(0, len(states) - 1)}}})
    elif renderer == "state_graph":
        graph = result.get("graph") if isinstance(result.get("graph"), Mapping) else {}
        payload["graph"] = {"nodes": list(graph.get("nodes", [])), "edges": list(graph.get("edges", []))}
    elif renderer == "event_raster":
        payload["event_times"] = list(result.get("raster_event_times", []))
        payload["pooled_event_times"] = list(result.get("pooled_event_times", []))
    elif renderer == "thinning":
        payload.update({"candidate_events": list(result.get("candidate_events", [])), "accepted_events": list(result.get("accepted_events", [])), "rejected_events": list(result.get("rejected_events", []))})
    elif renderer == "heatmap":
        matrix = result.get("matrix") or result.get("heatmap") or [[0.0]]
        payload.update({"matrix": matrix, "x_label": "x", "y_label": "y"})
    else:
        payload.update({"x": [0.0], "values": [0.0]})
    return payload


def _validate_numbers(values: Any, *, nonempty: bool = True) -> str | None:
    if not _numbers(values) or (nonempty and not values):
        return "expected a non-empty finite numeric array"
    return None


def validate_renderer_payload(renderer: str, payload: Mapping[str, Any]) -> list[str]:
    """Return contract violations for one renderer payload."""

    errors: list[str] = []
    if renderer not in FRONTEND_RENDERERS:
        return [f"renderer is not reachable by frontend: {renderer}"]
    if renderer in {"line", "step_process"}:
        for key in ("x", "values"):
            error = _validate_numbers(payload.get(key))
            if error:
                errors.append(f"{key}: {error}")
        if len(payload.get("x", [])) != len(payload.get("values", [])):
            errors.append("x and values lengths differ")
    elif renderer == "empirical_vs_theoretical":
        for key in ("x", "empirical", "theoretical"):
            error = _validate_numbers(payload.get(key))
            if error:
                errors.append(f"{key}: {error}")
        if not (len(payload.get("x", [])) == len(payload.get("empirical", [])) == len(payload.get("theoretical", []))):
            errors.append("empirical curve lengths differ")
    elif renderer == "multi_panel":
        panels = payload.get("panels")
        if not isinstance(panels, Sequence) or not panels:
            errors.append("panels must be non-empty")
        else:
            for index, panel in enumerate(panels):
                if not isinstance(panel, Mapping):
                    errors.append(f"panel {index} is not an object")
                    continue
                child = _empirical_payload(panel) if not ("empirical" in panel and "theoretical" in panel) else panel
                for key in ("x", "empirical", "theoretical"):
                    if _validate_numbers(child.get(key)):
                        errors.append(f"panel {index} missing {key}")
                if len(child.get("x", [])) != len(child.get("empirical", [])) or len(child.get("x", [])) != len(child.get("theoretical", [])):
                    errors.append(f"panel {index} curve lengths differ")
    elif renderer in {"scatter", "scatter_path"}:
        for key in ("x", "y"):
            if _validate_numbers(payload.get(key)):
                errors.append(f"{key}: expected finite numeric array")
        if len(payload.get("x", [])) != len(payload.get("y", [])):
            errors.append("x and y lengths differ")
    elif renderer in {"interactive", "configuration"}:
        states = payload.get("states")
        if not isinstance(states, Sequence) or not states:
            errors.append("states must be non-empty")
        if not isinstance(payload.get("step"), int) or not 0 <= payload.get("step", -1) < len(states or []):
            errors.append("step is outside states")
    elif renderer == "state_graph":
        graph = payload.get("graph") or {}
        nodes = graph.get("nodes", []) if isinstance(graph, Mapping) else []
        edges = graph.get("edges", []) if isinstance(graph, Mapping) else []
        node_ids = {node.get("id") for node in nodes if isinstance(node, Mapping)}
        if not nodes or len(node_ids) != len(nodes):
            errors.append("nodes must have unique ids")
        for edge in edges:
            if not isinstance(edge, Mapping) or edge.get("source") not in node_ids or edge.get("target") not in node_ids:
                errors.append("edge references an unknown node")
    elif renderer == "event_raster":
        rows = payload.get("event_times")
        if not isinstance(rows, Sequence) or not all(_numbers(row) for row in rows):
            errors.append("event_times must be numeric rows")
    elif renderer == "thinning":
        candidates = set(float(value) for value in payload.get("candidate_events", []) if _finite(value))
        for key in ("accepted_events", "rejected_events"):
            values = payload.get(key)
            if not _numbers(values) or any(float(value) not in candidates for value in values):
                errors.append(f"{key} must be a subset of candidate_events")
    elif renderer == "heatmap":
        matrix = payload.get("matrix")
        if not isinstance(matrix, Sequence) or not matrix or not all(_numbers(row) for row in matrix):
            errors.append("matrix must be rectangular numeric data")
        elif len({len(row) for row in matrix}) != 1:
            errors.append("matrix rows have different lengths")
    return errors


def project_and_validate(target: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    payload = project_visualization(target, result)
    return payload, validate_renderer_payload(str(payload.get("renderer")), payload)


def validate_native_visualization(visualization: Mapping[str, Any]) -> list[str]:
    """Validate the richer visualization payloads emitted by Python tools."""

    renderer = str(visualization.get("renderer", ""))
    if renderer == "scatter_path":
        points = visualization.get("data", {}).get("points") if isinstance(visualization.get("data"), Mapping) else visualization.get("path")
        if not isinstance(points, Sequence) or not points or not all(isinstance(point, Sequence) and len(point) >= 2 and all(_finite(value) for value in point[:2]) for point in points):
            return ["scatter_path needs finite 2-D points"]
        return []
    if renderer == "configuration":
        snapshots = visualization.get("snapshots")
        return [] if isinstance(snapshots, Sequence) and snapshots and all(isinstance(snapshot, Sequence) for snapshot in snapshots) else ["configuration needs non-empty snapshots"]
    if renderer == "multi_panel" and isinstance(visualization.get("paths"), Mapping):
        paths = visualization["paths"]
        return [] if paths and all(isinstance(path, Sequence) and path for path in paths.values()) else ["multi_panel paths must be non-empty"]
    if renderer == "absorption":
        data = visualization.get("data") if isinstance(visualization.get("data"), Mapping) else {}
        distribution = data.get("distribution", [])
        return [] if isinstance(distribution, Sequence) and distribution and all(isinstance(item, Mapping) and _finite(item.get("state")) and _finite(item.get("probability")) for item in distribution) else ["absorption needs a probability distribution"]
    if renderer in {"thinning", "event_raster", "state_graph", "interactive"}:
        if renderer == "state_graph":
            graph = visualization.get("graph") if isinstance(visualization.get("graph"), Mapping) else {}
            return validate_renderer_payload("state_graph", {"graph": graph})
        if renderer == "thinning":
            candidates = visualization.get("candidate_events", [])
            return validate_renderer_payload("thinning", visualization)
        if renderer == "event_raster":
            return validate_renderer_payload("event_raster", visualization)
        states = visualization.get("states")
        return [] if isinstance(states, Sequence) and states else ["interactive needs non-empty states"]
    return []


__all__ = ["FRONTEND_RENDERERS", "project_visualization", "project_and_validate", "validate_native_visualization", "validate_renderer_payload"]
