"""Optional OpenAI-compatible answer polisher using only the standard library."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .config import env_float, env_int


class OpenAICompatibleLLM:
    """Call OpenAI, DeepSeek, Qwen or another compatible chat endpoint."""

    def __init__(self) -> None:
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
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout if timeout is None else timeout,
            ) as response:
                body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                return None
            payload = json.loads(body.decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str) or len(content) > self.max_content_chars:
                return None
            return content.strip()
        except (
            urllib.error.URLError,
            TimeoutError,
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return None


def preserves_verified_facts(
    candidate: str,
    verified_result_text: str,
    sources: list[dict[str, object]],
) -> bool:
    """Accept a rewrite only when every numeric and source anchor survives.

    This is intentionally conservative. A hosted model is a presentation layer,
    not an authority over simulation results or retrieved provenance.
    """

    if not isinstance(candidate, str) or not candidate.strip():
        return False
    numeric_anchors = set(
        re.findall(
            r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?",
            verified_result_text,
            re.I,
        )
    )
    source_anchors = {
        str(source.get("source", ""))
        for source in sources
        if source.get("source")
    }
    return all(anchor in candidate for anchor in numeric_anchors | source_anchors)
