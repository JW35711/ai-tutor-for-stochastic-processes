"""Stable fingerprints for verified simulation evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def execution_sha256(
    *,
    module_id: str,
    tool: str,
    parameters: dict[str, Any],
    result: dict[str, Any],
    corpus_sha256: str,
) -> str:
    payload = {
        "module_id": module_id,
        "tool": tool,
        "parameters": parameters,
        "result": result,
        "corpus_sha256": corpus_sha256,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
