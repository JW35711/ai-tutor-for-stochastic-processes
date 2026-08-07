"""Minimal HTTP API and web server for the Stochastic Tutor Agent."""

from __future__ import annotations

import argparse
import json
import mimetypes
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.assessment import AssessmentEngine
from src.agent import StochasticTutorAgent
from src.module_registry import module_catalog


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
AGENT = StochasticTutorAgent()
ASSESSMENTS = AssessmentEngine()


class TutorRequestHandler(BaseHTTPRequestHandler):
    server_version = "StochasticTutor/0.1"

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
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
                    "knowledge": AGENT.knowledge.stats(),
                }
            )
        elif path == "/api/topics":
            self._json({"modules": module_catalog()})
        elif path == "/api/profile":
            session_id = parse_qs(parsed.query).get("session_id", [""])[0]
            if not session_id:
                self._json(
                    {"error": "session_id is required"}, HTTPStatus.BAD_REQUEST
                )
            else:
                self._json(
                    {
                        "profile": AGENT.memory.profile(session_id),
                        "history": AGENT.memory.history(session_id),
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
        path = urlparse(self.path).path
        if path not in {"/api/chat", "/api/quiz/submit"}:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/chat":
                response = AGENT.answer(
                    str(payload.get("question", "")),
                    session_id=payload.get("session_id"),
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
                response = {
                    "session_id": session_id,
                    "result": result,
                    "memory": AGENT.memory.profile(session_id),
                }
            self._json(response)
        except (ValueError, json.JSONDecodeError) as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            self._json(
                {"error": "internal server error"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_DELETE(self) -> None:  # noqa: N802
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
        print(f"[http] {self.address_string()} {format % args}")


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
