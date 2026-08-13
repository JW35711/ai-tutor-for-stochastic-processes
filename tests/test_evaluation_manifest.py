import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation_manifest import load_evaluation_manifest
from src.knowledge import KnowledgeBase


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
            "safety": len(json.loads((ROOT / "evals/safety_cases.json").read_text("utf-8"))),
            "answerability": len(json.loads((ROOT / "evals/answerability_cases.json").read_text("utf-8"))),
            "experiment_routing": 17,
            "visualization_e2e": 74,
        }
        case_files = {
            "single_turn": ROOT / "evals/cases.json",
            "multi_turn": ROOT / "evals/conversations.json",
            "retrieval": ROOT / "evals/retrieval_cases.json",
            "pedagogy": ROOT / "evals/pedagogy_cases.json",
            "safety": ROOT / "evals/safety_cases.json",
            "answerability": ROOT / "evals/answerability_cases.json",
            "experiment_routing": ROOT / "evals/experiment_routing_cases.json",
            "visualization_e2e": ROOT / "data/notebook_experiments.json",
        }
        self.assertEqual(
            {suite_id: suite["cases"] for suite_id, suite in suites.items()},
            expected,
        )
        self.assertEqual(manifest["total"], sum(expected.values()))
        self.assertEqual(manifest["passed"], manifest["total"])
        self.assertEqual(manifest["corpus_sha256"], KnowledgeBase().corpus_sha256)
        self.assertEqual(manifest["version"], 3)
        self.assertEqual(manifest["baseline_id"], "current-evidence-sufficiency")
        self.assertEqual(manifest["historical_baseline"]["total"], 109)
        for suite_id, path in case_files.items():
            self.assertEqual(
                suites[suite_id]["cases_file"],
                str(path.relative_to(ROOT)),
            )
            self.assertEqual(
                suites[suite_id]["cases_sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_loader_rejects_case_content_changed_without_manifest_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "evals").mkdir()
            case_path = root / "evals" / "cases.json"
            case_path.write_text('[{"id":"changed"}]', "utf-8")
            manifest = {
                "version": 2,
                "corpus_sha256": "a" * 64,
                "total": 1,
                "passed": 1,
                "suites": [
                    {
                        "id": "single_turn",
                        "cases": 1,
                        "passed": 1,
                        "cases_file": "evals/cases.json",
                        "cases_sha256": "b" * 64,
                    }
                ],
            }
            manifest_path = root / "data" / "evaluation_manifest.json"
            manifest_path.write_text(json.dumps(manifest), "utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_evaluation_manifest(manifest_path)


if __name__ == "__main__":
    unittest.main()
