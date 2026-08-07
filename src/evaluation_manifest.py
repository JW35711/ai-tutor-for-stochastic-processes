"""Load the checked evaluation summary shown by the API and dashboard."""

from __future__ import annotations

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
    if not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("corpus_sha256", ""))):
        raise ValueError("evaluation manifest needs a corpus SHA-256")
    return manifest
