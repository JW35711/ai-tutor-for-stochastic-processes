"""Typed, bounded runtime configuration for the local tutor service."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Load a small local ``.env`` file without overwriting real env values."""

    dotenv = path or ROOT / ".env"
    if not dotenv.is_file():
        return
    try:
        lines = dotenv.read_text("utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            continue
        name, value = (part.strip() for part in stripped.split("=", 1))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def _raw(name: str, default: str) -> str:
    value = os.getenv(name, default)
    return value if isinstance(value, str) else str(value)


def env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    """Read a bounded integer, stripping accidental whitespace."""

    raw = _raw(name, str(default)).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    """Read a bounded finite float, stripping accidental whitespace."""

    raw = _raw(name, str(default)).strip()
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _alias_float(primary: str, legacy: str, default: float, *, minimum: float, maximum: float) -> float:
    if primary in os.environ:
        return env_float(primary, default, minimum=minimum, maximum=maximum)
    return env_float(legacy, default, minimum=minimum, maximum=maximum)


def _safe_text(name: str, default: str = "", *, maximum: int = 512) -> str:
    value = _raw(name, default).strip()
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} contains invalid control characters or is too long")
    return value


def _validate_endpoint(value: str) -> str:
    if not value:
        return "https://api.openai.com/v1"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LLM_BASE_URL must be an absolute http(s) URL")
    if parsed.query or parsed.fragment:
        raise ValueError("LLM_BASE_URL must not contain a query or fragment")
    return value.rstrip("/")


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated settings shared by the LLM, retriever and answer limits."""

    llm_api_key: str
    llm_model: str
    llm_base_url: str
    llm_timeout: float
    llm_max_retries: int
    llm_max_response_bytes: int
    llm_max_content_chars: int
    llm_failure_cooldown: float
    retrieval_top_k: int
    answer_max_words: int
    evidence_max_chars: int

    @classmethod
    def from_env(cls, *, load_local: bool = True) -> "RuntimeConfig":
        if load_local:
            load_dotenv()
        api_key = _safe_text("LLM_API_KEY", maximum=4096)
        model = _safe_text("LLM_MODEL", maximum=256)
        if api_key and not model:
            raise ValueError("LLM_MODEL is required when LLM_API_KEY is configured")
        if model and ("\n" in model or "\r" in model or not re.fullmatch(r"[A-Za-z0-9._:/-]+", model)):
            raise ValueError("LLM_MODEL contains invalid header characters")
        if api_key and any(char in api_key for char in "\r\n"):
            raise ValueError("LLM_API_KEY contains invalid header characters")
        return cls(
            llm_api_key=api_key,
            llm_model=model,
            llm_base_url=_validate_endpoint(_safe_text("LLM_BASE_URL", "https://api.openai.com/v1")),
            llm_timeout=_alias_float("LLM_TIMEOUT", "LLM_TIMEOUT_SECONDS", 30.0, minimum=0.1, maximum=300),
            llm_max_retries=env_int("LLM_MAX_RETRIES", 2, minimum=0, maximum=5),
            llm_max_response_bytes=env_int("LLM_MAX_RESPONSE_BYTES", 1_000_000, minimum=1_024, maximum=20_000_000),
            llm_max_content_chars=env_int("LLM_MAX_CONTENT_CHARS", 12_000, minimum=256, maximum=100_000),
            llm_failure_cooldown=env_float("LLM_FAILURE_COOLDOWN_SECONDS", 60, minimum=0, maximum=3600),
            retrieval_top_k=env_int("RETRIEVAL_TOP_K", 3, minimum=1, maximum=10),
            answer_max_words=env_int("ANSWER_MAX_WORDS", 180, minimum=40, maximum=1_000),
            evidence_max_chars=env_int("EVIDENCE_MAX_CHARS", 900, minimum=200, maximum=20_000),
        )


def runtime_config() -> RuntimeConfig:
    """Build validated settings at a service/component boundary."""

    return RuntimeConfig.from_env()
