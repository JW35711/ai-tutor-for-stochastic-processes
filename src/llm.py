"""Optional OpenAI-compatible answer polisher using only the standard library."""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from threading import Lock

from .config import env_float, env_int


class OpenAICompatibleLLM:
    """Call OpenAI, DeepSeek, Qwen or another compatible chat endpoint."""

    def __init__(
        self,
        *,
        failure_cooldown: float | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.timeout = env_float(
            "LLM_TIMEOUT_SECONDS",
            30,
            minimum=0.1,
            maximum=300,
        )
        self.max_response_bytes = env_int(
            "LLM_MAX_RESPONSE_BYTES",
            1_000_000,
            minimum=1_024,
            maximum=20_000_000,
        )
        self.max_content_chars = env_int(
            "LLM_MAX_CONTENT_CHARS",
            12_000,
            minimum=256,
            maximum=100_000,
        )
        self.failure_cooldown = (
            env_float(
                "LLM_FAILURE_COOLDOWN_SECONDS",
                60,
                minimum=0,
                maximum=3600,
            )
            if failure_cooldown is None
            else float(failure_cooldown)
        )
        if not math.isfinite(self.failure_cooldown) or not (
            0 <= self.failure_cooldown <= 3600
        ):
            raise ValueError("failure_cooldown must be between 0 and 3600")
        self._clock = clock or time.monotonic
        self._circuit_lock = Lock()
        self._retry_after = 0.0
        self._request_in_flight = False
        self._attempts = 0
        self._successes = 0
        self._failures = 0
        self._skips = 0
        self._last_failure: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def complete(
        self,
        system: str,
        user: str,
        timeout: float | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        now = self._clock()
        with self._circuit_lock:
            if now < self._retry_after or self._request_in_flight:
                self._skips += 1
                return None
            self._request_in_flight = True
            self._attempts += 1
        effective_timeout = self.timeout if timeout is None else float(timeout)
        if not math.isfinite(effective_timeout) or not 0 < effective_timeout <= 300:
            with self._circuit_lock:
                self._request_in_flight = False
            raise ValueError("completion timeout must be between 0 and 300 seconds")
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
                    }
                ).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(
                request,
                timeout=effective_timeout,
            ) as response:
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
        except urllib.error.HTTPError as error:
            # Keep a useful operational signal without storing the provider body,
            # which can contain request details or provider-generated text.
            with self._circuit_lock:
                self._failures += 1
                self._last_failure = f"HTTP_{error.code}"
                self._retry_after = self._clock() + self.failure_cooldown
                self._request_in_flight = False
            return None
        except (
            urllib.error.URLError,
            TimeoutError,
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            with self._circuit_lock:
                self._failures += 1
                self._last_failure = type(error).__name__
                self._retry_after = self._clock() + self.failure_cooldown
                self._request_in_flight = False
            return None
        except BaseException:
            with self._circuit_lock:
                self._request_in_flight = False
            raise
        with self._circuit_lock:
            self._successes += 1
            self._last_failure = None
            self._retry_after = 0.0
            self._request_in_flight = False
        return content.strip()

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
            }


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
