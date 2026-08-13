"""Build the checked current evaluation manifest from fresh suite reports.

The previous v1.0.0 manifest remains versioned separately. This command only
promotes reports that were generated against the same current corpus hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"evaluation report is missing: {path}")
    return json.loads(path.read_text("utf-8"))


def _suite(
    suite_id: str,
    cases_file: str,
    report: dict[str, Any],
    *,
    total: int | None = None,
    passed: int | None = None,
) -> dict[str, Any]:
    cases_path = ROOT / cases_file
    report_total = int(report.get("total", 0))
    report_passed = int(
        report.get("passed", report_total - len(report.get("failures", [])))
    )
    suite: dict[str, Any] = {
        "id": suite_id,
        "cases": int(total if total is not None else report_total),
        "passed": int(passed if passed is not None else report_passed),
        "cases_file": cases_file,
        "cases_sha256": _sha256(cases_path),
    }
    for metric in (
        "hit_at_1",
        "hit_at_3",
        "mrr",
        "structured_answer_rate",
        "kp_coverage_rate",
        "answer_success_rate",
        "false_abstention_rate",
        "average_final_evidence_chunks",
        "answerability_accuracy",
        "unsupported_answer_rate",
        "abstention_precision",
        "conflict_detection_accuracy",
        "supplementary_retrieval_success_rate",
    ):
        if metric in report:
            suite[metric] = report[metric]
    for metric in ("experiment_selection_accuracy", "parameter_extraction_accuracy", "follow_up_context_accuracy", "execution_success_rate", "renderer_success_rate"):
        if metric in report:
            suite[metric] = report[metric]
    if "e2e_coverage" in report:
        suite["e2e_coverage"] = report["e2e_coverage"]
    return suite


def _credibility_suite(report: dict[str, Any]) -> dict[str, Any]:
    """Project the hard/natural set into the unified manifest."""

    hard = report.get("hard_natural_set", {}).get("cases", {})
    cases_file = "evals/course_hard_cases.json"
    cases_path = ROOT / cases_file
    return {
        "id": "course_hard",
        "cases": int(hard.get("total", 0)),
        "passed": int(hard.get("passed", 0)),
        "cases_file": cases_file,
        "cases_sha256": _sha256(cases_path),
        "kp_coverage_rate": hard.get("kp_coverage_rate", 0.0),
        "real_routing": hard.get("real_routing", {}),
        "answerability": hard.get("answerability", {}),
        "retrieval_process": hard.get("retrieval_process", {}),
        "failure_distribution": hard.get("failure_distribution", {}),
        "baseline_minimum_passed": 98,
    }


def _holdout_suite(report: dict[str, Any]) -> dict[str, Any]:
    holdout = report.get("holdout_set", {})
    cases_file = "evals/course_holdout_cases.json"
    return {
        "id": "course_holdout",
        "cases": int(holdout.get("total", 0)),
        "passed": int(holdout.get("routing_pass", 0)),
        "cases_file": cases_file,
        "cases_sha256": _sha256(ROOT / cases_file),
        "routing_module_accuracy": holdout.get("routing_module_accuracy", 0.0),
        "routing_concept_accuracy": holdout.get("routing_concept_accuracy", 0.0),
        "retrieval": holdout.get("retrieval", {}),
        "answerability": holdout.get("answerability", {}),
        "informational": True,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    main = _load(args.main)
    retrieval = _load(args.retrieval)
    pedagogy = _load(args.pedagogy)
    safety = _load(args.safety)
    answerability = _load(args.answerability)
    course_coverage = _load(args.course_coverage)
    experiment_routing = _load(args.experiment_routing)
    visualization_e2e = _load(args.visualization_e2e)
    credibility = _load(args.credibility) if args.credibility else None
    corpus_hashes = {
        str(report.get("corpus_sha256"))
        for report in (main, retrieval, pedagogy, safety, answerability, experiment_routing, course_coverage)
    }
    if args.credibility:
        corpus_hashes.add(str(credibility.get("corpus_sha256")))
    if len(corpus_hashes) != 1 or "None" in corpus_hashes:
        raise ValueError(f"evaluation reports do not share one corpus SHA: {sorted(corpus_hashes)}")

    multi = main.get("multi_turn") or {}
    suites = [
        _suite("single_turn", "evals/cases.json", main),
        _suite(
            "multi_turn",
            "evals/conversations.json",
            multi,
            total=multi.get("total"),
            passed=multi.get("passed"),
        ),
        _suite("retrieval", "evals/retrieval_cases.json", retrieval),
        _suite("pedagogy", "evals/pedagogy_cases.json", pedagogy),
        _suite("safety", "evals/safety_cases.json", safety),
        _suite("answerability", "evals/answerability_cases.json", answerability),
        _suite("course_coverage", "evals/course_coverage_cases.json", course_coverage),
        _suite("experiment_routing", "evals/experiment_routing_cases.json", experiment_routing),
        _suite("visualization_e2e", "data/notebook_experiments.json", visualization_e2e, total=visualization_e2e.get("registry_targets"), passed=visualization_e2e.get("passed")),
    ]
    if args.credibility:
        suites.append(_credibility_suite(credibility))
        suites.append(_holdout_suite(credibility))
    total = sum(suite["cases"] for suite in suites)
    passed = sum(suite["passed"] for suite in suites)
    return {
        "version": 4 if credibility else 3,
        "baseline_id": "current-rag-credibility" if credibility else "current-evidence-sufficiency",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corpus_sha256": next(iter(corpus_hashes)),
        "total": total,
        "passed": passed,
        "suites": suites,
        "historical_baseline": {
            "id": "v1.0.0-pre-answerability",
            "manifest_file": "data/evaluation_manifest_v1.0.0.json",
            "total": 109,
            "passed": 109,
            "note": "Historical result; not the current baseline.",
        },
        "current_baseline_note": "Current score includes deterministic governance, structured course coverage, the 129-case development credibility set, and the 32-case independent holdout. Historical scores are never substituted for this report.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--pedagogy", type=Path, required=True)
    parser.add_argument("--safety", type=Path, required=True)
    parser.add_argument("--answerability", type=Path, required=True)
    parser.add_argument("--course-coverage", type=Path, required=True)
    parser.add_argument("--experiment-routing", type=Path, required=True)
    parser.add_argument("--visualization-e2e", type=Path, required=True)
    parser.add_argument("--credibility", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "evaluation_manifest.json",
    )
    args = parser.parse_args()
    manifest = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({k: manifest[k] for k in ("baseline_id", "corpus_sha256", "total", "passed")}, indent=2))
    if args.credibility:
        hard_suite = next(suite for suite in manifest["suites"] if suite["id"] == "course_hard")
        if hard_suite["passed"] < int(hard_suite.get("baseline_minimum_passed", 0)):
            raise SystemExit("course hard-set result regressed below its frozen baseline")
        non_hard = [suite for suite in manifest["suites"] if suite["id"] != "course_hard"]
        if any(suite["passed"] != suite["cases"] for suite in non_hard if not suite.get("informational")):
            raise SystemExit("a deterministic core evaluation suite contains failing cases")
    elif manifest["passed"] != manifest["total"]:
        raise SystemExit("current evaluation baseline contains failing cases")


if __name__ == "__main__":
    main()
