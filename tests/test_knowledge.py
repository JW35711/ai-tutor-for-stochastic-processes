import unittest

from src.knowledge import KnowledgeBase


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge = KnowledgeBase()

    def test_indexes_curated_cards_and_notebook_cells(self) -> None:
        stats = self.knowledge.stats()
        self.assertEqual(stats["curated_cards"], 11)
        self.assertGreater(stats["notebook_chunks"], 100)
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
            all(
                item["corpus_sha256"] == self.knowledge.corpus_sha256
                for item in sources
            )
        )

    def test_chinese_character_terms_retrieve_relevant_card(self) -> None:
        sources = self.knowledge.retrieve("布朗运动方差", module_id="module04")
        self.assertEqual(sources[0]["module_id"], "module04")

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


if __name__ == "__main__":
    unittest.main()
