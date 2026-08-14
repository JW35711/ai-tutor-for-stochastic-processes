import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SecurityHygieneTests(unittest.TestCase):
    def test_docker_context_excludes_local_environment_files(self) -> None:
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".env\n", dockerignore)
        self.assertIn(".env.*", dockerignore)
        self.assertIn("!.env.example", dockerignore)

    def test_env_is_ignored_and_example_has_no_real_key(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn(".env\n", gitignore)
        self.assertNotRegex(example, r"sk-[A-Za-z0-9]{20,}")
        self.assertRegex(example, r"(?m)^LLM_API_KEY=$")
