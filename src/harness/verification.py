"""Conservative post-run checks that reuse existing domain validators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FAILURE_CATEGORIES = frozenset({
    "RETRIEVAL_INSUFFICIENT",
    "TOOL_VALIDATION_FAILED",
    "TOOL_EXECUTION_FAILED",
    "LLM_DISABLED",
    "LLM_PROVIDER_FAILED",
    "LLM_OUTPUT_REJECTED",
    "CONTEXT_COMPACTED",
    "OUT_OF_SCOPE",
})


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    failure_category: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "failure_category": self.failure_category,
            "reason": self.reason,
        }


def verify_runtime(runtime: Any, *, context_compacted: bool = False) -> VerificationResult:
    """Classify outcomes without replacing graph, provider, or tool checks."""

    intent = str(getattr(runtime, "intent", ""))
    answerability = str(getattr(runtime, "answerability_status", ""))
    tool_key = getattr(runtime, "tool_key", None)
    result = getattr(runtime, "result", {}) or {}
    llm = getattr(runtime, "llm_metadata", {}) or {}
    if intent == "unsupported" or answerability == "OUT_OF_SCOPE":
        return VerificationResult(True, "OUT_OF_SCOPE", "scope response")
    if intent == "simulation" and isinstance(result, dict) and result.get("error"):
        return VerificationResult(False, "TOOL_VALIDATION_FAILED", "tool result rejected")
    if intent == "simulation" and tool_key and not bool(getattr(runtime, "verified", False)):
        return VerificationResult(False, "TOOL_EXECUTION_FAILED", "tool did not produce a verified result")
    if intent in {"concept", "simulation"} and answerability in {"NONE", "PARTIAL"}:
        return VerificationResult(False, "RETRIEVAL_INSUFFICIENT", answerability.lower())
    status = str(llm.get("status") or "")
    if not bool(getattr(runtime, "llm_applied", False)) and status == "disabled":
        return VerificationResult(True, "LLM_DISABLED", "grounded fallback used")
    if not bool(getattr(runtime, "llm_applied", False)) and status in {"failed", "retry_exhausted", "circuit_open"}:
        return VerificationResult(True, "LLM_PROVIDER_FAILED", "grounded fallback used")
    if not bool(getattr(runtime, "llm_applied", False)) and status == "success":
        return VerificationResult(True, "LLM_OUTPUT_REJECTED", "provider output failed the existing answer contract")
    if context_compacted:
        return VerificationResult(True, "CONTEXT_COMPACTED", "bounded context applied")
    return VerificationResult(bool(getattr(runtime, "verified", False) or getattr(runtime, "answer", "")))


__all__ = ["FAILURE_CATEGORIES", "VerificationResult", "verify_runtime"]
