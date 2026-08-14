"""Keep the recruiter-facing README variants aligned on release facts."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReadmeConsistencyTests(unittest.TestCase):
    def test_trilingual_readmes_share_release_numbers_and_navigation(self) -> None:
        for name in ("README.md", "README.zh-CN.md", "README.sv.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for metric in ("11", "40", "15", "421", "74/74", "11/11"):
                self.assertIn(metric, text, msg=f"{name} is missing {metric}")
            self.assertIn("README.zh-CN.md", text)
            self.assertIn("README.sv.md", text)
            self.assertIn("docs/assets/stochlab-overview.png", text)

    def test_english_readme_states_the_architecture_boundary(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "Curriculum Agent",
            "Assessment Agent",
            "Tutor Agent",
            "not a free-form multi-agent platform",
        ):
            self.assertIn(phrase, text)
        self.assertIn("RAG,", text)
        self.assertIn("evidence sufficiency", text)
        self.assertIn("SQLite and Python tools are services", text)


if __name__ == "__main__":
    unittest.main()
