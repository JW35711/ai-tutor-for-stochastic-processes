"""Optional OpenAI-compatible answer polisher using only the standard library."""

from __future__ import annotations

import json
import os
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
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
            return None
