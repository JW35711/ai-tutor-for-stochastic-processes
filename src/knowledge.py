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
DEFAULT_RETRIEVAL_ALIASES_PATH = ROOT / "data" / "retrieval_aliases.json"


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
        aliases_path: Path = DEFAULT_RETRIEVAL_ALIASES_PATH,
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
        self.retrieval_aliases = self._load_aliases(aliases_path)
        self._textbook_page_priors = self._load_textbook_page_priors()
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
                concept_id, mapping_confidence, mapping_reason = self._map_notebook_cell(
                    module_id, raw_content, content
                )
                entries.append(
                    {
                        "module_id": module_id,
                        "topic": topic,
                        "title": self._title(raw_content, content, cell_index),
                        "content": content[:1400],
                        "source": f"notebooks/{path.name}#cell-{cell_index}",
                        "keywords": [],
                        "kind": "notebook_cell",
                        "concept_id": concept_id,
                        "mapping_confidence": mapping_confidence,
                        "mapping_reason": mapping_reason,
                    }
                )
        return entries

    @staticmethod
    def _load_aliases(path: Path) -> dict[str, dict[str, Any]]:
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _load_textbook_page_priors() -> dict[str, set[int]]:
        curriculum_path = ROOT / "data" / "curriculum.json"
        try:
            payload = json.loads(curriculum_path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        priors: dict[str, set[int]] = {}
        for module in payload.get("modules", []):
            for point in module.get("knowledge_points", []):
                pages = {
                    int(match.group(1))
                    for ref in point.get("source_refs", [])
                    if (match := re.search(r"#page-(\d+)$", str(ref)))
                }
                if pages:
                    priors[str(point.get("id"))] = pages
        return priors

    def _map_notebook_cell(
        self, module_id: str, raw_content: str, content: str
    ) -> tuple[str | None, str | None, str | None]:
        """Map only high-confidence teaching cells; keep ambiguous cells module-scoped."""

        text = f"{raw_content} {content}".lower()
        heading_match = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", raw_content, re.M)
        heading = (heading_match.group(1) if heading_match else "").lower()
        candidates: list[tuple[int, str, str]] = []
        for concept_id, spec in self.retrieval_aliases.items():
            if spec.get("module_id") != module_id:
                continue
            aliases = [str(item).lower() for item in spec.get("aliases", [])]
            keywords = [str(item).lower() for item in spec.get("keywords", [])]
            notation = [str(item).lower() for item in spec.get("notation", [])]
            title = str(concept_id).replace("-", " ")
            score = 0
            matched: list[str] = []
            for alias in aliases:
                if alias and alias in text:
                    # A heading is a much stronger signal than a generic word
                    # appearing in an explanatory paragraph.  This prevents a
                    # Poisson section mentioning Bernoulli trials from being
                    # mapped to the Bernoulli-process KP.
                    score += 24 if alias in heading else 4
                    matched.append(alias)
            for term in keywords + notation:
                if term and term in text:
                    score += 4 if term in heading else 1
                    matched.append(term)
            if score:
                candidates.append((score, concept_id, ", ".join(matched[:3])))
        if not candidates:
            return None, None, None
        candidates.sort(reverse=True)
        best = candidates[0]
        second = candidates[1][0] if len(candidates) > 1 else 0
        if best[0] < 20 or best[0] - second < 6:
            return None, "ambiguous", "multiple KP signals"
        return best[1], "high", f"alias/notation match: {best[2]}"

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
                    "source_type": "textbook" if "pdf" in source.casefold() else "course_material",
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
            mapping_confidence = chunk.get("mapping_confidence")
            mapping_reason = chunk.get("mapping_reason")
            if concept_id and textbook_chunks_path == DEFAULT_TEXTBOOK_CHUNKS_PATH:
                page = chunk.get("page")
                if not isinstance(page, int) or page not in self._textbook_page_priors.get(concept_id, set()):
                    concept_id = None
                    mapping_confidence = "unmapped"
                    mapping_reason = "no explicit curriculum page prior"
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
                    "chunk_id": chunk.get("chunk_id"),
                    "parent_id": chunk.get("parent_id"),
                    "section_title": chunk.get("section_title"),
                    "section_path": chunk.get("section_path", []),
                    "chunk_index": chunk.get("chunk_index"),
                    "mapping_confidence": mapping_confidence,
                    "mapping_reason": mapping_reason,
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

    def _expand_query(self, query: str, concept_id: str | None = None) -> tuple[str, list[str]]:
        """Expand from data-driven KP aliases while retaining legacy Chinese rules."""

        expansions = [
            english
            for chinese, english in self.QUERY_TRANSLATIONS
            if chinese in query
        ]
        lowered = query.lower()
        alias_expansions: list[str] = []
        # Keep the established module-scoped regression path byte-for-byte
        # compatible.  Alias expansion is activated once routing has a
        # high-confidence KP; otherwise a broad alias list can perturb legacy
        # top-k ordering for queries such as "Poisson count distribution N(t)".
        if concept_id:
            spec = self.retrieval_aliases.get(concept_id, {})
            terms = [*spec.get("aliases", []), *spec.get("notation", []), *spec.get("keywords", [])]
            # A routed concept is already a high-confidence signal.  Expand
            # it even when the learner uses only a short title variant such as
            # "What is the transition matrix?".
            alias_expansions.extend(str(term) for term in terms)
        expanded = list(dict.fromkeys([*expansions, *alias_expansions]))
        return " ".join([query, *expanded]), expanded

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
        expanded_query, query_expansions = self._expand_query(query, concept_id)
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
                "chunk_id": entry.get("chunk_id"),
                "parent_id": entry.get("parent_id"),
                "section_title": entry.get("section_title"),
                "section_path": entry.get("section_path", []),
                "chunk_index": entry.get("chunk_index"),
                "textbook_index": entry.get("textbook_index"),
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
                "mapping_confidence": entry.get("mapping_confidence"),
                "mapping_reason": entry.get("mapping_reason"),
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

    def retrieval_diagnostic(
        self,
        query: str,
        *,
        module_id: str | None = None,
        concept_id: str | None = None,
        final_limit: int = 4,
        candidate_limit: int = 10,
    ) -> dict[str, Any]:
        """Return bounded stage evidence for course-RAG failure attribution."""

        final, expansion = self.retrieve_with_context(
            query,
            module_id=module_id,
            concept_id=concept_id,
            limit=final_limit,
            candidate_limit=candidate_limit,
        )
        all_entries = self.entries
        module_entries = [entry for entry in all_entries if not module_id or entry.get("module_id") == module_id]
        concept_entries = [entry for entry in module_entries if not concept_id or entry.get("concept_id") == concept_id]
        return {
            "final": final,
            "candidate_pool": self.retrieve(
                query, module_id=module_id, concept_id=concept_id, limit=candidate_limit
            ),
            "corpus_has_module": bool(module_entries),
            "corpus_has_concept": bool(concept_entries),
            "expansion": expansion,
        }

    def rerank_candidates(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        concept_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Apply an offline A/B reranker without changing production retrieval.

        The reranker is deliberately transparent: exact title/alias matches and
        content-type cues receive small deterministic boosts.  It is used by
        evaluation tooling only unless a caller explicitly asks for it.
        """

        lowered = query.casefold()
        spec = self.retrieval_aliases.get(concept_id or "", {})
        aliases = [str(item).casefold() for item in spec.get("aliases", [])]
        notation = [str(item).casefold() for item in spec.get("notation", [])]
        key_terms = set(self._terms(query)) - self.QUERY_STOPWORDS
        ranked: list[tuple[float, int, dict[str, Any]]] = []
        for index, item in enumerate(candidates):
            title = str(item.get("title") or "").casefold()
            content = str(item.get("content") or "").casefold()
            bonus = 0.0
            if any(alias and alias in lowered and alias in title for alias in aliases):
                bonus += 3.0
            if any(term and term in title for term in notation):
                bonus += 1.5
            if key_terms and key_terms.issubset(self._terms(title)):
                bonus += 1.0
            if any(marker in lowered for marker in ("what is", "define", "definition")) and item.get("content_type") in {"definition", "theorem"}:
                bonus += 0.5
            if any(marker in lowered for marker in ("example", "illustrate")) and item.get("content_type") == "example":
                bonus += 0.5
            ranked.append((float(item.get("score") or 0.0) + bonus, -index, item))
        ranked.sort(key=lambda value: (value[0], value[1]), reverse=True)
        result: list[dict[str, Any]] = []
        for score, _, item in ranked:
            copy = dict(item)
            copy["ab_rerank_bonus"] = round(score - float(item.get("score") or 0.0), 3)
            result.append(copy)
        return result

    def retrieve_ab(
        self,
        query: str,
        *,
        module_id: str | None = None,
        concept_id: str | None = None,
        limit: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return baseline and deterministic-reranked candidates for A/B evals."""

        pool = self.retrieve(
            query,
            module_id=module_id,
            concept_id=concept_id,
            limit=max(10, limit),
        )
        return {
            "baseline": pool[:limit],
            "deterministic_rerank": self.rerank_candidates(
                query, pool, concept_id=concept_id
            )[:limit],
        }

    def retrieve_with_context(
        self,
        query: str,
        *,
        topic: str | None = None,
        module_id: str | None = None,
        concept_id: str | None = None,
        limit: int | None = None,
        candidate_limit: int = 10,
        max_extra: int = 2,
        max_adjacent_distance: int = 1,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Retrieve top evidence and a small amount of useful local context.

        This is intentionally separate from ``retrieve`` so its stable public
        contract remains unchanged.  Neighbours are limited to the same
        notebook or textbook page and never replace the scored candidates.
        """

        safe_limit = max(1, min(limit or self.config.retrieval_top_k, 10))
        candidates = self.retrieve(
            query,
            topic=topic,
            module_id=module_id,
            concept_id=concept_id,
            limit=max(safe_limit, min(candidate_limit, 10)),
        )
        selected = candidates[:safe_limit]
        selected_sources = {str(item.get("source")) for item in selected}
        extras: list[dict[str, Any]] = []
        for item in selected:
            source = str(item.get("source") or "")
            match = re.match(r"(.+?\.ipynb)#cell-(\d+)$", source)
            if match:
                stem, cell_text = match.groups()
                center = int(cell_text)
                neighbour_sources = {
                    f"{stem}#cell-{center + distance}"
                    for distance in range(-max_adjacent_distance, max_adjacent_distance + 1)
                    if distance
                }
            else:
                page = item.get("page")
                chunk_index = item.get("textbook_index")
                if isinstance(chunk_index, int):
                    neighbour_sources = {
                        str(other.get("source"))
                        for other in self.entries
                        if other.get("kind") == "textbook_chunk"
                        and other.get("source") == source
                        and other.get("page") == page
                        and isinstance(other.get("textbook_index"), int)
                        and abs(other["textbook_index"] - chunk_index) <= max_adjacent_distance
                    }
                else:
                    neighbour_sources = set()
            for entry in self.entries:
                locator = str(entry.get("source") or "")
                if locator not in neighbour_sources or locator in selected_sources:
                    continue
                if module_id and entry.get("module_id") not in {module_id, None}:
                    continue
                if concept_id and entry.get("concept_id") not in {concept_id, None}:
                    continue
                neighbour = dict(item)
                neighbour.update(
                    {
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
                        "score": 0.0,
                        "retrieval_scope": "expanded_context",
                        "expansion_reason": "same notebook neighbourhood or textbook page",
                    }
                )
                extras.append(neighbour)
                selected_sources.add(locator)
                if len(extras) >= max_extra:
                    break
            if len(extras) >= max_extra:
                break
        merged = selected + extras
        return merged, {
            "initial_retrieved_sources": [str(item.get("source")) for item in selected],
            "expanded_sources": [str(item.get("source")) for item in extras],
            "expansion_reason": "bounded same-source local context" if extras else None,
            "candidate_pool_size": len(candidates),
            "max_extra": max_extra,
            "max_adjacent_distance": max_adjacent_distance,
        }

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
            "retrieval_alias_concepts": len(self.retrieval_aliases),
            "mapped_notebook_chunks": sum(
                entry["kind"] == "notebook_cell" and bool(entry.get("concept_id"))
                for entry in self.entries
            ),
            "ambiguous_notebook_chunks": sum(
                entry["kind"] == "notebook_cell" and entry.get("mapping_confidence") == "ambiguous"
                for entry in self.entries
            ),
            "unmapped_notebook_chunks": sum(
                entry["kind"] == "notebook_cell" and not entry.get("concept_id")
                and entry.get("mapping_confidence") != "ambiguous"
                for entry in self.entries
            ),
        }
