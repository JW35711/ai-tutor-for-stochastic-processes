import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DeploymentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (ROOT / "compose.yaml").read_text("utf-8")
        cls.dockerfile = (ROOT / "Dockerfile").read_text("utf-8")

    def test_container_runs_as_unprivileged_user(self) -> None:
        self.assertIn("USER appuser", self.dockerfile)
        self.assertIn("useradd --create-home --uid 10001", self.dockerfile)

    def test_compose_limits_network_and_kernel_surface(self) -> None:
        for contract in (
            '"127.0.0.1:8000:8000"',
            "read_only: true",
            "cap_drop:",
            "- ALL",
            "no-new-privileges:true",
            "pids_limit: 256",
            "mem_limit: 1g",
            "cpus: 2.0",
        ):
            self.assertIn(contract, self.compose)

    def test_only_artifact_volume_and_bounded_tmp_are_writable(self) -> None:
        self.assertIn("tutor-data:/app/artifacts", self.compose)
        self.assertIn("/tmp:rw,noexec,nosuid,size=64m", self.compose)
        self.assertIn("TUTOR_MEMORY_PATH: /app/artifacts/", self.compose)


if __name__ == "__main__":
    unittest.main()
