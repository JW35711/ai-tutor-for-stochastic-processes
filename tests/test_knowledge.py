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

    def test_chinese_character_terms_retrieve_relevant_card(self) -> None:
        sources = self.knowledge.retrieve("布朗运动方差", module_id="module04")
        self.assertEqual(sources[0]["module_id"], "module04")


if __name__ == "__main__":
    unittest.main()
