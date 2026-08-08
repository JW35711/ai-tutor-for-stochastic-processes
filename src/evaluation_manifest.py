"""Load the checked evaluation summary shown by the API and dashboard."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent / "data" / "evaluation_manifest.json"
)


def load_evaluation_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text("utf-8"))
    suites = manifest.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("evaluation manifest needs at least one suite")
    total = sum(int(suite["cases"]) for suite in suites)
    passed = sum(int(suite["passed"]) for suite in suites)
    if manifest.get("total") != total or manifest.get("passed") != passed:
        raise ValueError("evaluation manifest totals do not match its suites")
    if passed > total:
        raise ValueError("evaluation manifest passed count exceeds total")
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", str(suite.get("cases_sha256", "")))
        for suite in suites
    ):
        raise ValueError("every evaluation suite needs a case-set SHA-256")
    repository_root = path.resolve().parent.parent
    for suite in suites:
        relative = suite.get("cases_file")
        if not isinstance(relative, str) or not relative:
            raise ValueError("every evaluation suite needs a case file")
        case_path = (repository_root / relative).resolve()
        if repository_root not in case_path.parents or not case_path.is_file():
            raise ValueError("evaluation case file is missing or outside repository")
        actual_sha256 = hashlib.sha256(case_path.read_bytes()).hexdigest()
        if actual_sha256 != suite["cases_sha256"]:
            raise ValueError(f"evaluation case hash mismatch: {suite['id']}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("corpus_sha256", ""))):
        raise ValueError("evaluation manifest needs a corpus SHA-256")
    return manifest
