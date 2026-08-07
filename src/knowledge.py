"""Small source-aware retrieval layer for the first Agent MVP."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_KNOWLEDGE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"
)


class KnowledgeBase:
    """Retrieve course notes with transparent lexical scoring and citations."""

    def __init__(self, path: Path = DEFAULT_KNOWLEDGE_PATH) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower()))

    def retrieve(
        self,
        query: str,
        topic: str | None = None,
        module_id: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        query_tokens = self._tokens(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self.entries:
            entry_tokens = self._tokens(
                " ".join(
                    [
                        entry["topic"],
                        entry["title"],
                        entry["content"],
                        " ".join(entry.get("keywords", [])),
                    ]
                )
            )
            overlap = len(query_tokens & entry_tokens)
            topic_bonus = 8 if topic and entry["topic"] == topic else 0
            module_bonus = 20 if module_id and entry["module_id"] == module_id else 0
            score = overlap + topic_bonus + module_bonus
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "module_id": entry["module_id"],
                "topic": entry["topic"],
                "title": entry["title"],
                "content": entry["content"],
                "source": entry["source"],
                "score": score,
            }
            for score, entry in scored[:limit]
        ]
