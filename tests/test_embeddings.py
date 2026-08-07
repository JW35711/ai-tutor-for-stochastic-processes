import json
import unittest
from unittest.mock import patch

from src.embeddings import LocalHashEmbedding, OpenAICompatibleEmbedding


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class EmbeddingTests(unittest.TestCase):
    def test_local_hash_embeddings_are_deterministic_and_normalized(self) -> None:
        backend = LocalHashEmbedding(dimension=128)
        first, second = backend.embed_many(["Brownian motion", "Brownian motion"])
        self.assertEqual(first, second)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_related_text_has_more_vector_overlap(self) -> None:
        backend = LocalHashEmbedding(dimension=384)
        query, related, unrelated = backend.embed_many(
            [
                "M/M/1 queue arrival service rate",
                "queue arrival rate and service rate",
                "Brownian Gaussian particle motion",
            ]
        )
        related_score = sum(a * b for a, b in zip(query, related))
        unrelated_score = sum(a * b for a, b in zip(query, unrelated))
        self.assertGreater(related_score, unrelated_score)

    def test_openai_compatible_backend_batches_and_normalizes(self) -> None:
        payload = {
            "data": [
                {"index": 1, "embedding": [0.0, 3.0]},
                {"index": 0, "embedding": [4.0, 0.0]},
            ]
        }
        backend = OpenAICompatibleEmbedding(
            api_key="test-key",
            model="embedding-test",
            base_url="https://example.invalid/v1",
        )
        with patch("urllib.request.urlopen", return_value=FakeResponse(payload)) as call:
            vectors = backend.embed_many(["first", "second"])
        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(backend.dimension, 2)
        request = call.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request_body["input"], ["first", "second"])
        self.assertEqual(request_body["model"], "embedding-test")


if __name__ == "__main__":
    unittest.main()
