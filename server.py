"""Minimal HTTP API and web server for the Stochastic Tutor Agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import signal
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.agent import StochasticTutorAgent
from src.assessment import AssessmentEngine
from src.config import env_float, env_int
from src.curriculum import curriculum_catalog
from src.experiments import ExperimentRegistry
from src.evaluation_manifest import load_evaluation_manifest
from src.module_registry import module_catalog
from src.openapi import OPENAPI_SPEC
from src.runtime import ServiceMetrics, SlidingWindowRateLimiter, structured_event
from src.tool_catalog import build_tool_catalog
from src.recommendation import recommend_next, recommend_next_knowledge_point
from src.version import API_VERSION, APP_VERSION
from src.validation import (
    MAX_QUESTION_CHARS,
    validate_question,
    validate_session_id,
)


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
AGENT = StochasticTutorAgent()
ASSESSMENTS = AssessmentEngine()
EXPERIMENTS = ExperimentRegistry()
EVALUATION = load_evaluation_manifest()
EVALUATION["corpus_match"] = (
    EVALUATION["corpus_sha256"] == AGENT.knowledge.corpus_sha256
)
EVALUATION["textbook_chunks"] = AGENT.knowledge.stats()["textbook_chunks"]
RATE_LIMITER = SlidingWindowRateLimiter(
    limit=env_int(
        "API_RATE_LIMIT_PER_MINUTE",
        60,
        minimum=1,
        maximum=1_000_000,
    ),
    max_clients=env_int(
        "API_RATE_LIMIT_CLIENT_CAP",
        10_000,
        minimum=1,
        maximum=1_000_000,
    ),
)
METRICS = ServiceMetrics()
MAX_JSON_BODY_BYTES = env_int(
    "MAX_JSON_BODY_BYTES",
    1_000_000,
    minimum=1_024,
    maximum=20_000_000,
)
REQUEST_SOCKET_TIMEOUT_SECONDS = env_float(
    "REQUEST_SOCKET_TIMEOUT_SECONDS",
    10,
    minimum=1,
    maximum=300,
)
MEMORY_RETENTION_DAYS = env_int(
    "MEMORY_RETENTION_DAYS",
    0,
    minimum=0,
    maximum=3650,
)
PURGED_SESSIONS_ON_STARTUP = (
    AGENT.memory.purge_stale(MEMORY_RETENTION_DAYS)
    if MEMORY_RETENTION_DAYS
    else 0
)


def readiness_report() -> dict[str, object]:
    """Report whether every local dependency is safe to receive traffic."""

    expected_modules = {f"module{index:02d}" for index in range(11)}
    checks = {
        "memory": AGENT.memory.is_ready(),
        "module_catalog": {
            item["module_id"] for item in module_catalog()
        } == expected_modules,
        "curriculum": {
            item["module_id"] for item in curriculum_catalog()["modules"]
        } == expected_modules,
        "tool_registry": len(AGENT.tools) == 15,
        "knowledge_index": AGENT.knowledge.stats()["entries"] >= 11,
        "assessment_bank": set(ASSESSMENTS.by_module) == expected_modules,
        "evaluation_corpus": bool(EVALUATION["corpus_match"]),
    }
    return {"ready": all(checks.values()), "checks": checks}


def prometheus_metrics() -> str:
    """Render low-cardinality process metrics without learner identifiers."""

    runtime = asdict(METRICS.snapshot())
    knowledge = AGENT.knowledge.stats()
    embedding_circuit = knowledge["embedding_circuit"]
    llm_circuit = AGENT.llm.stats()
    readiness = readiness_report()
    values = (
        (
            "stochlab_http_requests_total",
            runtime["requests"],
            "HTTP requests",
            "counter",
        ),
        (
            "stochlab_http_errors_total",
            runtime["errors"],
            "HTTP errors",
            "counter",
        ),
        (
            "stochlab_http_rate_limited_total",
            runtime["rate_limited"],
            "Rate-limited HTTP requests",
            "counter",
        ),
        (
            "stochlab_http_latency_average_ms",
            runtime["average_latency_ms"],
            "All-time average HTTP latency in milliseconds",
            "gauge",
        ),
        (
            "stochlab_http_latency_recent_p95_ms",
            runtime["recent_p95_latency_ms"],
            "Recent bounded-window p95 latency in milliseconds",
            "gauge",
        ),
        (
            "stochlab_http_latency_window_samples",
            runtime["latency_window_samples"],
            "Samples retained in the latency window",
            "gauge",
        ),
        (
            "stochlab_rate_limiter_tracked_clients",
            RATE_LIMITER.tracked_clients,
            "Client keys tracked by the process-local limiter",
            "gauge",
        ),
        (
            "stochlab_knowledge_entries",
            knowledge["entries"],
            "Indexed RAG entries",
            "gauge",
        ),
        (
            "stochlab_rag_embedding_query_failures_total",
            embedding_circuit["query_failures"],
            "Hosted query-embedding failures",
            "counter",
        ),
        (
            "stochlab_rag_embedding_query_skips_total",
            embedding_circuit["query_skips"],
            "Query embeddings skipped by the circuit",
            "counter",
        ),
        (
            "stochlab_llm_provider_attempts_total",
            llm_circuit["attempts"],
            "Hosted LLM rewrite attempts",
            "counter",
        ),
        (
            "stochlab_llm_provider_failures_total",
            llm_circuit["failures"],
            "Hosted LLM rewrite failures",
            "counter",
        ),
        (
            "stochlab_llm_provider_skips_total",
            llm_circuit["skips"],
            "Hosted LLM rewrites skipped by the circuit",
            "counter",
        ),
        (
            "stochlab_ready",
            int(bool(readiness["ready"])),
            "Whether all local readiness checks pass",
            "gauge",
        ),
    )
    lines: list[str] = []
    for name, value, help_text, metric_type in values:
        lines.extend(
            (
                f"# HELP {name} {help_text}",
                f"# TYPE {name} {metric_type}",
                f"{name} {value}",
            )
        )
    return "\n".join(lines) + "\n"


def validate_session_path(path: str, *, suffix: str = "") -> str:
    prefix = "/api/sessions/"
    if not path.startswith(prefix) or (suffix and not path.endswith(suffix)):
        raise ValueError("invalid session path")
    end = -len(suffix) if suffix else None
    session_id = validate_session_id(
        unquote(path[len(prefix) : end]),
        required=True,
    )
    assert session_id is not None
    return session_id


def validate_payload_fields(
    payload: dict[str, object],
    *,
    allowed: set[str],
    required: set[str],
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unexpected JSON fields: {', '.join(unknown)}")
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"missing required JSON fields: {', '.join(missing)}")


class TutorRequestHandler(BaseHTTPRequestHandler):
    server_version = f"StochasticTutor/{APP_VERSION}"

    def version_string(self) -> str:
        """Avoid disclosing the interpreter version in the Server header."""

        return self.server_version

    def _begin_request(self) -> None:
        supplied = self.headers.get("X-Request-ID", "")
        self.request_id = (
            supplied
            if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied)
            else uuid.uuid4().hex
        )
        self.request_started = time.monotonic()
        self.response_status = int(HTTPStatus.INTERNAL_SERVER_ERROR)
        self.response_started = False
        self.error_type: str | None = None
        self.rate_limit_remaining: int | None = None
        self.response_observability: dict[str, object] | None = None

    def _end_request(self) -> None:
        latency_ms = (time.monotonic() - self.request_started) * 1000
        METRICS.record(self.response_status, latency_ms)
        fields = {
            "request_id": self.request_id,
            "method": self.command,
            "path": urlparse(self.path).path,
            "status": self.response_status,
            "latency_ms": round(latency_ms, 2),
        }
        if self.error_type:
            fields["error_type"] = self.error_type
        if self.response_observability:
            for key in (
                "intent", "concept_sub_intent", "module_id", "concept_id",
                "llm_enabled", "llm_applied", "provider", "model",
                "retry_count", "latency_ms", "tool_called", "source_locators",
            ):
                if key in self.response_observability:
                    if key == "latency_ms":
                        fields["latency_breakdown_ms"] = self.response_observability[key]
                    else:
                        fields[key] = self.response_observability[key]
        print(structured_event("http_request", **fields), flush=True)

    def _internal_error(self, error: Exception) -> None:
        if not self.response_started:
            self._error(
                "internal server error",
                HTTPStatus.INTERNAL_SERVER_ERROR,
                code="internal_error",
            )
        # Preserve the concrete exception class in logs without exposing it to
        # the caller. The public envelope intentionally stays provider-neutral.
        self.error_type = type(error).__name__

    def _common_headers(self) -> None:
        self.send_header("X-Request-ID", self.request_id)
        self.send_header("X-API-Version", API_VERSION)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; connect-src 'self'",
        )
        if self.rate_limit_remaining is not None:
            self.send_header("X-RateLimit-Limit", str(RATE_LIMITER.limit))
            self.send_header("X-RateLimit-Remaining", str(self.rate_limit_remaining))

    def _allow_api_request(self) -> bool:
        allowed, remaining, retry_after = RATE_LIMITER.allow(self.client_address[0])
        self.rate_limit_remaining = remaining
        if allowed:
            return True
        self._error(
            "rate limit exceeded",
            HTTPStatus.TOO_MANY_REQUESTS,
            code="rate_limited",
            extra_headers={"Retry-After": str(retry_after)},
        )
        return False

    def _error(
        self,
        message: str,
        status: HTTPStatus,
        code: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """Return one traceable, backwards-compatible error envelope."""
        self.error_type = code
        self._json(
            {
                "error": message,
                "error_code": code,
                "request_id": self.request_id,
            },
            status,
            extra_headers,
        )

    def _json(
        self,
        payload: object,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.response_status = int(status)
        self.response_started = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._common_headers()
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _text(
        self,
        body: str,
        *,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = body.encode("utf-8")
        self.response_status = int(status)
        self.response_started = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self._common_headers()
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json_object(self) -> dict[str, object]:
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0]
        if media_type.strip().lower() != "application/json":
            raise ValueError("Content-Type must be application/json")
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding is not supported")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError) as error:
            raise ValueError("invalid request size") from error
        if length <= 0 or length > MAX_JSON_BODY_BYTES:
            raise ValueError("invalid request size")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("incomplete request body")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path[1:])
        candidate = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
            self._error("invalid path", HTTPStatus.BAD_REQUEST, "invalid_path")
            return
        if not candidate.is_file():
            self._error("not found", HTTPStatus.NOT_FOUND, "not_found")
            return
        body = candidate.read_bytes()
        etag = f'"{hashlib.sha256(body).hexdigest()}"'
        if self.headers.get("If-None-Match") == etag:
            self.response_status = int(HTTPStatus.NOT_MODIFIED)
            self.response_started = True
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self._common_headers()
            self.end_headers()
            return
        content_type, _ = mimetypes.guess_type(candidate.name)
        if content_type and content_type.startswith("text/"):
            content_type = f"{content_type}; charset=utf-8"
        elif content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self.response_status = int(HTTPStatus.OK)
        self.response_started = True
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        self._common_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._begin_request()
        try:
            self._do_get()
        except Exception as error:
            self._internal_error(error)
        finally:
            self._end_request()

    def _do_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/") and not self._allow_api_request():
            return
        if path == "/live":
            self._json({"status": "ok", "service": "stochastic-tutor-agent"})
        elif path == "/openapi.json":
            self._json(OPENAPI_SPEC)
        elif path == "/ready":
            readiness = readiness_report()
            self._json(
                {"status": "ready" if readiness["ready"] else "not_ready", **readiness},
                HTTPStatus.OK
                if readiness["ready"]
                else HTTPStatus.SERVICE_UNAVAILABLE,
            )
        elif path == "/health":
            readiness = readiness_report()
            self._json(
                {
                    "status": "ok",
                    "service_ready": bool(readiness["ready"]),
                    "curriculum_loaded": bool(readiness["checks"]["curriculum"]),
                    "knowledge_base_loaded": bool(readiness["checks"]["knowledge_index"]),
                    "service": "stochastic-tutor-agent",
                    "version": APP_VERSION,
                    "api_version": API_VERSION,
                    "modules": 11,
                    "tools": len(AGENT.tools),
                    "persistent_memory": True,
                    "multi_turn_context": True,
                    "learner_data": {
                        "retention_days": MEMORY_RETENTION_DAYS or None,
                        "max_events_per_type_per_session": (
                            AGENT.memory.max_events_per_session
                        ),
                        "schema_version": AGENT.memory.schema_version,
                        "purged_sessions_on_startup": PURGED_SESSIONS_ON_STARTUP,
                    },
                    "workflow": {
                        "nodes": list(AGENT.workflow.get_graph().nodes),
                        "runtime": "langgraph",
                    },
                    "knowledge": AGENT.knowledge.stats(),
                    "llm": {
                        "enabled": AGENT.llm.enabled,
                        "configured": bool(AGENT.config.llm_api_key and AGENT.config.llm_model),
                        "provider": AGENT.llm.stats().get("provider"),
                        "model": AGENT.llm.stats().get("model"),
                        "mode": "verified_rewrite",
                        "max_content_chars": AGENT.llm.max_content_chars,
                        "provider_circuit": AGENT.llm.stats(),
                    },
                    "evaluation": EVALUATION,
                    "assessment": {
                        "questions": len(ASSESSMENTS.questions),
                        "bank_sha256": ASSESSMENTS.bank_sha256,
                    },
                    "readiness": readiness,
                    "runtime": asdict(METRICS.snapshot()),
                    "rate_limit": {
                        "requests_per_minute": RATE_LIMITER.limit,
                        "client_capacity": RATE_LIMITER.max_clients,
                        "tracked_clients": RATE_LIMITER.tracked_clients,
                    },
                }
            )
        elif path == "/metrics":
            self._text(
                prometheus_metrics(),
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )
        elif path == "/api/topics":
            self._json({"modules": module_catalog()})
        elif path == "/api/curriculum":
            self._json(curriculum_catalog())
        elif path == "/api/tools":
            self._json({"tools": build_tool_catalog(AGENT.tools)})
        elif path == "/api/experiments":
            tool_parameters = {
                item["key"]: item.get("parameters", [])
                for item in build_tool_catalog(AGENT.tools)
            }
            self._json({
                "experiments": [
                    {
                        **EXPERIMENTS.summary(
                            item,
                            tool_parameters.get(str(item.get("simulation_engine")), []),
                        ),
                        "section": item.get("section"),
                        "visualization_id": item.get("visualization_id"),
                    }
                    for item in EXPERIMENTS.experiments
                ]
            })
        elif path == "/api/profile":
            session_id = parse_qs(parsed.query).get("session_id", [""])[0]
            ui_language = parse_qs(parsed.query).get("ui_language", ["en"])[0]
            try:
                session_id = validate_session_id(session_id, required=True)
            except ValueError as error:
                self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_session")
            else:
                assert session_id is not None
                profile = AGENT.memory.profile(session_id)
                self._json(
                    {
                        "profile": profile,
                        "history": AGENT.memory.history(session_id),
                        "assessments": AGENT.memory.assessment_history(session_id),
                        "recommendation": recommend_next_knowledge_point(AGENT.curriculum_agent, profile, ui_language),
                    }
                )
        elif path == "/api/quiz":
            query = parse_qs(parsed.query)
            module_id = query.get("module_id", [""])[0]
            concept_id = query.get("concept_id", [""])[0]
            try:
                self._json({"quiz": ASSESSMENTS.question_for_concept(concept_id) if concept_id else ASSESSMENTS.question(module_id)})
            except ValueError as error:
                self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_module")
        elif path == "/api/practice":
            query = parse_qs(parsed.query)
            concept_id = query.get("concept_id", [""])[0]
            try:
                self._json({"practice": ASSESSMENTS.practice_for_concept(concept_id)})
            except ValueError as error:
                self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_concept")
        elif path.startswith("/api/sessions/") and path.endswith("/export"):
            try:
                session_id = validate_session_path(path, suffix="/export")
            except ValueError as error:
                self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_session")
            else:
                profile = AGENT.memory.profile(session_id)
                self._json(
                    {
                        "exported_at": datetime.now(timezone.utc).isoformat(
                            timespec="seconds"
                        ),
                        "corpus_sha256": AGENT.knowledge.corpus_sha256,
                        "assessment_bank_sha256": ASSESSMENTS.bank_sha256,
                        "retention_days": MEMORY_RETENTION_DAYS or None,
                        "max_events_per_type": AGENT.memory.max_events_per_session,
                        "learner_data": AGENT.memory.snapshot(session_id),
                        "recommendation": recommend_next_knowledge_point(AGENT.curriculum_agent, profile),
                        "request_id": self.request_id,
                    }
                )
        else:
            self._static(path)

    def do_POST(self) -> None:  # noqa: N802
        self._begin_request()
        try:
            self._do_post()
        except Exception as error:
            self._internal_error(error)
        finally:
            self._end_request()

    def _do_post(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/chat", "/api/quiz/submit", "/api/practice", "/api/hint"}:
            self._error("not found", HTTPStatus.NOT_FOUND, "not_found")
            return
        if not self._allow_api_request():
            return
        try:
            payload = self._read_json_object()
            if path == "/api/chat":
                validate_payload_fields(
                    payload,
                    allowed={"question", "session_id", "ui_language", "action_type", "concept_id", "experiment_id"},
                    required={"question"},
                )
                question = validate_question(payload.get("question"))
                raw_session_id = validate_session_id(payload.get("session_id"))
                response = AGENT.answer(
                    question,
                    session_id=raw_session_id,
                    ui_language=str(payload.get("ui_language") or "en"),
                    action_type=payload.get("action_type"),
                    concept_id=payload.get("concept_id"),
                    experiment_id=payload.get("experiment_id"),
                )
            elif path == "/api/hint":
                validate_payload_fields(
                    payload,
                    allowed={"concept_id", "question_id", "hint_level", "session_id", "ui_language"},
                    required={"concept_id"},
                )
                session_id = validate_session_id(payload.get("session_id")) or str(uuid.uuid4())
                concept_id = payload.get("concept_id")
                if not isinstance(concept_id, str) or concept_id not in AGENT.curriculum_agent.concepts:
                    raise ValueError("concept_id is not in the curriculum")
                hint = ASSESSMENTS.hint(
                    concept_id=concept_id,
                    question_id=payload.get("question_id"),
                    hint_level=payload.get("hint_level", 1),
                    language=str(payload.get("ui_language") or "en"),
                )
                AGENT.memory.record_learning_event(
                    session_id=session_id, event_type="HINT_REQUEST",
                    concept_id=concept_id, question_id=hint["question_id"],
                    payload={"hint_level": hint["hint_level"]},
                )
                AGENT.memory.record_hint_used(session_id=session_id, concept_id=concept_id, question_id=hint["question_id"], hint_level=hint["hint_level"])
                hint["session_id"] = session_id
                hint["event_type"] = "HINT_USED"
                response = hint
            elif path == "/api/practice":
                validate_payload_fields(
                    payload,
                    allowed={"concept_id", "question_id", "student_answer", "hint_level", "attempt_number", "session_id", "ui_language", "reference_shown"},
                    required={"concept_id", "student_answer"},
                )
                session_id = validate_session_id(payload.get("session_id")) or str(uuid.uuid4())
                concept_id = payload.get("concept_id")
                if not isinstance(concept_id, str) or concept_id not in AGENT.curriculum_agent.concepts:
                    raise ValueError("concept_id is not in the curriculum")
                question_id = payload.get("question_id")
                if not isinstance(question_id, str):
                    question = ASSESSMENTS.practice_for_concept(concept_id)
                    question_id = question["id"]
                result = ASSESSMENTS.grade_free_text(question_id, payload.get("student_answer", ""))
                reference_shown = bool(payload.get("reference_shown", False))
                result.update({"answer_index": 0, "hints_used": max(0, int(payload.get("hint_level", 0) or 0), 3 if reference_shown else 0), "reference_shown": reference_shown, "attempt_number": payload.get("attempt_number", 1), "event_type": "PRACTICE_ANSWER", "grading_method": "deterministic_keyword_or_relation_check"})
                response = AGENT.handle_assessment(result, session_id, str(payload.get("ui_language") or "en"))
                # Keep the reference answer out of the rendered feedback until
                # the learner explicitly asks to see it.
                response["reference_answer"] = result.get("expected_answer")
            else:
                validate_payload_fields(
                    payload,
                    allowed={"question_id", "answer_index", "session_id", "ui_language"},
                    required={"question_id", "answer_index"},
                )
                session_id = validate_session_id(payload.get("session_id"))
                session_id = session_id or str(uuid.uuid4())
                question_id = payload.get("question_id")
                if not isinstance(question_id, str):
                    raise ValueError("question_id must be a string")
                result = ASSESSMENTS.grade(
                    question_id,
                    payload.get("answer_index"),
                )
                response = AGENT.handle_assessment(result, session_id, str(payload.get("ui_language") or "en"))
            response["request_id"] = self.request_id
            if isinstance(response.get("observability"), dict):
                response["observability"]["request_id"] = self.request_id
                self.response_observability = response["observability"]
            self._json(response)
        except (ValueError, json.JSONDecodeError) as error:
            self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_request")

    def do_DELETE(self) -> None:  # noqa: N802
        self._begin_request()
        try:
            self._do_delete()
        except Exception as error:
            self._internal_error(error)
        finally:
            self._end_request()

    def _do_delete(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self._allow_api_request():
            return
        prefix = "/api/sessions/"
        if not path.startswith(prefix):
            self._error("not found", HTTPStatus.NOT_FOUND, "not_found")
            return
        try:
            session_id = validate_session_path(path)
        except ValueError as error:
            self._error(str(error), HTTPStatus.BAD_REQUEST, "invalid_session")
            return
        AGENT.memory.reset(session_id)
        self._json({"status": "reset", "session_id": session_id})

    def log_message(self, format: str, *args: object) -> None:
        # Request completion is emitted once as structured JSON in _end_request.
        return


class TutorHTTPServer(ThreadingHTTPServer):
    # Let server_close wait for active handlers, while the per-connection
    # timeout prevents an idle client from blocking shutdown indefinitely.
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = True

    def get_request(self) -> tuple[object, object]:
        request, client_address = super().get_request()
        request.settimeout(REQUEST_SOCKET_TIMEOUT_SECONDS)
        return request, client_address


def _request_shutdown(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _request_shutdown)
    server = TutorHTTPServer((args.host, args.port), TutorRequestHandler)
    print(f"Stochastic Tutor Agent: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    print(
        structured_event(
            "service_started",
            host=args.host,
            port=args.port,
            modules=11,
            tools=len(AGENT.tools),
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
        AGENT.memory.close()
        print(structured_event("service_stopped"), flush=True)


if __name__ == "__main__":
    main()
