"""Minimal HTTP API and web server for the Stochastic Tutor Agent."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import time
import uuid
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.assessment import AssessmentEngine
from src.agent import StochasticTutorAgent
from src.evaluation_manifest import load_evaluation_manifest
from src.module_registry import module_catalog
from src.runtime import ServiceMetrics, SlidingWindowRateLimiter, structured_event
from src.tool_catalog import build_tool_catalog
from src.recommendation import recommend_next


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
AGENT = StochasticTutorAgent()
ASSESSMENTS = AssessmentEngine()
EVALUATION = load_evaluation_manifest()
RATE_LIMITER = SlidingWindowRateLimiter(
    limit=max(1, int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "60")))
)
METRICS = ServiceMetrics()
MAX_QUESTION_CHARS = max(100, int(os.getenv("MAX_QUESTION_CHARS", "4000")))


class TutorRequestHandler(BaseHTTPRequestHandler):
    server_version = "StochasticTutor/0.2"

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
        print(structured_event("http_request", **fields), flush=True)

    def _internal_error(self, error: Exception) -> None:
        self.error_type = type(error).__name__
        if not self.response_started:
            self._json(
                {"error": "internal server error", "request_id": self.request_id},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _common_headers(self) -> None:
        self.send_header("X-Request-ID", self.request_id)
        self.send_header("X-API-Version", "1")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'",
        )
        if self.rate_limit_remaining is not None:
            self.send_header("X-RateLimit-Limit", str(RATE_LIMITER.limit))
            self.send_header("X-RateLimit-Remaining", str(self.rate_limit_remaining))

    def _json(
        self,
        payload: object,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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

    def _static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path[1:])
        candidate = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
            self._json({"error": "invalid path"}, HTTPStatus.BAD_REQUEST)
            return
        if not candidate.is_file():
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        body = candidate.read_bytes()
        content_type, _ = mimetypes.guess_type(candidate.name)
        self.response_status = int(HTTPStatus.OK)
        self.response_started = True
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
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
        if path == "/health":
            self._json(
                {
                    "status": "ok",
                    "service": "stochastic-tutor-agent",
                    "modules": 11,
                    "tools": len(AGENT.tools),
                    "persistent_memory": True,
                    "multi_turn_context": True,
                    "workflow": {"nodes": list(AGENT.workflow.node_names)},
                    "knowledge": AGENT.knowledge.stats(),
                    "llm": {
                        "enabled": AGENT.llm.enabled,
                        "mode": "verified_rewrite",
                    },
                    "evaluation": EVALUATION,
                    "runtime": asdict(METRICS.snapshot()),
                }
            )
        elif path == "/api/topics":
            self._json({"modules": module_catalog()})
        elif path == "/api/tools":
            self._json({"tools": build_tool_catalog(AGENT.tools)})
        elif path == "/api/profile":
            session_id = parse_qs(parsed.query).get("session_id", [""])[0]
            if not session_id:
                self._json(
                    {"error": "session_id is required"}, HTTPStatus.BAD_REQUEST
                )
            else:
                profile = AGENT.memory.profile(session_id)
                self._json(
                    {
                        "profile": profile,
                        "history": AGENT.memory.history(session_id),
                        "recommendation": recommend_next(profile),
                    }
                )
        elif path == "/api/quiz":
            module_id = parse_qs(parsed.query).get("module_id", [""])[0]
            try:
                self._json({"quiz": ASSESSMENTS.question(module_id)})
            except ValueError as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
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
        if path not in {"/api/chat", "/api/quiz/submit"}:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        allowed, remaining, retry_after = RATE_LIMITER.allow(self.client_address[0])
        self.rate_limit_remaining = remaining
        if not allowed:
            self._json(
                {"error": "rate limit exceeded", "request_id": self.request_id},
                HTTPStatus.TOO_MANY_REQUESTS,
                {"Retry-After": str(retry_after)},
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            if path == "/api/chat":
                question = str(payload.get("question", "")).strip()
                if not question:
                    raise ValueError("question is required")
                if len(question) > MAX_QUESTION_CHARS:
                    raise ValueError(
                        f"question exceeds {MAX_QUESTION_CHARS} characters"
                    )
                raw_session_id = payload.get("session_id")
                if raw_session_id is not None and not isinstance(raw_session_id, str):
                    raise ValueError("session_id must be a string")
                if raw_session_id and len(raw_session_id) > 128:
                    raise ValueError("session_id is too long")
                response = AGENT.answer(
                    question,
                    session_id=raw_session_id,
                )
            else:
                session_id = str(payload.get("session_id") or uuid.uuid4())
                result = ASSESSMENTS.grade(
                    str(payload.get("question_id", "")),
                    payload.get("answer_index"),
                )
                AGENT.memory.record_assessment(
                    session_id=session_id,
                    question_id=result["question_id"],
                    module_id=result["module_id"],
                    answer_index=result["answer_index"],
                    correct=result["correct"],
                )
                profile = AGENT.memory.profile(session_id)
                response = {
                    "session_id": session_id,
                    "result": result,
                    "memory": profile,
                    "recommendation": recommend_next(profile),
                }
            response["request_id"] = self.request_id
            self._json(response)
        except (ValueError, json.JSONDecodeError) as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

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
        prefix = "/api/sessions/"
        if not path.startswith(prefix):
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        session_id = unquote(path[len(prefix) :]).strip()
        if not session_id or "/" in session_id or len(session_id) > 128:
            self._json({"error": "invalid session id"}, HTTPStatus.BAD_REQUEST)
            return
        AGENT.memory.reset(session_id)
        self._json({"status": "reset", "session_id": session_id})

    def log_message(self, format: str, *args: object) -> None:
        # Request completion is emitted once as structured JSON in _end_request.
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), TutorRequestHandler)
    print(f"Stochastic Tutor Agent: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
