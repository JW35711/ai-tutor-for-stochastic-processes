"""Deterministic, bounded learner context for one Tutor execution.

The harness keeps only compact identifiers, validated parameters, assessed
state, source locators and a few recent turn summaries.  It deliberately does
not serialize raw simulation arrays, full chat history, prompts, credentials,
or arbitrary private profile fields.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping


_DROP_KEY_RE = re.compile(
    r"(?:array|arrays|samples|series|values|matrix|path|paths|raw|prompt|secret|token|password|credential)",
    re.I,
)
_SAFE_SCALARS = (str, int, float, bool)


@dataclass(frozen=True)
class ContextBudget:
    """Hard limits for the compact context snapshot."""

    max_recent_turns: int = 4
    max_evidence_refs: int = 8
    max_items: int = 24
    max_chars: int = 6000
    max_value_chars: int = 320


@dataclass(frozen=True)
class ContextSnapshot:
    """Serializable context plus compaction accounting."""

    stable: dict[str, Any] = field(default_factory=dict)
    assessed_state: dict[str, Any] = field(default_factory=dict)
    recent_turns: tuple[dict[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    items_dropped: int = 0
    before_chars: int = 0
    after_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stable": dict(self.stable),
            "assessed_state": dict(self.assessed_state),
            "recent_turns": [dict(item) for item in self.recent_turns],
            "evidence_refs": list(self.evidence_refs),
            "items_dropped": self.items_dropped,
            "before_chars": self.before_chars,
            "after_chars": self.after_chars,
        }


def _value(value: Any, *, budget: ContextBudget) -> Any:
    """Keep primitives and compact nested mappings while dropping payloads."""

    if isinstance(value, _SAFE_SCALARS):
        if isinstance(value, str):
            return value[: budget.max_value_chars]
        return value
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if _DROP_KEY_RE.search(name):
                continue
            compact = _value(item, budget=budget)
            if compact is not None:
                output[name] = compact
        return output
    # Lists are useful for compact assessed misconceptions, but arbitrary
    # arrays and simulation outputs are intentionally excluded.
    if isinstance(value, (list, tuple)):
        if len(value) > 8:
            return None
        compact_items = [_value(item, budget=budget) for item in value]
        return [item for item in compact_items if item is not None]
    return None


def _object_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    if hasattr(raw, "__dict__"):
        return dict(vars(raw))
    return {}


def _turns(raw: Mapping[str, Any], budget: ContextBudget) -> list[dict[str, str]]:
    candidates = raw.get("recent_turns") or raw.get("turns") or raw.get("conversation")
    if candidates is None and raw.get("previous_turn"):
        candidates = [raw["previous_turn"]]
    if not isinstance(candidates, (list, tuple)):
        return []
    selected: list[dict[str, str]] = []
    for item in list(candidates)[-budget.max_recent_turns :]:
        mapping = _object_mapping(item)
        question = str(mapping.get("question") or mapping.get("user") or "").strip()
        answer = str(mapping.get("answer") or mapping.get("assistant") or "").strip()
        if question or answer:
            selected.append({
                "question": question[: budget.max_value_chars],
                "answer": answer[: budget.max_value_chars],
            })
    return selected


def _source_refs(raw: Mapping[str, Any], budget: ContextBudget) -> list[str]:
    sources = raw.get("sources") or raw.get("supporting_source_locators") or []
    refs: list[str] = []
    if isinstance(sources, (list, tuple)):
        for item in sources:
            locator = item.get("source") if isinstance(item, Mapping) else item
            if locator and str(locator) not in refs:
                refs.append(str(locator)[: budget.max_value_chars])
            if len(refs) >= budget.max_evidence_refs:
                break
    return refs


def compact_context(raw: Any, budget: ContextBudget | None = None) -> ContextSnapshot:
    """Build a deterministic bounded snapshot without model/tokenizer calls.

    Priority is stable experiment context, module/concept, assessed state,
    recent relevant turns, then old context/evidence references.  Applying the
    function twice to its own snapshot is idempotent.
    """

    budget = budget or ContextBudget()
    mapping = _object_mapping(raw)
    # A snapshot is already compact.  Returning its normalized representation
    # makes repeated compaction deterministic and idempotent.
    if {"stable", "assessed_state", "recent_turns", "evidence_refs"}.issubset(mapping):
        stable = _value(mapping.get("stable"), budget=budget) or {}
        assessed = _value(mapping.get("assessed_state"), budget=budget) or {}
        turns = _turns({"recent_turns": mapping.get("recent_turns")}, budget)
        refs = _source_refs({"evidence_refs": mapping.get("evidence_refs")}, budget)
        encoded = json.dumps(
            {"stable": stable, "assessed_state": assessed, "recent_turns": turns, "evidence_refs": refs},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return ContextSnapshot(
            stable=stable,
            assessed_state=assessed,
            recent_turns=tuple(turns),
            evidence_refs=tuple(refs),
            items_dropped=int(mapping.get("items_dropped", 0) or 0),
            before_chars=len(encoded),
            after_chars=len(encoded),
        )
    before = len(json.dumps(mapping, ensure_ascii=False, default=str))

    stable_keys = (
        "session_id", "learner_id", "active_experiment_id", "active_visualization_id",
        "active_parameters", "latest_result_reference", "latest_result_summary",
        "module_id", "concept_id", "requested_concept_id", "experiment_id",
    )
    stable: dict[str, Any] = {}
    for key in stable_keys:
        compact = _value(mapping.get(key), budget=budget)
        if compact not in (None, "", {}, []):
            stable[key] = compact

    assessed: dict[str, Any] = {}
    for key in ("assessment_result", "current_concept_mastery", "prerequisite_mastery", "learning_note"):
        compact = _value(mapping.get(key), budget=budget)
        if compact not in (None, "", {}, []):
            assessed[key] = compact

    turns = _turns(mapping, budget)
    refs = _source_refs(mapping, budget)
    dropped = max(0, len(mapping) - len(stable) - len(assessed) - len(turns) - len(refs))

    def encoded() -> str:
        return json.dumps(
            {"stable": stable, "assessed_state": assessed, "recent_turns": turns, "evidence_refs": refs},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    # Remove the least important material first until both budgets hold.
    while len(encoded()) > budget.max_chars or len(stable) + len(assessed) + len(turns) + len(refs) > budget.max_items:
        if refs:
            refs.pop()
        elif turns:
            turns.pop(0)
        elif assessed:
            assessed.pop(next(reversed(assessed)))
        elif stable:
            # Preserve the key but trim the least important long value before
            # dropping identifiers such as the active experiment.
            long_key = max(
                (key for key, value in stable.items() if isinstance(value, str)),
                key=lambda key: len(stable[key]),
                default=None,
            )
            if long_key is None:
                stable.pop(next(reversed(stable)))
            elif len(stable[long_key]) > 48:
                stable[long_key] = stable[long_key][: max(16, len(stable[long_key]) // 2)]
            else:
                stable.pop(long_key)
        else:
            break
        dropped += 1
    after = len(encoded())
    return ContextSnapshot(
        stable=stable,
        assessed_state=assessed,
        recent_turns=tuple(turns),
        evidence_refs=tuple(refs),
        items_dropped=dropped,
        before_chars=before,
        after_chars=after,
    )


__all__ = ["ContextBudget", "ContextSnapshot", "compact_context"]
