import unittest
from unittest.mock import Mock

from server import RATE_LIMITER, TutorHTTPServer, TutorRequestHandler


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


if __name__ == "__main__":
    unittest.main()
