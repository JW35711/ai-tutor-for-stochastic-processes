"""Traceable hybrid retrieval over curated cards and notebook Markdown cells."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter, OrderedDict
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from .embeddings import (
    EmbeddingBackend,
    LocalHashEmbedding,
    embedding_backend_from_environment,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PATH = ROOT / "data" / "knowledge_base.json"
DEFAULT_NOTEBOOK_ROOT = ROOT / "notebooks"


class KnowledgeBase:
    """Retrieve course evidence with transparent sparse and character scoring.

    This is intentionally local and deterministic.  It behaves as an offline
    RAG retriever, while exposing sparse and vector scores plus the exact
    notebook cell used in a response.
    """

    def __init__(
        self,
        path: Path = DEFAULT_KNOWLEDGE_PATH,
        notebook_root: Path = DEFAULT_NOTEBOOK_ROOT,
        embedding_backend: EmbeddingBackend | None = None,
        cache_size: int | None = None,
    ) -> None:
        self.path = path
        resolved_cache_size = (
            int(os.getenv("RAG_RETRIEVAL_CACHE_SIZE", "256"))
            if cache_size is None
            else cache_size
        )
        if resolved_cache_size < 0 or resolved_cache_size > 10_000:
            raise ValueError("retrieval cache size must be between 0 and 10000")
        self._cache_size = resolved_cache_size
        self._cache: OrderedDict[
            tuple[str, str | None, str | None, int],
            list[dict[str, Any]],
        ] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = Lock()
        curated: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
        self._module_topics = {
            entry["module_id"]: entry["topic"] for entry in curated
        }
        self.entries = [dict(entry, kind="curated") for entry in curated]
        self.entries.extend(self._notebook_entries(notebook_root))
        self._entry_texts = [self._entry_text(entry) for entry in self.entries]
        corpus_digest = hashlib.sha256()
        for entry, text in zip(self.entries, self._entry_texts, strict=True):
            corpus_digest.update(entry["module_id"].encode("utf-8"))
            corpus_digest.update(b"\0")
            corpus_digest.update(entry["source"].encode("utf-8"))
            corpus_digest.update(b"\0")
            corpus_digest.update(text.encode("utf-8"))
            corpus_digest.update(b"\0")
        self.corpus_sha256 = corpus_digest.hexdigest()
        self._term_sets = [self._terms(text) for text in self._entry_texts]
        document_frequency: Counter[str] = Counter()
        for terms in self._term_sets:
            document_frequency.update(terms)
        total = len(self.entries)
        self._idf = {
            term: math.log((total + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }
        self.embedding_fallback_reason: str | None = None
        try:
            self.embedding_backend = (
                embedding_backend or embedding_backend_from_environment()
            )
        except (ValueError, TypeError) as error:
            self.embedding_fallback_reason = str(error)
            self.embedding_backend = LocalHashEmbedding()
        try:
            self._entry_vectors = self.embedding_backend.embed_many(
                self._entry_texts
            )
        except (RuntimeError, ValueError, TypeError) as error:
            self.embedding_fallback_reason = str(error)
            self.embedding_backend = LocalHashEmbedding()
            self._entry_vectors = self.embedding_backend.embed_many(
                self._entry_texts
            )

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
        safe_limit = max(1, min(limit, 10))
        cache_key = (" ".join(query.casefold().split()), topic, module_id, safe_limit)
        if self._cache_size:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    self._cache_hits += 1
                    self._cache.move_to_end(cache_key)
                    return deepcopy(cached)
                self._cache_misses += 1
        query_terms = self._terms(query)
        normalized_query = " ".join(query.lower().split())
        try:
            query_vector = self.embedding_backend.embed_many([query])[0]
        except (RuntimeError, ValueError, TypeError) as error:
            self.embedding_fallback_reason = str(error)
            query_vector = []
        scored: list[
            tuple[float, int, dict[str, Any], float, float, float]
        ] = []
        for index, (entry, entry_terms, entry_vector) in enumerate(
            zip(
                self.entries,
                self._term_sets,
                self._entry_vectors,
                strict=True,
            )
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
            dense_score = (
                max(0.0, sum(a * b for a, b in zip(query_vector, entry_vector)))
                if query_vector
                else 0.0
            )
            bonus_score = topic_bonus + curated_bonus + phrase_bonus
            score = sparse_score + 5.0 * dense_score + bonus_score
            if score > 0:
                scored.append(
                    (
                        score,
                        -index,
                        entry,
                        sparse_score,
                        dense_score,
                        bonus_score,
                    )
                )
        scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
        results = [
            {
                "module_id": entry["module_id"],
                "topic": entry["topic"],
                "title": entry["title"],
                "content": entry["content"],
                "source": entry["source"],
                "kind": entry["kind"],
                "score": round(score, 3),
                "score_breakdown": {
                    "sparse": round(sparse_score, 3),
                    "vector": round(dense_score, 4),
                    "bonuses": round(bonus_score, 3),
                },
                "embedding_backend": self.embedding_backend.name,
                "corpus_sha256": self.corpus_sha256,
            }
            for (
                score,
                _,
                entry,
                sparse_score,
                dense_score,
                bonus_score,
            ) in scored[:safe_limit]
        ]
        if self._cache_size:
            with self._cache_lock:
                self._cache[cache_key] = deepcopy(results)
                self._cache.move_to_end(cache_key)
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        return results

    def stats(self) -> dict[str, Any]:
        with self._cache_lock:
            cache_stats = {
                "capacity": self._cache_size,
                "size": len(self._cache),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
            }
        return {
            "entries": len(self.entries),
            "curated_cards": sum(entry["kind"] == "curated" for entry in self.entries),
            "notebook_chunks": sum(
                entry["kind"] == "notebook_cell" for entry in self.entries
            ),
            "embedding_backend": self.embedding_backend.name,
            "embedding_dimension": self.embedding_backend.dimension,
            "embedding_fallback": self.embedding_fallback_reason,
            "corpus_sha256": self.corpus_sha256,
            "retrieval_cache": cache_stats,
        }
