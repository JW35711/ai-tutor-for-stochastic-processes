#!/usr/bin/env python3
"""Measure module-scoped evidence retrieval with Hit@k and MRR."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge import KnowledgeBase  # noqa: E402


DEFAULT_CASES = ROOT / "evals" / "retrieval_cases.json"


def _matches(result: dict[str, Any], phrases: list[str]) -> bool:
    searchable = " ".join(
        str(result.get(field, ""))
        for field in ("title", "content", "source")
    ).lower()
    return any(phrase.lower() in searchable for phrase in phrases)


def evaluate(cases_path: Path = DEFAULT_CASES, limit: int = 3) -> dict[str, Any]:
    knowledge = KnowledgeBase()
    cases: list[dict[str, Any]] = json.loads(cases_path.read_text("utf-8"))
    failures: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []
    for case in cases:
        results = knowledge.retrieve(
            case["query"],
            module_id=case["module_id"],
            limit=limit,
        )
        rank = next(
            (
                index
                for index, result in enumerate(results, start=1)
                if _matches(result, case["relevant_phrases"])
            ),
            None,
        )
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        if rank is None:
            failures.append(
                {
                    "id": case["id"],
                    "module_id": case["module_id"],
                    "query": case["query"],
                    "returned_titles": [result["title"] for result in results],
                }
            )
    hits = len(cases) - len(failures)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "embedding_backend": knowledge.stats()["embedding_backend"],
        "corpus_sha256": knowledge.corpus_sha256,
        "total": len(cases),
        f"hit_at_{limit}": round(hits / len(cases), 4) if cases else 0.0,
        "mrr": round(sum(reciprocal_ranks) / len(cases), 4) if cases else 0.0,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.cases, args.limit)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", "utf-8")
    print(rendered)
    raise SystemExit(0 if not report["failures"] else 1)


if __name__ == "__main__":
    main()
