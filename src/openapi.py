"""Machine-readable API contract for the dependency-free HTTP service."""

from __future__ import annotations

from typing import Any

from .version import API_VERSION, APP_VERSION
from .validation import MAX_QUESTION_CHARS


def _json_response(description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": schema}},
        "headers": {
            "X-Request-ID": {"schema": {"type": "string"}},
            "X-API-Version": {
                "schema": {"type": "string", "const": API_VERSION}
            },
        },
    }


OBJECT = {"type": "object", "additionalProperties": True}
ERROR_RESPONSE = _json_response(
    "Traceable request error",
    {"$ref": "#/components/schemas/Error"},
)


OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {
        "title": "StochLab Teaching Agent API",
        "version": APP_VERSION,
        "description": (
            "Local-first API for a source-aware stochastic-process teaching Agent. "
            "The interview build has no application-level authentication and must "
            "sit behind an authenticated reverse proxy before public exposure."
        ),
    },
    "x-api-version": API_VERSION,
    "servers": [{"url": "/", "description": "Current origin"}],
    "paths": {
        "/live": {
            "get": {
                "operationId": "getLiveness",
                "summary": "Process liveness",
                "responses": {"200": _json_response("Alive", OBJECT)},
            }
        },
        "/ready": {
            "get": {
                "operationId": "getReadiness",
                "summary": "Dependency readiness",
                "responses": {
                    "200": _json_response("Ready", OBJECT),
                    "503": _json_response("Not ready", OBJECT),
                },
            }
        },
        "/health": {
            "get": {
                "operationId": "getHealth",
                "summary": "Coverage, evaluation and runtime evidence",
                "responses": {"200": _json_response("Health report", OBJECT)},
            }
        },
        "/api/topics": {
            "get": {
                "operationId": "listTopics",
                "summary": "List all 11 teaching modules",
                "responses": {
                    "200": _json_response("Module catalog", OBJECT),
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/tools": {
            "get": {
                "operationId": "listTools",
                "summary": "List all 15 executable tool contracts",
                "responses": {
                    "200": _json_response("Tool catalog", OBJECT),
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/chat": {
            "post": {
                "operationId": "askTutor",
                "summary": "Run the seven-node teaching workflow",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatRequest"}
                        }
                    },
                },
                "responses": {
                    "200": _json_response("Grounded Agent response", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/profile": {
            "get": {
                "operationId": "getLearnerProfile",
                "summary": "Get retained progress and recent histories",
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "query",
                        "required": True,
                        "schema": {"$ref": "#/components/schemas/SessionId"},
                    }
                ],
                "responses": {
                    "200": _json_response("Learner profile", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/quiz": {
            "get": {
                "operationId": "getQuiz",
                "summary": "Get a module concept check without its answer",
                "parameters": [
                    {
                        "name": "module_id",
                        "in": "query",
                        "required": True,
                        "schema": {
                            "type": "string",
                            "pattern": "^module(0[0-9]|10)$",
                        },
                    }
                ],
                "responses": {
                    "200": _json_response("Public quiz question", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/quiz/submit": {
            "post": {
                "operationId": "submitQuiz",
                "summary": "Grade and persist one concept-check attempt",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/QuizSubmitRequest"
                            }
                        }
                    },
                },
                "responses": {
                    "200": _json_response("Graded attempt", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/sessions/{session_id}": {
            "delete": {
                "operationId": "deleteLearnerSession",
                "summary": "Delete one learner-owned local session",
                "parameters": [
                    {"$ref": "#/components/parameters/SessionPath"}
                ],
                "responses": {
                    "200": _json_response("Session reset", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
        "/api/sessions/{session_id}/export": {
            "get": {
                "operationId": "exportLearnerSession",
                "summary": "Export all retained learner data with provenance",
                "parameters": [
                    {"$ref": "#/components/parameters/SessionPath"}
                ],
                "responses": {
                    "200": _json_response("Versioned learner export", OBJECT),
                    "400": ERROR_RESPONSE,
                    "429": ERROR_RESPONSE,
                },
            }
        },
    },
    "components": {
        "schemas": {
            "SessionId": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "pattern": "^[^/\\u0000-\\u001F]{1,128}$",
                "description": "Printable opaque learner-session identifier without slash.",
            },
            "ChatRequest": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question"],
                "properties": {
                    "question": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_QUESTION_CHARS,
                    },
                    "session_id": {"$ref": "#/components/schemas/SessionId"},
                },
            },
            "QuizSubmitRequest": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question_id", "answer_index"],
                "properties": {
                    "question_id": {"type": "string", "minLength": 1},
                    "answer_index": {"type": "integer", "minimum": 0},
                    "session_id": {"$ref": "#/components/schemas/SessionId"},
                },
            },
            "Error": {
                "type": "object",
                "additionalProperties": False,
                "required": ["error", "error_code", "request_id"],
                "properties": {
                    "error": {"type": "string"},
                    "error_code": {"type": "string"},
                    "request_id": {"type": "string"},
                },
            },
        },
        "parameters": {
            "SessionPath": {
                "name": "session_id",
                "in": "path",
                "required": True,
                "schema": {"$ref": "#/components/schemas/SessionId"},
            }
        },
    },
}
