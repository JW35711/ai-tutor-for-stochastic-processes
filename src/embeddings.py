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
        if dimension < 64:
            raise ValueError("hash embedding dimension must be at least 64")
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
    ) -> None:
        if not api_key:
            raise ValueError("embedding API key is required")
        if not model:
            raise ValueError("embedding model is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
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
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"embedding request failed: {error}") from error
        rows = sorted(payload.get("data", []), key=lambda item: item["index"])
        if len(rows) != len(texts):
            raise RuntimeError("embedding endpoint returned an unexpected row count")
        vectors = [normalize(row["embedding"]) for row in rows]
        if vectors:
            self.dimension = len(vectors[0])
        return vectors


def embedding_backend_from_environment() -> EmbeddingBackend:
    backend = os.getenv("RAG_EMBEDDING_BACKEND", "local_hash").strip().lower()
    if backend in {"", "local", "local_hash"}:
        dimension = int(os.getenv("RAG_HASH_DIMENSION", "384"))
        return LocalHashEmbedding(dimension=dimension)
    if backend in {"openai", "openai_compatible"}:
        return OpenAICompatibleEmbedding(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            model=os.getenv("EMBEDDING_MODEL", ""),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1"),
        )
    raise ValueError(f"unsupported RAG_EMBEDDING_BACKEND: {backend}")
