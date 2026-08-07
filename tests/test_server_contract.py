import unittest
from unittest.mock import Mock

from server import EVALUATION, RATE_LIMITER, TutorHTTPServer, TutorRequestHandler


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

    def test_invalid_supplied_request_id_is_replaced(self) -> None:
        handler = object.__new__(TutorRequestHandler)
        handler.headers = {"X-Request-ID": "contains spaces and is invalid"}
        handler._begin_request()
        self.assertRegex(handler.request_id, r"^[0-9a-f]{32}$")

    def test_server_request_threads_do_not_block_shutdown(self) -> None:
        self.assertTrue(TutorHTTPServer.daemon_threads)
        self.assertTrue(TutorHTTPServer.allow_reuse_address)

    def test_dashboard_evaluation_matches_live_corpus(self) -> None:
        self.assertTrue(EVALUATION["corpus_match"])

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
        self.assertIn("Retry-After", args[2])


if __name__ == "__main__":
    unittest.main()
