"""Traceable hybrid retrieval over curated cards and notebook Markdown cells."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PATH = ROOT / "data" / "knowledge_base.json"
DEFAULT_NOTEBOOK_ROOT = ROOT / "notebooks"


class KnowledgeBase:
    """Retrieve course evidence with transparent sparse and character scoring.

    This is intentionally local and deterministic.  It behaves as an offline
    RAG retriever, while exposing every score and exact notebook cell used in a
    response.  A hosted embedding retriever can later be added behind the same
    ``retrieve`` interface without changing the Agent workflow.
    """

    def __init__(
        self,
        path: Path = DEFAULT_KNOWLEDGE_PATH,
        notebook_root: Path = DEFAULT_NOTEBOOK_ROOT,
    ) -> None:
        self.path = path
        curated: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
        self._module_topics = {
            entry["module_id"]: entry["topic"] for entry in curated
        }
        self.entries = [dict(entry, kind="curated") for entry in curated]
        self.entries.extend(self._notebook_entries(notebook_root))
        self._term_sets = [self._terms(self._entry_text(entry)) for entry in self.entries]
        document_frequency: Counter[str] = Counter()
        for terms in self._term_sets:
            document_frequency.update(terms)
        total = len(self.entries)
        self._idf = {
            term: math.log((total + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }

    def _notebook_entries(self, notebook_root: Path) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        if not notebook_root.is_dir():
            return entries
        for path in sorted(notebook_root.glob("*.ipynb")):
            prefix = re.match(r"(\d{2})_", path.name)
            if not prefix:
                continue
            module_id = f"module{prefix.group(1)}"
            topic = self._module_topics.get(module_id)
            if not topic:
                continue
            try:
                notebook = json.loads(path.read_text("utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for cell_index, cell in enumerate(notebook.get("cells", [])):
                if cell.get("cell_type") != "markdown":
                    continue
                raw_content = "".join(cell.get("source", []))
                content = self._clean_markdown(raw_content)
                if len(content) < 100:
                    continue
                entries.append(
                    {
                        "module_id": module_id,
                        "topic": topic,
                        "title": self._title(raw_content, content, cell_index),
                        "content": content[:1400],
                        "source": f"notebooks/{path.name}#cell-{cell_index}",
                        "keywords": [],
                        "kind": "notebook_cell",
                    }
                )
        return entries

    @staticmethod
    def _clean_markdown(text: str) -> str:
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _title(raw_content: str, content: str, cell_index: int) -> str:
        heading = re.search(
            r"^\s*#{1,6}\s+(.+?)\s*$", raw_content, flags=re.MULTILINE
        )
        if heading:
            title = re.sub(r"[*_`]", "", heading.group(1)).strip(" *#")
            return title[:100]
        first_sentence = re.split(r"(?<=[.!?。！？])\s+", content, maxsplit=1)[0]
        if 5 <= len(first_sentence) <= 100:
            return first_sentence
        return f"Notebook teaching note, cell {cell_index}"

    @staticmethod
    def _terms(text: str) -> set[str]:
        lowered = text.lower().replace("‑", "-").replace("–", "-")
        terms = set(re.findall(r"[a-z0-9_]+(?:/[a-z0-9_]+)*", lowered))
        for sequence in re.findall(r"[\u4e00-\u9fff]+", lowered):
            if len(sequence) <= 3:
                terms.add(sequence)
            for width in (2, 3):
                terms.update(
                    sequence[index : index + width]
                    for index in range(max(0, len(sequence) - width + 1))
                )
        return terms

    @staticmethod
    def _entry_text(entry: dict[str, Any]) -> str:
        return " ".join(
            [
                entry["topic"],
                entry["title"],
                entry["content"],
                " ".join(entry.get("keywords", [])),
            ]
        )

    def retrieve(
        self,
        query: str,
        topic: str | None = None,
        module_id: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        query_terms = self._terms(query)
        normalized_query = " ".join(query.lower().split())
        scored: list[tuple[float, int, dict[str, Any]]] = []
        for index, (entry, entry_terms) in enumerate(
            zip(self.entries, self._term_sets, strict=True)
        ):
            if module_id and entry["module_id"] != module_id:
                continue
            overlap = query_terms & entry_terms
            sparse_score = sum(self._idf.get(term, 1.0) for term in overlap)
            topic_bonus = 6.0 if topic and entry["topic"] == topic else 0.0
            curated_bonus = 2.5 if entry["kind"] == "curated" else 0.0
            phrase_bonus = (
                4.0
                if len(normalized_query) >= 5
                and normalized_query in self._entry_text(entry).lower()
                else 0.0
            )
            score = sparse_score + topic_bonus + curated_bonus + phrase_bonus
            if score > 0:
                scored.append((score, -index, entry))
        scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
        return [
            {
                "module_id": entry["module_id"],
                "topic": entry["topic"],
                "title": entry["title"],
                "content": entry["content"],
                "source": entry["source"],
                "kind": entry["kind"],
                "score": round(score, 3),
            }
            for score, _, entry in scored[: max(1, min(limit, 10))]
        ]

    def stats(self) -> dict[str, int]:
        return {
            "entries": len(self.entries),
            "curated_cards": sum(entry["kind"] == "curated" for entry in self.entries),
            "notebook_chunks": sum(
                entry["kind"] == "notebook_cell" for entry in self.entries
            ),
        }
