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
        "hit_at_3",
        "mrr",
        "structured_answer_rate",
        "answerability_accuracy",
        "unsupported_answer_rate",
        "abstention_precision",
        "conflict_detection_accuracy",
        "supplementary_retrieval_success_rate",
    ):
        if metric in report:
            suite[metric] = report[metric]
    return suite


def build(args: argparse.Namespace) -> dict[str, Any]:
    main = _load(args.main)
    retrieval = _load(args.retrieval)
    pedagogy = _load(args.pedagogy)
    safety = _load(args.safety)
    answerability = _load(args.answerability)
    corpus_hashes = {
        str(report.get("corpus_sha256"))
        for report in (main, retrieval, pedagogy, safety, answerability)
    }
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
    ]
    total = sum(suite["cases"] for suite in suites)
    passed = sum(suite["passed"] for suite in suites)
    return {
        "version": 3,
        "baseline_id": "current-evidence-sufficiency",
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
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--pedagogy", type=Path, required=True)
    parser.add_argument("--safety", type=Path, required=True)
    parser.add_argument("--answerability", type=Path, required=True)
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
    if manifest["passed"] != manifest["total"]:
        raise SystemExit("current evaluation baseline contains failing cases")


if __name__ == "__main__":
    main()
