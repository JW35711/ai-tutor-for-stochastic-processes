"""Optional OpenAI-compatible answer polisher using only the standard library."""

from __future__ import annotations

import json
import math
import os
import re
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from threading import Lock
from urllib.parse import urlparse

from .config import RuntimeConfig, runtime_config


class OpenAICompatibleLLM:
    """Call OpenAI, DeepSeek, Qwen or another compatible chat endpoint."""

    def __init__(
        self,
        *,
        config: RuntimeConfig | None = None,
        failure_cooldown: float | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config or runtime_config()
        self.api_key = self.config.llm_api_key
        self.model = self.config.llm_model
        self.base_url = self.config.llm_base_url
        self.timeout = self.config.llm_timeout
        self.max_retries = self.config.llm_max_retries
        self.max_response_bytes = self.config.llm_max_response_bytes
        self.max_content_chars = self.config.llm_max_content_chars
        self.failure_cooldown = (
            self.config.llm_failure_cooldown
            if failure_cooldown is None
            else float(failure_cooldown)
        )
        if not math.isfinite(self.failure_cooldown) or not (
            0 <= self.failure_cooldown <= 3600
        ):
            raise ValueError("failure_cooldown must be between 0 and 3600")
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._circuit_lock = Lock()
        self._retry_after = 0.0
        self._request_in_flight = False
        self._attempts = 0
        self._successes = 0
        self._failures = 0
        self._skips = 0
        self._last_failure: str | None = None
        self._last_request: dict[str, object] = {
            "provider": urlparse(self.base_url).netloc,
            "model": self.model or None,
            "status": "not_started",
            "retry_count": 0,
            "latency_ms": 0.0,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def complete(
        self,
        system: str,
        user: str,
        timeout: float | None = None,
    ) -> str | None:
        started = time.perf_counter()
        if not self.enabled:
            self._set_last_request("disabled", 0, started)
            return None
        now = self._clock()
        with self._circuit_lock:
            if now < self._retry_after or self._request_in_flight:
                self._skips += 1
                skipped = True
            else:
                skipped = False
                self._request_in_flight = True
                self._attempts += 1
        if skipped:
            self._set_last_request("circuit_open", 0, started)
            return None
        effective_timeout = self.timeout if timeout is None else float(timeout)
        if not math.isfinite(effective_timeout) or not 0 < effective_timeout <= 300:
            with self._circuit_lock:
                self._request_in_flight = False
            raise ValueError("completion timeout must be between 0 and 300 seconds")
        for attempt in range(self.max_retries + 1):
            try:
                request = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=json.dumps(
                        {
                            "model": self.model,
                            "temperature": 0.2,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": user},
                            ],
                        },
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=effective_timeout) as response:
                    body = response.read(self.max_response_bytes + 1)
                if len(body) > self.max_response_bytes:
                    raise RuntimeError("LLM response exceeds configured limit")
                payload = json.loads(body.decode("utf-8"))
                content = payload["choices"][0]["message"]["content"]
                if (
                    not isinstance(content, str)
                    or not content.strip()
                    or len(content) > self.max_content_chars
                ):
                    raise RuntimeError("LLM content violates configured contract")
                usage = payload.get("usage") if isinstance(payload, dict) else None
                self._finish_success(attempt, started, usage if isinstance(usage, dict) else None)
                return content.strip()
            except urllib.error.HTTPError as error:
                status_code = int(error.code or 0)
                retryable = status_code == 429 or 500 <= status_code < 600
                if retryable and attempt < self.max_retries:
                    self._sleep(min(2.0, 0.2 * (2**attempt)))
                    continue
                self._finish_failure(f"HTTP_{status_code}", attempt, started)
                return None
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as error:
                if attempt < self.max_retries:
                    self._sleep(min(2.0, 0.2 * (2**attempt)))
                    continue
                self._finish_failure(type(error).__name__, attempt, started)
                return None
            except (AttributeError, KeyError, IndexError, TypeError, ValueError,
                    UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as error:
                self._finish_failure(type(error).__name__, attempt, started)
                return None
            except BaseException:
                with self._circuit_lock:
                    self._request_in_flight = False
                raise
        self._finish_failure("retry_exhausted", self.max_retries, started)
        return None

    def _set_last_request(self, status: str, retry_count: int, started: float, **extra: object) -> None:
        with self._circuit_lock:
            self._last_request = {
                "provider": urlparse(self.base_url).netloc,
                "model": self.model or None,
                "status": status,
                "retry_count": retry_count,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input_tokens": extra.get("input_tokens"),
                "output_tokens": extra.get("output_tokens"),
                "total_tokens": extra.get("total_tokens"),
            }

    def _finish_success(self, attempt: int, started: float, usage: dict[str, object] | None) -> None:
        with self._circuit_lock:
            self._successes += 1
            self._last_failure = None
            self._retry_after = 0.0
            self._request_in_flight = False
        self._set_last_request(
            "success",
            attempt,
            started,
            input_tokens=usage.get("prompt_tokens") if usage else None,
            output_tokens=usage.get("completion_tokens") if usage else None,
            total_tokens=usage.get("total_tokens") if usage else None,
        )

    def _finish_failure(self, reason: str, attempt: int, started: float) -> None:
        with self._circuit_lock:
            self._failures += 1
            self._last_failure = reason
            self._retry_after = self._clock() + self.failure_cooldown
            self._request_in_flight = False
        self._set_last_request("failed", attempt, started)

    def stats(self) -> dict[str, object]:
        """Return bounded provider state without prompts or credentials."""

        with self._circuit_lock:
            retry_after_seconds = max(0.0, self._retry_after - self._clock())
            if not self.enabled:
                state = "disabled"
            elif self._request_in_flight:
                state = "request_in_flight"
            elif retry_after_seconds > 0:
                state = "open"
            else:
                state = "closed"
            return {
                "state": state,
                "cooldown_seconds": self.failure_cooldown,
                "retry_after_seconds": round(retry_after_seconds, 3),
                "attempts": self._attempts,
                "successes": self._successes,
                "failures": self._failures,
                "skips": self._skips,
                "last_failure": self._last_failure,
                "retry_count": self._last_request.get("retry_count", 0),
                "provider": self._last_request.get("provider"),
                "model": self._last_request.get("model"),
            }

    def last_request(self) -> dict[str, object]:
        """Return safe timing/usage metadata without credentials or prompts."""

        with self._circuit_lock:
            return dict(self._last_request)


def preserves_verified_facts(
    candidate: str,
    verified_result_text: str,
    sources: list[dict[str, object]],
) -> bool:
    """Accept a rewrite only when the verified result block remains immutable.

    This is intentionally conservative. A hosted model is a presentation layer,
    not an authority over simulation results or retrieved provenance.
    """

    if not isinstance(candidate, str) or not candidate.strip():
        return False
    verified_block = verified_result_text.strip()
    if not verified_block or verified_block not in candidate:
        return False
    numeric_pattern = r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?"
    numeric_anchors = set(
        re.findall(numeric_pattern, verified_result_text, re.I)
    )
    candidate_numbers = set(re.findall(numeric_pattern, candidate, re.I))
    source_anchors = {
        str(source.get("source", ""))
        for source in sources
        if source.get("source")
    }
    return numeric_anchors <= candidate_numbers and all(
        anchor in candidate for anchor in source_anchors
    )
