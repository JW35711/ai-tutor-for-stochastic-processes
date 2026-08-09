import unittest

from src.knowledge import KnowledgeBase


class QueryFailingEmbedding:
    name = "query_failing_test"
    dimension = 2

    def __init__(self) -> None:
        self.calls = 0

    def embed_many(self, texts):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("query backend unavailable")
        return [[1.0, 0.0] for _ in texts]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge = KnowledgeBase()

    def test_indexes_curated_cards_and_notebook_cells(self) -> None:
        stats = self.knowledge.stats()
        self.assertEqual(stats["curated_cards"], 11)
        self.assertGreater(stats["notebook_chunks"], 100)
        self.assertGreaterEqual(stats["reference_chunks"], 10)
        self.assertEqual(stats["embedding_backend"], "local_hash")
        self.assertEqual(stats["embedding_dimension"], 384)
        self.assertRegex(stats["corpus_sha256"], r"^[0-9a-f]{64}$")

    def test_retrieval_is_module_scoped_and_traceable(self) -> None:
        sources = self.knowledge.retrieve(
            "M/M/1 queue stability",
            topic="applied_markov_models",
            module_id="module07",
        )
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(item["module_id"] == "module07" for item in sources))
        self.assertTrue(any("#cell-" in item["source"] for item in sources))
        self.assertTrue(all(item["score"] > 0 for item in sources))
        self.assertTrue(all("score_breakdown" in item for item in sources))
        self.assertTrue(
            all(item["embedding_backend"] == "local_hash" for item in sources)
        )
        self.assertTrue(
            all(item["retrieval_mode"] == "hybrid" for item in sources)
        )
        self.assertTrue(
            all(
                item["corpus_sha256"] == self.knowledge.corpus_sha256
                for item in sources
            )
        )

    def test_reference_chunks_are_retrievable_with_page_locators(self) -> None:
        sources = self.knowledge.retrieve(
            "M/M/1 traffic intensity geometric steady state",
            module_id="module07",
        )
        self.assertTrue(
            any(
                item["kind"] == "reference_chunk"
                and item["source"] == "reference/lectnotes_technmath.pdf#page-69"
                for item in sources
            )
        )

    def test_chinese_character_terms_retrieve_relevant_card(self) -> None:
        sources = self.knowledge.retrieve("布朗运动方差", module_id="module04")
        self.assertEqual(sources[0]["module_id"], "module04")

    def test_chinese_concept_expansion_targets_english_notebook_cell(self) -> None:
        sources = self.knowledge.retrieve(
            "如何用模拟检验几何等待时间的无记忆性",
            module_id="module01",
        )
        self.assertIn("memoryless property", sources[0]["content"].lower())
        self.assertIn("memoryless property", sources[0]["query_expansions"][0])
        self.assertGreater(
            sources[0]["score_breakdown"]["title_sparse"],
            0,
        )

    def test_repeated_retrieval_uses_isolated_lru_cache_entries(self) -> None:
        knowledge = KnowledgeBase(cache_size=2)
        first = knowledge.retrieve("Poisson waiting time", module_id="module01")
        first[0]["title"] = "mutated by caller"
        second = knowledge.retrieve("Poisson waiting time", module_id="module01")
        self.assertNotEqual(second[0]["title"], "mutated by caller")
        stats = knowledge.stats()["retrieval_cache"]
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

    def test_zero_cache_capacity_disables_cache(self) -> None:
        knowledge = KnowledgeBase(cache_size=0)
        knowledge.retrieve("Brownian path", module_id="module04")
        knowledge.retrieve("Brownian path", module_id="module04")
        stats = knowledge.stats()["retrieval_cache"]
        self.assertEqual(stats, {"capacity": 0, "size": 0, "hits": 0, "misses": 0})

    def test_corpus_fingerprint_is_stable_for_same_material(self) -> None:
        other = KnowledgeBase()
        self.assertEqual(other.corpus_sha256, self.knowledge.corpus_sha256)

    def test_query_embedding_failure_is_labeled_sparse_fallback(self) -> None:
        knowledge = KnowledgeBase(
            embedding_backend=QueryFailingEmbedding(),
            cache_size=0,
        )
        sources = knowledge.retrieve("Poisson waiting time", module_id="module01")
        self.assertTrue(sources)
        self.assertTrue(
            all(item["retrieval_mode"] == "sparse_fallback" for item in sources)
        )
        self.assertIn(
            "query backend unavailable",
            knowledge.stats()["embedding_fallback"],
        )

    def test_query_embedding_circuit_skips_then_recovers(self) -> None:
        backend = QueryFailingEmbedding()
        clock = FakeClock()
        knowledge = KnowledgeBase(
            embedding_backend=backend,
            cache_size=0,
            embedding_failure_cooldown=60,
            clock=clock,
        )

        failed = knowledge.retrieve("Poisson arrivals", module_id="module01")
        skipped = knowledge.retrieve("Brownian variance", module_id="module04")
        self.assertEqual(backend.calls, 2)
        self.assertTrue(
            all(item["retrieval_mode"] == "sparse_fallback" for item in failed)
        )
        self.assertTrue(
            all(item["retrieval_mode"] == "sparse_fallback" for item in skipped)
        )
        open_stats = knowledge.stats()["embedding_circuit"]
        self.assertEqual(open_stats["state"], "open")
        self.assertEqual(open_stats["query_failures"], 1)
        self.assertEqual(open_stats["query_skips"], 1)

        clock.now += 61
        recovered = knowledge.retrieve("Markov transition", module_id="module05")
        self.assertEqual(backend.calls, 3)
        self.assertTrue(
            all(item["retrieval_mode"] == "hybrid" for item in recovered)
        )
        recovered_stats = knowledge.stats()
        self.assertEqual(recovered_stats["embedding_circuit"]["state"], "closed")
        self.assertIsNone(recovered_stats["embedding_fallback"])

    def test_sparse_fallback_result_is_not_cached(self) -> None:
        backend = QueryFailingEmbedding()
        clock = FakeClock()
        knowledge = KnowledgeBase(
            embedding_backend=backend,
            cache_size=2,
            embedding_failure_cooldown=1,
            clock=clock,
        )
        knowledge.retrieve("Poisson arrivals", module_id="module01")
        self.assertEqual(knowledge.stats()["retrieval_cache"]["size"], 0)
        clock.now += 2
        recovered = knowledge.retrieve("Poisson arrivals", module_id="module01")
        self.assertTrue(
            all(item["retrieval_mode"] == "hybrid" for item in recovered)
        )
        self.assertEqual(knowledge.stats()["retrieval_cache"]["size"], 1)

    def test_embedding_failure_cooldown_is_bounded(self) -> None:
        for invalid in (-1, float("inf"), 3601):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "cooldown"):
                    KnowledgeBase(embedding_failure_cooldown=invalid)


if __name__ == "__main__":
    unittest.main()
