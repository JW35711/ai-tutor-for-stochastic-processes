# API contract

The local server exposes a versioned response contract without requiring a
framework. All JSON is UTF-8. Successful and error responses include
`X-Request-ID` and `X-API-Version: 1`.

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
Each trace item contains the public node name, a concise detail, `status` and
`duration_ms` for node-level observability.

## Concept checks

- `GET /api/quiz?module_id=module04` returns a question without its answer.
- `POST /api/quiz/submit` accepts `question_id`, zero-based `answer_index` and
  an optional `session_id`.

## Discovery

- `GET /api/topics` lists Modules 00--10 and their Notebook ownership.
- `GET /api/tools` lists all 15 executable tools, their module IDs, function
  names, descriptions and JSON-ready parameter types/defaults.

## Profile and reset

- `GET /api/profile?session_id=...` returns persistent progress and history.
- `DELETE /api/sessions/{id}` clears only that learner session.

## Errors and limits

Malformed or invalid requests return status `400` and an `error` string.
Requests over the configured sliding-window limit return status `429`, a
`Retry-After` header and the generated `request_id`:

```json
{
  "error": "rate limit exceeded",
  "request_id": "5ce20d1658b84ad3b60601d5f0279b3d"
}
```

The default request limits are a 1 MB JSON body, a 4,000-character question
and 60 POST requests per client per minute. The in-memory limiter is suitable
for this single-process interview deployment, not a distributed service.

## Health

`GET /health` reports module and tool coverage, the declared workflow nodes,
knowledge-index statistics, embedding backend/fallback state and process-local
request metrics. It also returns the checked evaluation manifest used by the
dashboard, including retrieval Hit@3 and MRR. It does not expose API keys,
prompts or learner records.
