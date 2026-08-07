"""Small production-oriented runtime helpers for the standard-library API."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable


Clock = Callable[[], float]


class SlidingWindowRateLimiter:
    """Thread-safe, in-memory request limiter keyed by a non-secret client id."""

    def __init__(
        self,
        limit: int = 60,
        window_seconds: float = 60.0,
        clock: Clock = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("rate limit must be positive")
        if window_seconds <= 0:
            raise ValueError("rate-limit window must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> tuple[bool, int, int]:
        """Return allowed, remaining and retry-after seconds."""

        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[client_id]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0]) + 0.999))
                return False, 0, retry_after
            events.append(now)
            return True, self.limit - len(events), 0


@dataclass(frozen=True)
class MetricsSnapshot:
    requests: int
    errors: int
    rate_limited: int
    average_latency_ms: float


class ServiceMetrics:
    """Process-local request counters exposed through the health endpoint."""

    def __init__(self) -> None:
        self._requests = 0
        self._errors = 0
        self._rate_limited = 0
        self._latency_ms = 0.0
        self._lock = threading.Lock()

    def record(self, status: int, latency_ms: float) -> None:
        with self._lock:
            self._requests += 1
            self._latency_ms += max(0.0, latency_ms)
            if status >= 400:
                self._errors += 1
            if status == 429:
                self._rate_limited += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            average = self._latency_ms / self._requests if self._requests else 0.0
            return MetricsSnapshot(
                requests=self._requests,
                errors=self._errors,
                rate_limited=self._rate_limited,
                average_latency_ms=round(average, 2),
            )


def structured_event(event: str, **fields: Any) -> str:
    """Render one compact JSON event; callers decide where it is emitted."""

    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        **fields,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
