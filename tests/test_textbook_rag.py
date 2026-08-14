import json
import tempfile
import unittest
from pathlib import Path

from src.agent import StochasticTutorAgent
from src.knowledge import KnowledgeBase
from src.memory import LearnerMemory


class TextbookRagTests(unittest.TestCase):
    def test_loads_textbook_chunks_and_falls_back_from_concept_scope(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "textbook_chunks.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "text": "Brownian motion has Gaussian increments.",
                            "title": "Brownian motion",
                            "source_type": "textbook",
                            "source": "lectnotes_technmath.pdf#page-43",
                            "page": 43,
                            "module_id": "module04",
                            "concept_id": "m04-brownian-increments",
                            "content_type": "definition",
                        },
                        {
                            "text": "The law of large numbers concerns sample averages.",
                            "title": "Law of large numbers",
                            "source_type": "textbook",
                            "source": "lectnotes_technmath.pdf#page-9",
                            "page": 9,
                            "module_id": None,
                            "concept_id": None,
                            "content_type": "theorem",
                        },
                    ]
                ),
                "utf-8",
            )
            knowledge = KnowledgeBase(textbook_chunks_path=path)
            results = knowledge.retrieve(
                "Brownian motion Gaussian increments",
                module_id="module04",
                concept_id="m04-brownian-increments",
            )
            self.assertEqual(results[0]["retrieval_scope"], "concept")
            self.assertEqual(results[0]["source_type"], "textbook")
            self.assertEqual(knowledge.stats()["textbook_chunks"], 2)
            self.assertEqual(knowledge.stats()["total_entries"], len(knowledge.entries))

    def test_unknown_question_is_a_safe_scope_response(self) -> None:
        memory = LearnerMemory(":memory:")
        try:
            response = StochasticTutorAgent(memory=memory).answer("你好，你是谁？")
        finally:
            memory.close()
        self.assertEqual(response["tool"], "no_simulation")
        self.assertEqual(response["intent"], "general_chat")
        self.assertEqual(response["sources"], [])


if __name__ == "__main__":
    unittest.main()
