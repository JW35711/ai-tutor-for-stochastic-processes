# API contract

The local server exposes a versioned response contract without requiring a
framework. All JSON is UTF-8. Successful and error responses include
`X-Request-ID` and `X-API-Version: 1`.
Errors keep a human-readable string in `error` for the browser and also return
a stable `error_code` plus `request_id` for programmatic handling and log
correlation.
Static UI assets return a SHA-256 `ETag` with `Cache-Control: no-cache`, so
browsers revalidate changed files and reuse unchanged bytes through `304`.
The same contract is available to tools at `GET /openapi.json` as OpenAPI 3.1.

## Chat

`POST /api/chat`

```json
{
  "question": "M/M/1 queue：到达率为0.75、服务率为1、时长为2000",
  "session_id": "optional-existing-session"
}
```

The response contains the selected module and tool, validated parameters,
numerical result, Notebook sources, seven-node trace, learner profile and
request ID. `llm_enabled` states whether a provider is configured, while
`llm_applied` is true only when its rewrite passed numeric and source-anchor
validation. `session_id` can be omitted on the first turn and then reused.
`verified` is true only when tool validation and execution completed; the UI
uses it instead of displaying a static success badge.
Each trace item contains the public node name, a concise detail, `status` and
`duration_ms` for node-level observability.
The response also includes an explainable `recommendation` with its module,
reason code, learner-facing reason and suggested next question.

## Concept checks

- `GET /api/quiz?module_id=module04` returns a question without its answer and
  includes `bank_sha256` so an attempt can be traced to the exact quiz bank.
- `POST /api/quiz/submit` accepts `question_id`, zero-based `answer_index` and
  an optional `session_id`; the result carries the same quiz-bank hash. Boolean,
  string and out-of-range answer indices are rejected rather than coerced.

## Discovery

- `GET /api/topics` lists Modules 00--10 and their Notebook ownership.
- `GET /api/tools` lists all 15 executable tools, their module IDs, function
  names, descriptions and JSON-ready parameter types/defaults.

## Profile and reset

`GET /api/profile?session_id=...` returns the learner profile, simulation
history, quiz-attempt history and next recommendation. Each new quiz attempt
stores the `bank_sha256` of the exact assessment content used; rows created by
older releases may return `null` for that field after the in-place migration.

- `DELETE /api/sessions/{id}` clears only that learner session.
- `GET /api/sessions/{id}/export` returns every retained simulation turn and
  quiz attempt for that session, plus content hashes, policy limits and the
  current recommendation. The UI exposes this separately from single-run JSON.

## Errors and limits

Malformed or invalid requests return status `400`, an `error` string and a
stable `error_code`.
Requests over the configured sliding-window limit return status `429`, a
`Retry-After` header and the generated `request_id`:

```json
{
  "error": "rate limit exceeded",
  "error_code": "rate_limited",
  "request_id": "5ce20d1658b84ad3b60601d5f0279b3d"
}
```

POST routes require `Content-Type: application/json`, a complete non-chunked
JSON object and typed string fields rather than implicit coercion. The default
request limits are a 1 MB JSON body, a 4,000-character question
and 60 API requests per client per minute. The in-memory limiter is suitable
for this single-process interview deployment, not a distributed service.
`MAX_JSON_BODY_BYTES` and `MAX_QUESTION_CHARS` can lower or raise the first two
limits for a controlled deployment.
All routes share the same session contract: 1--128 printable characters, with
omission allowed only when the server can generate a new session.

## Health

`GET /live` is a minimal process-liveness probe. `GET /ready` checks SQLite,
the 11-module catalog, 15-tool registry, knowledge index, assessment bank and
evaluation-to-corpus version match; it returns `503` if any check fails.
`GET /health` reports module and tool coverage, the declared workflow nodes,
knowledge-index statistics, embedding backend/fallback state and process-local
request metrics. It also returns the checked evaluation manifest used by the
dashboard, including retrieval Hit@3 and MRR. It does not expose API keys,
prompts or learner records.
Latency metrics include the all-time process average and p95 over a bounded
256-request recent window, together with the current window sample count.
Knowledge statistics and every retrieved source include `corpus_sha256`, the
fingerprint of the indexed cards and Notebook teaching cells.
The `learner_data` section reports the configured retention period and how many
stale sessions were purged at startup, without revealing their identifiers.
