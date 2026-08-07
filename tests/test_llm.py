import unittest

from src.llm import preserves_verified_facts


class LLMGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.draft = (
            "经验均值 1.25，理论值 1.5。\n"
            "来源：notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.sources = [
            {"source": "notebooks/04_Random_Walk_Part3.ipynb#cell-4"}
        ]

    def test_accepts_rewrite_that_preserves_numbers_and_source(self) -> None:
        candidate = (
            "理论值 1.5，而本次经验均值为 1.25。\n"
            "notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.assertTrue(
            preserves_verified_facts(candidate, self.draft, self.sources)
        )

    def test_rejects_changed_number(self) -> None:
        candidate = (
            "经验均值 1.20，理论值 1.5。\n"
            "notebooks/04_Random_Walk_Part3.ipynb#cell-4"
        )
        self.assertFalse(
            preserves_verified_facts(candidate, self.draft, self.sources)
        )

    def test_rejects_missing_source(self) -> None:
        self.assertFalse(
            preserves_verified_facts(
                "经验均值 1.25，理论值 1.5。",
                self.draft,
                self.sources,
            )
        )


if __name__ == "__main__":
    unittest.main()
