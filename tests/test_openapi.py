import unittest

from src.openapi import OPENAPI_SPEC


class OpenAPIContractTests(unittest.TestCase):
    def test_spec_covers_every_public_api_and_probe(self) -> None:
        expected = {
            "/live",
            "/ready",
            "/health",
            "/api/topics",
            "/api/tools",
            "/api/chat",
            "/api/profile",
            "/api/quiz",
            "/api/quiz/submit",
            "/api/sessions/{session_id}",
            "/api/sessions/{session_id}/export",
        }
        self.assertEqual(set(OPENAPI_SPEC["paths"]), expected)

    def test_mutating_routes_have_typed_request_or_path_contracts(self) -> None:
        chat = OPENAPI_SPEC["paths"]["/api/chat"]["post"]
        quiz = OPENAPI_SPEC["paths"]["/api/quiz/submit"]["post"]
        delete = OPENAPI_SPEC["paths"]["/api/sessions/{session_id}"]["delete"]
        self.assertTrue(chat["requestBody"]["required"])
        self.assertTrue(quiz["requestBody"]["required"])
        self.assertEqual(delete["parameters"][0]["$ref"], "#/components/parameters/SessionPath")

    def test_error_schema_matches_traceable_runtime_envelope(self) -> None:
        required = OPENAPI_SPEC["components"]["schemas"]["Error"]["required"]
        self.assertEqual(required, ["error", "error_code", "request_id"])


if __name__ == "__main__":
    unittest.main()
