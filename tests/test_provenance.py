import unittest

from src.provenance import execution_sha256


class ProvenanceTests(unittest.TestCase):
    def test_fingerprint_is_order_independent_but_result_sensitive(self) -> None:
        common = {
            "module_id": "module04",
            "tool": "simulate_brownian_motion",
            "corpus_sha256": "a" * 64,
        }
        first = execution_sha256(
            **common,
            parameters={"paths": 500, "horizon": 1.0},
            result={"variance": 1.01, "mean": 0.0},
        )
        reordered = execution_sha256(
            **common,
            parameters={"horizon": 1.0, "paths": 500},
            result={"mean": 0.0, "variance": 1.01},
        )
        changed = execution_sha256(
            **common,
            parameters={"horizon": 2.0, "paths": 500},
            result={"mean": 0.0, "variance": 2.02},
        )
        self.assertEqual(first, reordered)
        self.assertNotEqual(first, changed)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
