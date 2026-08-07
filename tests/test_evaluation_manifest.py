import json
import unittest
from pathlib import Path

from src.evaluation_manifest import load_evaluation_manifest


ROOT = Path(__file__).resolve().parent.parent


class EvaluationManifestTests(unittest.TestCase):
    def test_manifest_matches_versioned_case_files(self) -> None:
        manifest = load_evaluation_manifest()
        suites = {suite["id"]: suite for suite in manifest["suites"]}
        expected = {
            "single_turn": len(json.loads((ROOT / "evals/cases.json").read_text("utf-8"))),
            "multi_turn": len(json.loads((ROOT / "evals/conversations.json").read_text("utf-8"))),
            "retrieval": len(json.loads((ROOT / "evals/retrieval_cases.json").read_text("utf-8"))),
            "pedagogy": len(json.loads((ROOT / "evals/pedagogy_cases.json").read_text("utf-8"))),
        }
        self.assertEqual(
            {suite_id: suite["cases"] for suite_id, suite in suites.items()},
            expected,
        )
        self.assertEqual(manifest["total"], sum(expected.values()))
        self.assertEqual(manifest["passed"], manifest["total"])


if __name__ == "__main__":
    unittest.main()
