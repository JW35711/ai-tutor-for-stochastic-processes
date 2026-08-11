import unittest

from evals.run_v1_acceptance import run


class V1AcceptanceSetTests(unittest.TestCase):
    def test_mock_acceptance_set_passes_without_provider_credentials(self) -> None:
        report = run(real=False)
        self.assertEqual(report["total"], 22)
        self.assertEqual(report["passed"], 22)
        self.assertFalse(report["failures"])

    def test_definition_and_why_cases_are_not_the_same_answer(self) -> None:
        report = run(real=False)
        answers = {item["id"]: item["answer"] for item in report["results"]}
        self.assertNotEqual(answers["definition_bernoulli"], answers["why_poisson_waiting"])
        self.assertEqual(
            next(item for item in report["results"] if item["id"] == "brownian_simulation")["tool_called"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
