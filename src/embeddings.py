"""Pluggable embedding backends for hybrid course-material retrieval."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Protocol

from .config import env_float, env_int


def normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) ** 2 for value in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [float(value) / norm for value in vector]


class EmbeddingBackend(Protocol):
    name: str
    dimension: int

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]: ...


class LocalHashEmbedding:
    """Deterministic, offline character and word hashing vectorizer.

    It provides a real vector index and catches near-duplicate phrasing without
    pretending to be a neural semantic model.  The backend is useful as a safe
    fallback when no embedding API is configured.
    """

    name = "local_hash"

    def __init__(self, dimension: int = 384) -> None:
        if not 64 <= dimension <= 4096:
            raise ValueError("hash embedding dimension must be between 64 and 4096")
        self.dimension = dimension

    @staticmethod
    def _features(text: str) -> list[str]:
        lowered = " ".join(text.lower().replace("‑", "-").split())
        features = re.findall(r"[a-z0-9_]+(?:/[a-z0-9_]+)*", lowered)
        compact = re.sub(r"\s+", "", lowered)
        for width in (2, 3, 4):
            features.extend(
                compact[index : index + width]
                for index in range(max(0, len(compact) - width + 1))
            )
        return features

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for feature in self._features(text):
                digest = hashlib.blake2b(
                    feature.encode("utf-8"), digest_size=8
                ).digest()
                number = int.from_bytes(digest, "big")
                index = (number >> 1) % self.dimension
                sign = 1.0 if number & 1 else -1.0
                vector[index] += sign
            vectors.append(normalize(vector))
        return vectors


class OpenAICompatibleEmbedding:
    """Optional batched embedding client using an OpenAI-compatible endpoint."""

    name = "openai_compatible"
    dimension = 0

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 30.0,
        batch_size: int = 64,
        max_response_bytes: int = 10_000_000,
    ) -> None:
        if not api_key:
            raise ValueError("embedding API key is required")
        if not model:
            raise ValueError("embedding model is required")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("embedding timeout must be positive")
        if batch_size < 1 or batch_size > 2048:
            raise ValueError("embedding batch size must be between 1 and 2048")
        if not 1_024 <= max_response_bytes <= 100_000_000:
            raise ValueError(
                "embedding response limit must be between 1024 and 100000000"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = batch_size
        self.max_response_bytes = max_response_bytes

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed_batch(texts[offset : offset + self.batch_size]))
        return vectors

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(
                {"model": self.model, "input": list(texts)}, ensure_ascii=False
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise RuntimeError("embedding response exceeds configured limit")
            payload = json.loads(body.decode("utf-8"))
        except (
            urllib.error.URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise RuntimeError(f"embedding request failed: {error}") from error
        try:
            rows = sorted(payload.get("data", []), key=lambda item: item["index"])
        except (AttributeError, KeyError, TypeError) as error:
            raise RuntimeError("embedding endpoint returned malformed data") from error
        if len(rows) != len(texts):
            raise RuntimeError("embedding endpoint returned an unexpected row count")
        if [row.get("index") for row in rows] != list(range(len(texts))):
            raise RuntimeError("embedding endpoint returned invalid row indices")
        try:
            vectors = [normalize(row["embedding"]) for row in rows]
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("embedding endpoint returned malformed vectors") from error
        if vectors:
            dimension = len(vectors[0])
            if dimension < 1 or any(len(vector) != dimension for vector in vectors):
                raise RuntimeError("embedding vectors have inconsistent dimensions")
            if self.dimension not in {0, dimension}:
                raise RuntimeError("embedding dimension changed between batches")
            self.dimension = dimension
        return vectors


def embedding_backend_from_environment() -> EmbeddingBackend:
    backend = os.getenv("RAG_EMBEDDING_BACKEND", "local_hash").strip().lower()
    if backend in {"", "local", "local_hash"}:
        dimension = env_int(
            "RAG_HASH_DIMENSION",
            384,
            minimum=64,
            maximum=4096,
        )
        return LocalHashEmbedding(dimension=dimension)
    if backend in {"openai", "openai_compatible"}:
        return OpenAICompatibleEmbedding(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            model=os.getenv("EMBEDDING_MODEL", ""),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1"),
            timeout=env_float(
                "EMBEDDING_TIMEOUT_SECONDS",
                30,
                minimum=0.1,
                maximum=300,
            ),
            batch_size=env_int(
                "EMBEDDING_BATCH_SIZE",
                64,
                minimum=1,
                maximum=2048,
            ),
            max_response_bytes=env_int(
                "EMBEDDING_MAX_RESPONSE_BYTES",
                10_000_000,
                minimum=1_024,
                maximum=100_000_000,
            ),
        )
    raise ValueError(f"unsupported RAG_EMBEDDING_BACKEND: {backend}")
