"""Execute and contract-check every registered notebook visualization target."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import StochasticTutorAgent  # noqa: E402
from src.experiments import ExperimentRegistry  # noqa: E402
from src.memory import LearnerMemory  # noqa: E402
from src.visualization_contracts import project_and_validate  # noqa: E402


REGISTRY_PATH = ROOT / "data" / "notebook_experiments.json"


def _frontend_renderers() -> set[str]:
    """Read renderer branches from the actual browser renderer code."""

    source = (ROOT / "web" / "app.js").read_text("utf-8")
    import re

    return set(re.findall(r'viz\.renderer\s*===\s*["\']([^"\']+)', source))


def _valid_source(target: dict[str, Any]) -> tuple[bool, str | None]:
    path = ROOT / str(target.get("source_notebook", ""))
    if not path.is_file():
        return False, "source notebook does not exist"
    try:
        notebook = json.loads(path.read_text("utf-8"))
    except Exception as exc:  # pragma: no cover - malformed notebooks are reported
        return False, f"source notebook is not valid JSON: {exc}"
    cell = target.get("source_cell_index")
    if not isinstance(cell, int) or cell < 0 or cell >= len(notebook.get("cells", [])):
        return False, "source cell is outside notebook"
    return True, None


def verify(*, update_registry: bool = False) -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text("utf-8"))
    frontend_renderers = _frontend_renderers()
    memory = LearnerMemory(":memory:")
    agent = StochasticTutorAgent(memory=memory)
    experiments = ExperimentRegistry()
    results: list[dict[str, Any]] = []
    cache: dict[str, dict[str, Any]] = {}
    try:
        for target in registry.get("visualizations", []):
            started = time.perf_counter()
            viz_id = str(target.get("visualization_id"))
            experiment_id = str(target.get("experiment_id"))
            errors: list[str] = []
            source_ok, source_error = _valid_source(target)
            if not source_ok:
                errors.append(source_error or "invalid source")
            experiment = experiments.get(experiment_id)
            if experiment is None:
                errors.append("experiment mapping is missing")
            engine = str(target.get("existing_tool") or (experiment or {}).get("simulation_engine") or "")
            if engine not in agent.tools:
                errors.append(f"simulation engine is unavailable: {engine}")
            if str(target.get("renderer")) not in frontend_renderers:
                errors.append(f"renderer is not reachable in web/app.js: {target.get('renderer')}")
            result: dict[str, Any] | None = None
            payload: dict[str, Any] | None = None
            if not errors:
                try:
                    result = cache.setdefault(engine, dict(agent.tools[engine]()))
                except Exception as exc:
                    errors.append(f"engine raised {type(exc).__name__}: {exc}")
            if result is not None:
                def walk(value: Any, path: str = "result") -> None:
                    if isinstance(value, float) and not math.isfinite(value):
                        errors.append(f"non-finite value at {path}")
                    elif isinstance(value, dict):
                        for key, child in value.items():
                            walk(child, f"{path}.{key}")
                    elif isinstance(value, list):
                        for index, child in enumerate(value):
                            walk(child, f"{path}[{index}]")
                walk(result)
                try:
                    payload, contract_errors = project_and_validate(target, result)
                    errors.extend(contract_errors)
                except Exception as exc:
                    errors.append(f"projection raised {type(exc).__name__}: {exc}")
            results.append(
                {
                    "visualization_id": viz_id,
                    "experiment_id": experiment_id,
                    "module_id": target.get("module_id"),
                    "renderer": target.get("renderer"),
                    "engine": engine,
                    "status": "E2E_IMPLEMENTED" if not errors else "FAILED",
                    "errors": errors,
                    "payload_keys": sorted(payload) if payload else [],
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
    finally:
        memory.close()
    passed = sum(item["status"] == "E2E_IMPLEMENTED" for item in results)
    if update_registry:
        by_id = {item["visualization_id"]: item for item in results}
        for target in registry.get("visualizations", []):
            item = by_id.get(target.get("visualization_id"))
            if item:
                target["verification_status"] = item["status"]
                target["verification_errors"] = item["errors"]
        REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry_targets": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "e2e_coverage": round(100 * passed / len(results), 2) if results else 100.0,
        "targets": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "visualization_e2e_report.json")
    parser.add_argument("--update-registry", action="store_true", help="persist per-target verification status")
    args = parser.parse_args()
    report = verify(update_registry=args.update_registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("registry_targets", "passed", "failed", "e2e_coverage")}, indent=2))
    failures = [item for item in report["targets"] if item["status"] != "E2E_IMPLEMENTED"]
    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
