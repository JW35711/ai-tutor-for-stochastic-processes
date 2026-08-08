import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DeploymentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (ROOT / "compose.yaml").read_text("utf-8")
        cls.dockerfile = (ROOT / "Dockerfile").read_text("utf-8")
        cls.workflow = (
            ROOT / ".github" / "workflows" / "test.yml"
        ).read_text("utf-8")
        cls.environment = (ROOT / ".env.example").read_text("utf-8")

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

    def test_ci_starts_checks_and_cleans_hardened_service(self) -> None:
        self.assertIn("docker compose config --quiet", self.workflow)
        self.assertIn("http://127.0.0.1:8000/ready", self.workflow)
        self.assertIn("http://127.0.0.1:8000/openapi.json", self.workflow)
        self.assertIn("docker compose down --volumes", self.workflow)

    def test_example_environment_documents_every_runtime_bound(self) -> None:
        for variable in (
            "API_RATE_LIMIT_PER_MINUTE",
            "API_RATE_LIMIT_CLIENT_CAP",
            "MAX_JSON_BODY_BYTES",
            "MAX_QUESTION_CHARS",
            "REQUEST_SOCKET_TIMEOUT_SECONDS",
            "MAX_SESSION_EVENTS",
            "MEMORY_RETENTION_DAYS",
        ):
            self.assertIn(f"{variable}=", self.environment)


if __name__ == "__main__":
    unittest.main()
