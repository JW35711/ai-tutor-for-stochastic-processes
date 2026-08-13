"""Audit notebook experiments and teaching visualizations.

The notebooks are the source of truth.  This script intentionally uses the
notebook cell order and Markdown headings instead of recreating a curriculum
from implementation details.  It can either print a coverage report or write
the checked-in experiment/visualization registry.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"
CURRICULUM_PATH = ROOT / "data" / "curriculum.json"
REGISTRY_PATH = ROOT / "data" / "notebook_experiments.json"

MODULE_NOTEBOOKS = {
    f"module{number:02d}": f"{number:02d}_"
    for number in range(11)
}
VISUAL_CALLS = {
    "figure": "line",
    "plot": "line",
    "step": "step_process",
    "hist": "histogram",
    "scatter": "scatter",
    "bar": "bar_distribution",
    "barh": "bar_distribution",
    "imshow": "heatmap",
    "pcolormesh": "heatmap",
    "contour": "heatmap",
    "vlines": "event_marks",
    "fill_between": "line",
    "subplots": "multi_panel",
    "pie": "bar_distribution",
}

SUPPORTED_RENDERERS = {
    "line", "step_process", "histogram", "empirical_vs_theoretical", "multi_panel",
    "interactive", "scatter", "heatmap", "event_marks", "state_graph", "event_raster",
    "scatter_path", "thinning", "configuration", "absorption",
}


def _module_id(path: Path) -> str:
    match = re.match(r"(\d\d)_", path.name)
    if not match:
        raise ValueError(f"notebook filename must start with two digits: {path.name}")
    return f"module{int(match.group(1)):02d}"


def _heading_state(source: str, current: dict[str, str]) -> dict[str, str]:
    result = dict(current)
    for raw_line in source.splitlines():
        line = raw_line.strip()
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = re.sub(r"\s+#+$", "", match.group(2)).strip()
        if level == 1:
            result["module"] = title
        elif level == 2:
            result["section"] = title
            result["experiment"] = title if re.search(r"(?:Example|Part|Model|Task)", title, re.I) else ""
        elif level >= 3 and re.search(r"(?:Example|Task|Interactive|Solution)", title, re.I):
            result["experiment"] = title
    return result


def _markdown_context(cells: list[dict[str, Any]], index: int) -> str:
    bits: list[str] = []
    for cell in reversed(cells[:index]):
        if cell.get("cell_type") != "markdown":
            continue
        text = "".join(cell.get("source", [])).strip()
        if text:
            bits.append(text)
        if len(" ".join(bits)) >= 1800:
            break
    return " ".join(reversed(bits))[:2400]


def _following_markdown_context(cells: list[dict[str, Any]], index: int) -> str:
    bits: list[str] = []
    for cell in cells[index + 1 :]:
        if cell.get("cell_type") != "markdown":
            continue
        text = "".join(cell.get("source", [])).strip()
        if text:
            # Keep the explanatory prose, while retaining formulas and short
            # headings because they identify the intended observation.
            bits.append(text)
        if len(" ".join(bits)) >= 1800:
            break
        if bits and any(line.startswith("## ") for line in text.splitlines()):
            break
    return " ".join(bits)[:2400]


def _calls_outside_functions(source: str) -> list[tuple[str, str]]:
    """Return plotting calls, ignoring helper function definitions."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    calls: list[tuple[str, str]] = []

    def walk(node: ast.AST, inside_function: bool = False) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in VISUAL_CALLS:
                calls.append((name, VISUAL_CALLS[name]))
            if isinstance(node.func, ast.Name) and node.func.id.startswith("plot_"):
                calls.append((node.func.id, "line"))
        for child in ast.iter_child_nodes(node):
            walk(child, inside_function)

    for node in tree.body:
        walk(node)
    return calls


def _visualization_type(calls: list[tuple[str, str]], source: str, has_widget: bool) -> str:
    if has_widget or "interact(" in source:
        return "interactive"
    names = {kind for _, kind in calls}
    if "multi_panel" in names:
        return "multi_panel"
    if "histogram" in names and "line" in names:
        return "empirical_vs_theoretical"
    if "scatter" in names:
        return "scatter"
    if "step_process" in names and "event_marks" in names:
        return "step_process"
    return next(iter(names), "line")


