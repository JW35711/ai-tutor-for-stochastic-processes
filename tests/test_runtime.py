import json
import unittest
from concurrent.futures import ThreadPoolExecutor

from src.runtime import ServiceMetrics, SlidingWindowRateLimiter, structured_event


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class RuntimeTests(unittest.TestCase):
    def test_sliding_window_rejects_and_then_recovers(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, clock=clock)
        self.assertEqual(limiter.allow("client")[:2], (True, 1))
        self.assertEqual(limiter.allow("client")[:2], (True, 0))
        allowed, remaining, retry_after = limiter.allow("client")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertEqual(retry_after, 10)
        clock.now = 10.1
        self.assertTrue(limiter.allow("client")[0])

    def test_metrics_track_errors_and_latency(self) -> None:
        metrics = ServiceMetrics()
        metrics.record(200, 20)
        metrics.record(429, 40)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.requests, 2)
        self.assertEqual(snapshot.errors, 1)
        self.assertEqual(snapshot.rate_limited, 1)
        self.assertEqual(snapshot.average_latency_ms, 30)
        self.assertEqual(snapshot.recent_p95_latency_ms, 40)
        self.assertEqual(snapshot.latency_window_samples, 2)

    def test_metrics_p95_uses_bounded_recent_window(self) -> None:
        metrics = ServiceMetrics(latency_window=3)
        for latency in (1000, 10, 20, 30):
            metrics.record(200, latency)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.requests, 4)
        self.assertEqual(snapshot.latency_window_samples, 3)
        self.assertEqual(snapshot.recent_p95_latency_ms, 30)

    def test_metrics_window_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            ServiceMetrics(latency_window=0)

    def test_concurrent_rate_limit_never_exceeds_budget(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60, clock=clock)
        with ThreadPoolExecutor(max_workers=12) as executor:
            decisions = list(
                executor.map(
                    lambda _: limiter.allow("same-client")[0],
                    range(50),
                )
            )
        self.assertEqual(sum(decisions), 10)

    def test_client_key_capacity_is_bounded_and_recovers_after_window(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(
            limit=2,
            window_seconds=10,
            max_clients=2,
            clock=clock,
        )
        self.assertTrue(limiter.allow("client-a")[0])
        self.assertTrue(limiter.allow("client-b")[0])
        self.assertFalse(limiter.allow("client-c")[0])
        self.assertEqual(limiter.tracked_clients, 2)
        clock.now = 10.1
        self.assertTrue(limiter.allow("client-c")[0])
        self.assertEqual(limiter.tracked_clients, 1)

    def test_client_key_capacity_must_be_positive(self) -> None:
        for invalid in (0, -1, True):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "client capacity"):
                    SlidingWindowRateLimiter(max_clients=invalid)

    def test_structured_event_is_valid_json(self) -> None:
        payload = json.loads(structured_event("request", status=200))
        self.assertEqual(payload["event"], "request")
        self.assertEqual(payload["status"], 200)
        self.assertIn("timestamp", payload)


if __name__ == "__main__":
    unittest.main()
