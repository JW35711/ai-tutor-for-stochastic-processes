"""Optional OpenAI-compatible answer polisher using only the standard library."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


class OpenAICompatibleLLM:
    """Call OpenAI, DeepSeek, Qwen or another compatible chat endpoint."""

    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def complete(self, system: str, user: str, timeout: int = 30) -> str | None:
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
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"].strip()
        except (
            urllib.error.URLError,
            TimeoutError,
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None


def preserves_verified_facts(
    candidate: str,
    verified_draft: str,
    sources: list[dict[str, object]],
) -> bool:
    """Accept a rewrite only when every numeric and source anchor survives.

    This is intentionally conservative. A hosted model is a presentation layer,
    not an authority over simulation results or retrieved provenance.
    """

    if not isinstance(candidate, str) or not candidate.strip():
        return False
    numeric_anchors = set(
        re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", verified_draft, re.I)
    )
    source_anchors = {
        str(source.get("source", ""))
        for source in sources
        if source.get("source")
    }
    return all(anchor in candidate for anchor in numeric_anchors | source_anchors)