def _concept_id(module_id: str, experiment: str, curriculum: dict[str, Any]) -> str | None:
    module = next((item for item in curriculum["modules"] if item["module_id"] == module_id), None)
    if not module:
        return None
    text = experiment.lower()
    aliases = {
        "module00": [("mean value", "m00-sample-mean"), ("increasing", "m00-law-large-numbers"), ("probability", "m00-monte-carlo-estimation"), ("convergence", "m00-law-large-numbers")],
        "module01": [("bernoulli", "m01-bernoulli-process"), ("total number", "m01-binomial-counts"), ("waiting", "m01-geometric-waiting-time"), ("discrete time", "m01-poisson-process"), ("poisson", "m01-poisson-process")],
        "module02": [("gambler", "m02-hitting-probability"), ("final position", "m02-drift-variance"), ("sample path", "m02-random-walk-increments"), ("several sample", "m02-random-walk-increments")],
        "module03": [("distribution", "m03-continuous-time-path"), ("jump rate", "m03-rate-effects"), ("sample path", "m03-continuous-time-path")],
        "module04": [("distribution", "m04-terminal-distribution"), ("approximation", "m04-brownian-scaling"), ("particle", "m04-brownian-increments"), ("price", "m04-brownian-increments"), ("sample path", "m04-brownian-increments")],
        "module05": [("stationary", "m05-stationary-distribution"), ("gambler", "m05-absorption-and-ruin"), ("absorb", "m05-absorption-and-ruin"), ("diagram", "m05-transition-matrix"), ("weather", "m05-transition-matrix"), ("path", "m05-markov-property"), ("pagerank", "m05-stationary-distribution")],
        "module06": [("birth death", "m06-birth-death-process"), ("gas station", "m06-birth-death-process"), ("holding", "m06-holding-times"), ("two state", "m06-two-state-reliability"), ("three state", "m06-generator-matrix")],
        "module07": [("hazard", "m07-survival-and-hazard"), ("survival", "m07-survival-and-hazard"), ("series", "m07-series-parallel-systems"), ("parallel", "m07-series-parallel-systems"), ("buffer", "m07-batch-buffer"), ("queue", "m07-mm1-queue")],
        "module08": [("intensity", "m08-time-varying-intensity"), ("thinning", "m08-thinning"), ("mean count", "m08-integrated-intensity"), ("event times", "m08-integrated-intensity")],
        "module09": [("ordinary random", "m09-self-avoidance"), ("stopping", "m09-stopping-length"), ("obstacle", "m09-path-trapping"), ("path", "m09-self-avoidance")],
        "module10": [("configuration", "m10-particle-motion"), ("interactive", "m10-coalescence"), ("coalescence time", "m10-coalescence-time"), ("occupied", "m10-particle-motion"), ("cluster", "m10-coalescence")],
    }
    for phrase, concept_id in aliases.get(module_id, []):
        if phrase in text:
            return concept_id
    points = module.get("knowledge_points", [])
    for point in points:
        title_terms = [term for term in re.findall(r"[a-z0-9]+", point["title"].lower()) if len(term) > 3]
        if title_terms and sum(term in text for term in title_terms) >= max(1, len(title_terms) // 2):
            return point["id"]
    return None


def detect_notebook_targets(notebook_dir: Path = NOTEBOOK_DIR) -> list[dict[str, Any]]:
    curriculum = json.loads(CURRICULUM_PATH.read_text("utf-8"))
    module_tools = {
        module["module_id"]: next(
            (point.get("simulation_tool") for point in module.get("knowledge_points", []) if point.get("simulation_tool")),
            None,
        )
        for module in curriculum["modules"]
    }
    targets: list[dict[str, Any]] = []
    for path in sorted(notebook_dir.glob("*.ipynb")):
        module_id = _module_id(path)
        notebook = json.loads(path.read_text("utf-8"))
        state = {"module": "", "section": "", "experiment": ""}
        experiment_number = 0
        for index, cell in enumerate(notebook.get("cells", [])):
            if cell.get("cell_type") == "markdown":
                state = _heading_state("".join(cell.get("source", [])), state)
                continue
            source = "".join(cell.get("source", []))
            outputs = cell.get("outputs", [])
            has_image = any("image/png" in (output.get("data") or {}) or "image/jpeg" in (output.get("data") or {}) for output in outputs)
            has_widget = any("application/vnd.jupyter.widget-view+json" in (output.get("data") or {}) for output in outputs)
            calls = _calls_outside_functions(source)
            if not calls and not has_image and not has_widget:
                continue
            # A saved image is a target even if the plotting code was edited out.
            if not calls and not has_image and not has_widget:
                continue
            experiment_number += 1
            experiment = state["experiment"] or state["section"] or state["module"]
            visual_type = _visualization_type(calls, source, has_widget)
            experiment_id = f"{module_id}-exp-{experiment_number:02d}"
            visualization_id = f"{module_id}-viz-{experiment_number:02d}"
            point = next((item for item in curriculum["modules"] if item["module_id"] == module_id for item in item.get("knowledge_points", []) if item["id"] == _concept_id(module_id, experiment, curriculum)), None)
            tool = _tool_for_experiment(module_id, experiment)
            status = _implementation_status(tool, visual_type)
            observation = _following_markdown_context(notebook["cells"], index)
            targets.append(
                {
                    "experiment_id": experiment_id,
                    "visualization_id": visualization_id,
                    "module_id": module_id,
                    "section": state["section"],
                    "concept_id": _concept_id(module_id, experiment, curriculum),
                    "title": experiment,
                    "teaching_purpose": _markdown_context(notebook["cells"], index),
                    "source_notebook": str(path.relative_to(ROOT)),
                    "source_markdown_context": _markdown_context(notebook["cells"], index),
                    "source_cell_indices": [index],
                    "simulation_engine": tool,
                    "parameters": _parameter_names(source),
                    "default_parameters": {},
                    "expected_observation": observation,
                    "theory_connection": observation,
                    "implementation_status": status,
                    "visualization": {
                        "visualization_id": visualization_id,
                        "experiment_id": experiment_id,
                        "source_notebook": str(path.relative_to(ROOT)),
                        "source_cell_index": index,
                        "output_indices": [i for i, output in enumerate(outputs) if "image/png" in (output.get("data") or {}) or "image/jpeg" in (output.get("data") or {}) or "application/vnd.jupyter.widget-view+json" in (output.get("data") or {})],
                        "title": experiment,
                        "visualization_type": visual_type,
                        "renderer": visual_type,
                        "renderer_data_requirements": _renderer_requirements(visual_type),
                        "existing_tool": tool,
                        "implementation_status": status,
                    },
                }
            )
    return targets


def _parameter_names(source: str) -> list[str]:
    return sorted(set(re.findall(r"^\s*([a-zA-Z][a-zA-Z0-9_]*)\s*=", source, re.M)))[:30]


def _renderer_requirements(renderer: str) -> list[str]:
    return {
        "line": ["x", "values", "labels"],
        "step_process": ["times", "states", "x_label", "y_label"],
        "histogram": ["samples", "bins", "x_label", "y_label"],
        "empirical_vs_theoretical": ["x", "empirical", "theoretical", "labels"],
        "multi_panel": ["panels", "panel_titles"],
        "interactive": ["state_history", "step", "controls"],
        "scatter": ["x", "y", "labels"],
        "heatmap": ["matrix", "x_label", "y_label"],
        "event_marks": ["event_times", "count_path"],
        "state_graph": ["nodes", "edges", "weights"],
    }.get(renderer, ["x", "values"])


def _tool_for_experiment(module_id: str, title: str) -> str | None:
    text = title.lower()
    if module_id == "module00": return "monte_carlo"
    if module_id == "module01": return "poisson" if any(term in text for term in ("poisson", "exponential", "continuous time")) else "bernoulli"
    if module_id == "module02": return "random_walk"
    if module_id == "module03": return "continuous_random_walk"
    if module_id == "module04": return "brownian_motion"
    if module_id == "module05": return "markov_chain"
    if module_id == "module06": return "birth_death" if any(term in text for term in ("birth death", "gas station")) else "ctmc"
    if module_id == "module07": return "buffer" if "buffer" in text else ("mm1_queue" if any(term in text for term in ("queue", "m/m/1")) else "reliability")
    if module_id == "module08": return "nhpp"
    if module_id == "module09": return "self_avoiding_walk"
    if module_id == "module10": return "coalescing_particles"
    return None


def _implementation_status(tool: str | None, visualization_type: str) -> str:
    # Registration is deliberately not execution.  The verifier adds the
    # separate ``verification_status`` field after running the real engine,
    # checking the payload contract and exercising the API/UI mapping.
    return "REGISTERED" if tool is not None else "MISSING"


def build_registry(targets: list[dict[str, Any]]) -> dict[str, Any]:
    experiments: dict[str, dict[str, Any]] = {}
    visualizations: list[dict[str, Any]] = []
    for target in targets:
        experiment = {key: value for key, value in target.items() if key != "visualization"}
        experiments[target["experiment_id"]] = experiment
        visualizations.append(target["visualization"])
    return {
        "schema_version": 1,
        "source": "actual notebook cell order and outputs",
        "notebook_visualization_targets": len(visualizations),
        "experiments": list(experiments.values()),
        "visualizations": visualizations,
    }


def audit(registry: dict[str, Any], notebook_dir: Path = NOTEBOOK_DIR) -> dict[str, Any]:
    detected = detect_notebook_targets(notebook_dir)
    detected_ids = {item["visualization_id"] for item in detected}
    registered = registry.get("visualizations", [])
    registered_ids = {item.get("visualization_id") for item in registered}
    counts = Counter(item.get("verification_status", item.get("implementation_status", "MISSING")) for item in registered)
    known_engines = {
        "monte_carlo", "bernoulli", "poisson", "random_walk",
        "continuous_random_walk", "brownian_motion", "markov_chain", "ctmc",
        "birth_death", "reliability", "buffer", "mm1_queue", "nhpp",
        "self_avoiding_walk", "coalescing_particles",
    }
    frontend_renderers = {
        "line", "step_process", "histogram", "empirical_vs_theoretical",
        "multi_panel", "interactive", "scatter", "scatter_path", "state_graph",
        "event_raster", "thinning", "configuration", "absorption", "heatmap",
        "event_marks",
    }
    by_module: dict[str, dict[str, int]] = defaultdict(lambda: {"targets": 0, "registered": 0, "implemented": 0, "partial": 0, "missing": 0})
    for item in detected:
        by_module[item["module_id"]]["targets"] += 1
    for item in registered:
        module = str(item.get("visualization_id", "module??"))[:8]
        by_module[module]["registered"] += 1
        status = str(item.get("verification_status", item.get("implementation_status", "MISSING"))).lower()
        by_module[module][status] = by_module[module].get(status, 0) + 1
    denominator = len(detected_ids) or 1
    registered_count = len(detected_ids & registered_ids)
    executable_count = sum(
        1 for item in registered
        if item.get("visualization_id") in detected_ids and item.get("existing_tool") in known_engines
    )
    renderer_count = sum(
        1 for item in registered
        if item.get("visualization_id") in detected_ids and item.get("renderer") in frontend_renderers
    )
    e2e_count = sum(
        1 for item in registered
        if item.get("visualization_id") in detected_ids and item.get("verification_status") == "E2E_IMPLEMENTED"
    )
    return {
        "total_notebook_visualization_targets": len(detected_ids),
        "registered": len(detected_ids & registered_ids),
        "implemented": e2e_count,
        "partial": counts.get("PARTIAL", 0),
        "missing": counts.get("MISSING", 0),
        "coverage_percent": round(100 * registered_count / denominator, 2) if detected_ids else 100.0,
        "registration_coverage": round(100 * registered_count / denominator, 2) if detected_ids else 100.0,
        "executable_coverage": round(100 * executable_count / denominator, 2) if detected_ids else 100.0,
        "renderer_coverage": round(100 * renderer_count / denominator, 2) if detected_ids else 100.0,
        "e2e_coverage": round(100 * e2e_count / denominator, 2) if detected_ids else 100.0,
        "unregistered_ids": sorted(detected_ids - registered_ids),
        "orphan_registered_ids": sorted(registered_ids - detected_ids),
        "by_module": dict(sorted(by_module.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write data/notebook_experiments.json")
    args = parser.parse_args()
    if args.write:
        registry = build_registry(detect_notebook_targets())
        REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", "utf-8")
    else:
        registry = json.loads(REGISTRY_PATH.read_text("utf-8"))
    print(json.dumps(audit(registry), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
