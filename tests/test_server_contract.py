import unittest
from io import BytesIO
from unittest.mock import Mock

from server import (
    EVALUATION,
    RATE_LIMITER,
    TutorHTTPServer,
    TutorRequestHandler,
    readiness_report,
    validate_session_id,
    validate_session_path,
)


class ServerContractTests(unittest.TestCase):
    def test_common_headers_include_request_and_browser_protection(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.request_id = "request-123"
        handler.rate_limit_remaining = 9
        handler.send_header = Mock()
        handler._common_headers()
        headers = dict(call.args for call in handler.send_header.call_args_list)
        self.assertEqual(headers["X-Request-ID"], "request-123")
        self.assertEqual(headers["X-API-Version"], "1")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-RateLimit-Limit"], str(RATE_LIMITER.limit))
        self.assertEqual(headers["X-RateLimit-Remaining"], "9")

    def test_server_header_omits_python_runtime_version(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        self.assertRegex(handler.version_string(), r"^StochasticTutor/\d+\.\d+\.\d+$")
        self.assertNotIn("Python", handler.version_string())

    def test_invalid_supplied_request_id_is_replaced(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.headers = {"X-Request-ID": "contains spaces and is invalid"}
        handler._begin_request()
        self.assertRegex(handler.request_id, r"^[0-9a-f]{32}$")

    def test_server_drains_request_threads_before_closing_memory(self) -> None:
        self.assertFalse(TutorHTTPServer.daemon_threads)
        self.assertTrue(TutorHTTPServer.block_on_close)
        self.assertTrue(TutorHTTPServer.allow_reuse_address)

    def test_dashboard_evaluation_matches_live_corpus(self) -> None:
        self.assertTrue(EVALUATION["corpus_match"])

    def test_service_is_ready_only_when_all_dependencies_pass(self) -> None:
        report = readiness_report()
        self.assertTrue(report["ready"])
        self.assertTrue(all(report["checks"].values()))

    def test_api_rate_limit_helper_returns_retry_metadata(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.client_address = ("contract-test-client", 1234)
        handler.request_id = "rate-test"
        handler._json = Mock()
        original_limit = RATE_LIMITER.limit
        try:
            RATE_LIMITER.limit = 1
            self.assertTrue(handler._allow_api_request())
            self.assertFalse(handler._allow_api_request())
        finally:
            RATE_LIMITER.limit = original_limit
        args = handler._json.call_args.args
        self.assertEqual(args[1].value, 429)
        self.assertEqual(args[0]["error_code"], "rate_limited")
        self.assertEqual(args[0]["request_id"], "rate-test")
        self.assertIn("Retry-After", args[2])

    def test_error_envelope_is_traceable_and_keeps_string_message(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.request_id = "request-error-1"
        handler._json = Mock()
        handler._error("bad input", 400, "invalid_request")
        payload, status, headers = handler._json.call_args.args
        self.assertEqual(
            payload,
            {
                "error": "bad input",
                "error_code": "invalid_request",
                "request_id": "request-error-1",
            },
        )
        self.assertEqual(status, 400)
        self.assertIsNone(headers)

    def test_session_id_contract_is_shared_across_api_routes(self) -> None:
        self.assertEqual(validate_session_id(" learner-1 "), "learner-1")
        self.assertIsNone(validate_session_id(None))
        for invalid in (123, "", "x" * 129, "line\nbreak"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_session_id(invalid, required=True)

    def test_session_export_path_decodes_only_one_safe_identifier(self) -> None:
        self.assertEqual(
            validate_session_path(
                "/api/sessions/learner-1/export",
                suffix="/export",
            ),
            "learner-1",
        )
        with self.assertRaisesRegex(ValueError, "slash"):
            validate_session_path(
                "/api/sessions/learner%2Fother/export",
                suffix="/export",
            )

    def test_json_reader_requires_declared_complete_object_body(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        body = b'{"question":"simulate Brownian motion"}'
        handler.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
        }
        handler.rfile = BytesIO(body)
        self.assertEqual(
            handler._read_json_object()["question"],
            "simulate Brownian motion",
        )

    def test_json_reader_rejects_wrong_media_type_and_short_body(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.headers = {"Content-Type": "text/plain", "Content-Length": "2"}
        handler.rfile = BytesIO(b"{}")
        with self.assertRaisesRegex(ValueError, "Content-Type"):
            handler._read_json_object()

        handler.headers = {
            "Content-Type": "application/json",
            "Content-Length": "20",
        }
        handler.rfile = BytesIO(b"{}")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            handler._read_json_object()

    def test_json_reader_rejects_chunked_or_non_object_payload(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.headers = {
            "Content-Type": "application/json",
            "Content-Length": "2",
            "Transfer-Encoding": "chunked",
        }
        handler.rfile = BytesIO(b"{}")
        with self.assertRaisesRegex(ValueError, "Transfer-Encoding"):
            handler._read_json_object()

        body = b"[]"
        handler.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }
        handler.rfile = BytesIO(body)
        with self.assertRaisesRegex(ValueError, "must be an object"):
            handler._read_json_object()

    def test_static_assets_support_etag_revalidation(self) -> None:
        first = object.__new__(TutorRequestHandler)
        first.headers = {}
        first.request_id = "static-first"
        first.rate_limit_remaining = None
        first.response_started = False
        first.send_response = Mock()
        first.send_header = Mock()
        first.end_headers = Mock()
        first.wfile = BytesIO()
        first._static("/app.js")
        headers = dict(call.args for call in first.send_header.call_args_list)
        self.assertRegex(headers["ETag"], r'^"[0-9a-f]{64}"$')
        self.assertEqual(headers["Cache-Control"], "no-cache")
        self.assertGreater(len(first.wfile.getvalue()), 0)

        cached = object.__new__(TutorRequestHandler)
        cached.headers = {"If-None-Match": headers["ETag"]}
        cached.request_id = "static-cached"
        cached.rate_limit_remaining = None
        cached.response_started = False
        cached.send_response = Mock()
        cached.send_header = Mock()
        cached.end_headers = Mock()
        cached.wfile = BytesIO()
        cached._static("/app.js")
        self.assertEqual(cached.response_status, 304)
        self.assertEqual(cached.wfile.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
