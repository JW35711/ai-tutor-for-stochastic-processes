"""Traceable hybrid retrieval over curated cards and notebook Markdown cells."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter, OrderedDict
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from .config import RuntimeConfig, env_float, env_int, runtime_config
from .embeddings import (
    EmbeddingBackend,
    LocalHashEmbedding,
    embedding_backend_from_environment,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PATH = ROOT / "data" / "knowledge_base.json"
DEFAULT_NOTEBOOK_ROOT = ROOT / "notebooks"
DEFAULT_REFERENCE_CHUNKS_PATH = ROOT / "data" / "reference_chunks.json"
DEFAULT_TEXTBOOK_CHUNKS_PATH = ROOT / "artifacts" / "textbook_chunks.json"


class KnowledgeBase:
    """Retrieve course evidence with transparent sparse and character scoring.

    This is intentionally local and deterministic.  It behaves as an offline
    RAG retriever, while exposing sparse and vector scores plus the exact
    notebook cell used in a response.
    """

    QUERY_TRANSLATIONS: tuple[tuple[str, str], ...] = (
        (
            "样本量",
            "sample size repetitions increasing N convergence fluctuations standard error",
        ),
        (
            "无记忆",
            "memoryless property geometric waiting time first event simulation",
        ),
        ("终点位置", "distribution final position number of right steps"),
        ("跳跃率", "effect of the jump rate lambda different values"),
        ("固定时刻", "fixed time distribution not a sample path B(T)"),
        (
            "吸收马尔可夫链",
            "absorbing Markov chain gambler ruin histogram distribution of absorption times over many simulations boundary",
        ),
        ("停留时间", "holding time exponential distribution generator"),
        ("风险率", "hazard rate constant exponential distribution life length"),
        (
            "平均累计事件数",
            "many simulations mean count average count integrated intensity",
        ),
        (
            "已访问格点",
            "visited set same lattice site Markov property self avoidance",
        ),
        (
            "簇数量",
            "cluster count coalescence does not occur at every step stay same decrease",
        ),
    )
    QUERY_STOPWORDS = frozenset(
        {"what", "is", "the", "a", "an", "of", "and", "explain", "please", "how", "does"}
    )

    def __init__(
        self,
        path: Path = DEFAULT_KNOWLEDGE_PATH,
        notebook_root: Path = DEFAULT_NOTEBOOK_ROOT,
        reference_chunks_path: Path = DEFAULT_REFERENCE_CHUNKS_PATH,
        textbook_chunks_path: Path = DEFAULT_TEXTBOOK_CHUNKS_PATH,
        embedding_backend: EmbeddingBackend | None = None,
        cache_size: int | None = None,
        embedding_failure_cooldown: float | None = None,
        clock: Callable[[], float] | None = None,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.config = config or runtime_config()
        self.path = path
        resolved_cache_size = (
            env_int(
                "RAG_RETRIEVAL_CACHE_SIZE",
                256,
                minimum=0,
                maximum=10_000,
            )
            if cache_size is None
            else cache_size
        )
        if resolved_cache_size < 0 or resolved_cache_size > 10_000:
            raise ValueError("retrieval cache size must be between 0 and 10000")
        self._cache_size = resolved_cache_size
        self._cache: OrderedDict[
            tuple[str, str | None, str | None, str | None, int],
            list[dict[str, Any]],
        ] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = Lock()
        resolved_cooldown = (
            env_float(
                "RAG_EMBEDDING_FAILURE_COOLDOWN_SECONDS",
                60,
                minimum=0,
                maximum=3600,
            )
            if embedding_failure_cooldown is None
            else float(embedding_failure_cooldown)
        )
        if not math.isfinite(resolved_cooldown) or not 0 <= resolved_cooldown <= 3600:
            raise ValueError(
                "embedding failure cooldown must be between 0 and 3600 seconds"
            )
        self._embedding_failure_cooldown = resolved_cooldown
        self._clock = clock or time.monotonic
        self._embedding_circuit_lock = Lock()
        self._embedding_retry_after = 0.0
        self._embedding_request_in_flight = False
        self._embedding_query_failures = 0
        self._embedding_query_skips = 0
        curated: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
        self._module_topics = {
            entry["module_id"]: entry["topic"] for entry in curated
        }
        self.entries = [dict(entry, kind="curated") for entry in curated]
        self.entries.extend(self._notebook_entries(notebook_root))
        self.entries.extend(self._reference_entries(reference_chunks_path))
        baseline_entries = list(self.entries)
        self.entries.extend(self._textbook_entries(textbook_chunks_path))
        self._entry_texts = [self._entry_text(entry) for entry in self.entries]
        self.evaluation_corpus_sha256 = self._corpus_sha256(baseline_entries)
        corpus_digest = hashlib.sha256()
        for entry, text in zip(self.entries, self._entry_texts, strict=True):
            corpus_digest.update(str(entry.get("module_id") or "").encode("utf-8"))
            corpus_digest.update(b"\0")
            corpus_digest.update(entry["source"].encode("utf-8"))
            corpus_digest.update(b"\0")
            corpus_digest.update(text.encode("utf-8"))
            corpus_digest.update(b"\0")
        self.corpus_sha256 = corpus_digest.hexdigest()
        self._term_sets = [self._terms(text) for text in self._entry_texts]
        self._title_term_sets = [
            self._terms(entry.get("title", "")) for entry in self.entries
        ]
        document_frequency: Counter[str] = Counter()
        for terms in self._term_sets:
            document_frequency.update(terms)
        total = len(self.entries)
        self._idf = {
            term: math.log((total + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }
        self.embedding_fallback_reason: str | None = None
        self._index_fallback_reason: str | None = None
        try:
            self.embedding_backend = (
                embedding_backend or embedding_backend_from_environment()
            )
        except (ValueError, TypeError) as error:
            self.embedding_fallback_reason = str(error)
            self._index_fallback_reason = str(error)
            self.embedding_backend = LocalHashEmbedding()
        try:
            self._entry_vectors = self.embedding_backend.embed_many(
                self._entry_texts
            )
        except (RuntimeError, ValueError, TypeError) as error:
            self.embedding_fallback_reason = str(error)
            self._index_fallback_reason = str(error)
            self.embedding_backend = LocalHashEmbedding()
            self._entry_vectors = self.embedding_backend.embed_many(
                self._entry_texts
            )

    def _corpus_sha256(self, entries: list[dict[str, Any]]) -> str:
        digest = hashlib.sha256()
        for entry in entries:
            digest.update(str(entry.get("module_id") or "").encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(entry.get("source") or "").encode("utf-8"))
            digest.update(b"\0")
            digest.update(self._entry_text(entry).encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _query_vector(self, query: str) -> tuple[list[float], str]:
        """Embed one query without repeatedly blocking on a failed provider."""

        if self.embedding_backend.name == "local_hash":
            return self.embedding_backend.embed_many([query])[0], "hybrid"

        now = self._clock()
        with self._embedding_circuit_lock:
            if now < self._embedding_retry_after:
                self._embedding_query_skips += 1
                return [], "sparse_fallback"
            if self._embedding_request_in_flight:
                self._embedding_query_skips += 1
                return [], "sparse_fallback"
            self._embedding_request_in_flight = True

        try:
            vectors = self.embedding_backend.embed_many([query])
            if len(vectors) != 1:
                raise RuntimeError(
                    "embedding endpoint returned an unexpected query row count"
                )
            query_vector = vectors[0]
            expected_dimension = (
                len(self._entry_vectors[0]) if self._entry_vectors else 0
            )
            if len(query_vector) != expected_dimension:
                raise RuntimeError("query embedding dimension differs from the index")
        except (RuntimeError, ValueError, TypeError) as error:
            with self._embedding_circuit_lock:
                self.embedding_fallback_reason = str(error)
                self._embedding_query_failures += 1
                self._embedding_retry_after = (
                    self._clock() + self._embedding_failure_cooldown
                )
                self._embedding_request_in_flight = False
            return [], "sparse_fallback"
        except BaseException:
            with self._embedding_circuit_lock:
                self._embedding_request_in_flight = False
            raise

        with self._embedding_circuit_lock:
            self.embedding_fallback_reason = self._index_fallback_reason
            self._embedding_retry_after = 0.0
            self._embedding_request_in_flight = False
        return query_vector, "hybrid"

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

    def _reference_entries(self, reference_chunks_path: Path) -> list[dict[str, Any]]:
        """Load reviewed course-reference chunks with explicit source locators."""

        if not reference_chunks_path.is_file():
            return []
        try:
            chunks = json.loads(reference_chunks_path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        entries: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            module_id = chunk.get("module_id")
            topic = chunk.get("topic")
            title = chunk.get("title")
            content = chunk.get("content")
            source = chunk.get("source")
            if (
                module_id not in self._module_topics
                or topic != self._module_topics[module_id]
                or not isinstance(title, str)
                or not isinstance(content, str)
                or not isinstance(source, str)
            ):
                continue
            clean_content = self._clean_markdown(content)
            if len(clean_content) < 80:
                continue
            keywords = chunk.get("keywords", [])
            entries.append(
                {
                    "module_id": module_id,
                    "topic": topic,
                    "title": title[:100],
                    "content": clean_content[:1400],
                    "source": source,
                    "keywords": keywords if isinstance(keywords, list) else [],
                    "kind": "reference_chunk",
                    "reference_index": index,
                }
            )
        return entries

    def _textbook_entries(self, textbook_chunks_path: Path) -> list[dict[str, Any]]:
        """Load locally generated PDF chunks without making the PDF a dependency."""

        if not textbook_chunks_path.is_file():
            return []
        try:
            chunks = json.loads(textbook_chunks_path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        entries: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                continue
            text = chunk.get("text")
            source = chunk.get("source")
            module_id = chunk.get("module_id")
            concept_id = chunk.get("concept_id")
            if not isinstance(text, str) or not isinstance(source, str):
                continue
            content = self._clean_markdown(text)
            if not content:
                continue
            if module_id not in self._module_topics:
                module_id = None
            if not isinstance(concept_id, str):
                concept_id = None
            title = chunk.get("title")
            entries.append(
                {
                    "module_id": module_id,
                    "concept_id": concept_id,
                    "topic": self._module_topics.get(module_id, "textbook"),
                    "title": title[:120] if isinstance(title, str) else source,
                    "content": content,
                    "source": source,
                    "source_type": "textbook",
                    "page": chunk.get("page"),
                    "content_type": chunk.get("content_type", "textbook_text"),
                    "keywords": chunk.get("keywords", []),
                    "kind": "textbook_chunk",
                    "textbook_index": index,
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
                str(entry.get("topic") or ""),
                str(entry.get("title") or ""),
                str(entry.get("content") or ""),
                " ".join(entry.get("keywords", [])),
            ]
        )

    @classmethod
    def _expand_query(cls, query: str) -> tuple[str, list[str]]:
        """Append explicit bilingual concepts while preserving the raw query."""

        expansions = [
            english
            for chinese, english in cls.QUERY_TRANSLATIONS
            if chinese in query
        ]
        return " ".join([query, *expansions]), expansions

    def retrieve(
        self,
        query: str,
        topic: str | None = None,
        module_id: str | None = None,
        concept_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(self.config.retrieval_top_k if limit is None else limit, 10))
        cache_key = (
            " ".join(query.casefold().split()),
            topic,
            module_id,
            concept_id,
            safe_limit,
        )
        if self._cache_size:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    self._cache_hits += 1
                    self._cache.move_to_end(cache_key)
                    return deepcopy(cached)
                self._cache_misses += 1
        expanded_query, query_expansions = self._expand_query(query)
        query_terms = self._terms(expanded_query) - self.QUERY_STOPWORDS
        normalized_query = " ".join(query.lower().split())
        query_vector, retrieval_mode = self._query_vector(expanded_query)
        scored: list[
            tuple[float, int, dict[str, Any], float, float, float, float]
        ] = []
        for index, (entry, entry_terms, title_terms, entry_vector) in enumerate(
            zip(
                self.entries,
                self._term_sets,
                self._title_term_sets,
                self._entry_vectors,
                strict=True,
            )
        ):
            overlap = query_terms & entry_terms
            sparse_score = sum(self._idf.get(term, 1.0) for term in overlap)
            title_sparse_score = sum(
                self._idf.get(term, 1.0) for term in query_terms & title_terms
            )
            topic_bonus = 6.0 if topic and entry.get("topic") == topic else 0.0
            curated_bonus = 2.5 if entry["kind"] == "curated" else 0.0
            phrase_bonus = (
                12.0
                if len(normalized_query) >= 5
                and normalized_query in self._entry_text(entry).lower()
                else 0.0
            )
            key_terms = [
                term for term in re.findall(r"[a-z][a-z0-9-]{2,}", query.lower())
                if term not in self.QUERY_STOPWORDS
            ]
            key_phrase_bonus = (
                14.0
                if len(key_terms) >= 2
                and re.search(
                    r".*".join(re.escape(term) for term in key_terms),
                    self._entry_text(entry).lower(),
                )
                else 0.0
            )
            definition_bonus = (
                8.0
                if len(key_terms) >= 2
                and re.search(
                    r".*".join(re.escape(term) for term in key_terms)
                    + r"\s+(?:says|is|are|means)\b",
                    self._entry_text(entry).lower(),
                )
                else 0.0
            )
            dense_score = (
                max(0.0, sum(a * b for a, b in zip(query_vector, entry_vector)))
                if query_vector
                else 0.0
            )
            bonus_score = (
                topic_bonus
                + curated_bonus
                + phrase_bonus
                + key_phrase_bonus
                + definition_bonus
            )
            score = (
                sparse_score
                + 2.0 * title_sparse_score
                + 5.0 * dense_score
                + bonus_score
            )
            if score > 0:
                scored.append(
                    (
                        score,
                        -index,
                        entry,
                        sparse_score,
                        title_sparse_score,
                        dense_score,
                        bonus_score,
                    )
                )
        scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
        def serialise(item: tuple[float, int, dict[str, Any], float, float, float, float], scope: str) -> dict[str, Any]:
            score, _, entry, sparse_score, title_sparse_score, dense_score, bonus_score = item
            return {
                "module_id": entry.get("module_id"),
                "concept_id": entry.get("concept_id"),
                "topic": entry.get("topic"),
                "title": entry.get("title"),
                "content": entry.get("content"),
                "source": entry.get("source"),
                "kind": entry.get("kind"),
                "source_type": entry.get("source_type", "course_material"),
                "page": entry.get("page"),
                "content_type": entry.get("content_type"),
                "retrieval_scope": scope,
                "score": round(score, 3),
                "score_breakdown": {
                    "sparse": round(sparse_score, 3),
                    "title_sparse": round(title_sparse_score, 3),
                    "vector": round(dense_score, 4),
                    "bonuses": round(bonus_score, 3),
                },
                "embedding_backend": self.embedding_backend.name,
                "retrieval_mode": retrieval_mode,
                "query_expansions": query_expansions,
                "corpus_sha256": self.corpus_sha256,
            }

        # Prefer the selected concept, then its module, then the global corpus.
        # Each scope is only used to fill missing evidence, never to discard an
        # unmapped textbook passage.
        selected: list[dict[str, Any]] = []
        used: set[int] = set()

        def take(predicate: Callable[[dict[str, Any]], bool], scope: str) -> None:
            for item in scored:
                entry_index = -item[1]
                if len(selected) >= safe_limit:
                    return
                if entry_index not in used and predicate(item[2]):
                    used.add(entry_index)
                    selected.append(serialise(item, scope))

        if concept_id:
            take(lambda entry: entry.get("concept_id") == concept_id, "concept")
            if len(selected) < safe_limit and module_id:
                take(lambda entry: entry.get("module_id") == module_id, "module")
            if len(selected) < safe_limit:
                take(lambda entry: True, "global")
        elif module_id:
            take(lambda entry: entry.get("module_id") == module_id, "module")
            if not selected:
                take(lambda entry: True, "global")
        else:
            take(lambda entry: True, "global")
        results = selected
        # A sparse emergency answer must not outlive provider recovery in cache.
        if self._cache_size and retrieval_mode == "hybrid":
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
        with self._embedding_circuit_lock:
            retry_after_seconds = max(
                0.0, self._embedding_retry_after - self._clock()
            )
            embedding_circuit = {
                "state": (
                    "probe_in_flight"
                    if self._embedding_request_in_flight
                    else "open" if retry_after_seconds > 0 else "closed"
                ),
                "cooldown_seconds": self._embedding_failure_cooldown,
                "retry_after_seconds": round(retry_after_seconds, 3),
                "query_failures": self._embedding_query_failures,
                "query_skips": self._embedding_query_skips,
                "request_in_flight": self._embedding_request_in_flight,
            }
        return {
            "entries": len(self.entries),
            "total_entries": len(self.entries),
            "curated_cards": sum(entry["kind"] == "curated" for entry in self.entries),
            "notebook_chunks": sum(
                entry["kind"] == "notebook_cell" for entry in self.entries
            ),
            "reference_chunks": sum(
                entry["kind"] == "reference_chunk" for entry in self.entries
            ),
            "textbook_chunks": sum(
                entry["kind"] == "textbook_chunk" for entry in self.entries
            ),
            "embedding_backend": self.embedding_backend.name,
            "embedding_dimension": self.embedding_backend.dimension,
            "embedding_fallback": self.embedding_fallback_reason,
            "embedding_circuit": embedding_circuit,
            "corpus_sha256": self.corpus_sha256,
            "retrieval_top_k": self.config.retrieval_top_k,
            "retrieval_cache": cache_stats,
            "query_translation_rules": len(self.QUERY_TRANSLATIONS),
        }
