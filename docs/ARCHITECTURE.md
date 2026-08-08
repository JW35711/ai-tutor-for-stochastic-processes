# Architecture

The project separates probabilistic computation from language generation. The
Python tools own all numerical results; an optional language model may only
rewrite the verified explanation.

The rewrite boundary is enforced after generation: every number in the
verified tool-result summary and every exact Notebook source locator must
remain present. Numbers that merely occur inside a retrieved teaching excerpt
are not confused with numerical outputs. A candidate that drops or changes a
required anchor is discarded, and the offline draft is returned. Prompt
instructions are therefore not the only grounding control.

```mermaid
flowchart LR
    Q[Student question] --> C[Module router]
    C --> R[Hybrid notebook RAG]
    R --> P[Parameter planner]
    P --> V[Validation]
    V --> T[One of 15 simulation tools]
    T --> X[Theory comparison]
    X --> D[Misconception diagnosis]
    D --> M[(SQLite learner memory)]
    M --> A[Adaptive response]
    A --> UI[Web demo and evidence panel]
    Z[Concept quiz] --> M
```

## Components

| Component | Responsibility | Why it is separate |
| --- | --- | --- |
| `workflow.py` | Runs the typed seven-node state graph | Node order and state transitions can be tested without the web layer |
| `module_registry.py` | Routes Chinese and English questions to Modules 00–10 | Routing can be evaluated independently |
| `knowledge.py` | Indexes curated cards and Markdown cells, then hybrid-ranks evidence | Retrieval remains traceable and replaceable |
| `embeddings.py` | Provides local hash and optional OpenAI-compatible vectors | Neural retrieval is optional, while offline behavior remains deterministic |
| `processes/` | Runs 15 validated stochastic simulations | The LLM cannot invent or modify numerical output |
| `pedagogy.py` | Detects explicitly stated misconceptions | Diagnoses are transparent rather than hidden in a prompt |
| `assessment.py` | Serves and grades module concept checks | Quiz results provide evidence beyond tool execution |
| `memory.py` | Persists turns, tool parameters, quizzes and per-module progress in SQLite | Learner state and follow-up context survive server restarts |
| `runtime.py` | Implements rate limiting, request metrics and structured events | HTTP protection remains independent of tutoring logic |
| `openapi.py` | Publishes the versioned machine-readable HTTP contract | Clients can inspect routes without coupling to handler code |
| `version.py` | Defines application and API versions once | UI, health, headers and OpenAPI cannot silently disagree |
| `validation.py` | Shares session contracts across core and HTTP layers | Direct Agent calls cannot bypass lifecycle-safe identifiers |
| `provenance.py` | Canonically hashes module, tool, parameters, result and corpus | Equivalent execution evidence has a stable portable fingerprint |
| `evaluation_manifest.py` | Validates the evaluation summary shown in health and UI | Dashboard counts cannot silently drift from case files |
| `tool_catalog.py` | Exposes function descriptions, module ownership and parameter contracts | Tool use is inspectable without reading orchestrator code |
| `recommendation.py` | Selects one next practice from coverage and evidence | Personalization remains inspectable and avoids diagnostic claims |
| `agent.py` | Orchestrates retrieval, tools, verification and response | Provides a single API boundary |
| `evals/` | Measures routing, tool, citation and trace accuracy | Agent changes have a repeatable acceptance gate |

## Retrieval

At startup, the retriever loads 11 curated knowledge cards and extracts
Markdown teaching cells from all 11 notebooks. It combines IDF-weighted sparse
terms, Chinese character bigrams and trigrams, and cosine similarity over a
vector index. Results are restricted to the routed module and expose sparse,
title, vector and bonus score components, the backend name, source type and
exact `#cell-N` locator.

For Chinese course questions, a small reviewed concept map appends transparent
English retrieval hints for terms such as holding time, memorylessness, hazard
rate and absorption time. Every returned source includes the applied expansion
list. Title overlap receives a fixed, separately reported boost, so a specific
Notebook section can outrank a broad module summary without a hidden reranker.

The default 384-dimensional hash vectorizer is deterministic and offline. It
helps with wording variation but is not described as a neural semantic model.
An OpenAI-compatible embedding backend can batch-index the same entries when
explicitly configured. A failed hosted configuration falls back to the local
backend and reports the reason through `/health`.
If a hosted index succeeds but a later query-vector call fails, retrieval uses
the compatible sparse score only and labels every result
`retrieval_mode=sparse_fallback`; it never compares incompatible local and
hosted vector spaces. A bounded cooldown circuit prevents every concurrent
question from waiting on the same failed provider. The health payload exposes
its state, failure and skip counters, and next retry delay. Sparse emergency
results are not cached, so a recovered provider can restore hybrid retrieval.

A bounded LRU cache avoids repeated embedding calls for equivalent normalized
queries. Cached results are deep-copied on both insertion and return so one
request cannot mutate another request's evidence. Cache counters are exposed
for operational tuning without logging the query text.

At index time, the ordered module IDs, source locators and normalized entry
text are hashed into `corpus_sha256`. The fingerprint travels with every result
and the health response, making content changes observable without publishing
the local reference PDFs.

Retrieval is regression-tested separately from end-to-end routing. The
44-case suite spans all eleven modules, English and Chinese queries, and reports
Hit@3 and mean reciprocal rank. Keeping this suite separate makes a future
neural embedding change measurable instead of relying on a subjective UI
demonstration. Each report includes per-case ranks and matched relevance text.

Teaching behavior has a second independent gate: ten cases cover all six
explicit misconception rules plus neutral controls. The evaluator requires
every correction to appear in the answer and every successful tool response
to include experiment, interpretation, guiding question and source sections.
A third ten-case safety gate covers registry confinement, invalid numeric
inputs, non-stationary queue claims and multiplicative simulation budgets.

The committed evaluation manifest includes the corpus fingerprint used by its
reports. At startup the service compares that value with the live index and
exposes `corpus_match`; the UI refuses to present a stale pass count.
Manifest version 2 also stores the SHA-256 of each exact case file, so changing
case wording without changing the case count cannot preserve an old pass claim.
The assessment bank has its own SHA-256 fingerprint. Each graded attempt stores
that fingerprint, so a future question edit does not make historical evidence
look as though it came from the new bank.

## State graph

`AgentState` is the single object passed through seven named nodes:

```text
classify → retrieve → plan → tool → diagnose → memory → respond
```

Each handler owns a small set of state fields and returns a trace description.
The graph validates unique node names and exposes its declared node contract in
every API response. This local implementation keeps the offline server free of
framework dependencies; its node signatures are deliberately close to hosted
graph orchestrators so a LangGraph adapter is an integration change rather
than another rewrite of the tools.

Every trace entry also records `status` and `duration_ms`. If a node raises,
the failed node and exception type are appended before the error propagates.
This gives the UI node-level latency and failure evidence without exposing
private reasoning text.

## Learner model

The learner profile distinguishes three forms of evidence:

1. successful validated simulation runs;
2. concept-check accuracy;
3. repeated misconception triggers.

The displayed score is labelled *practice evidence*. It is not presented as a
psychometrically validated estimate of ability. That distinction is important
in an education product.

The recommendation policy first revisits a practiced module with weak or
missing evidence, then expands to the next uncovered course module, and finally
suggests boundary cases when all modules are covered. Every recommendation
includes a reason code, learner-facing reason and editable suggested question.

## Multi-turn state

Each successful turn stores the routed module, selected tool and validated
parameters. If the next turn omits the model, the Agent inherits the previous
module and tool. It carries forward only parameters that the learner did not
explicitly replace. The `classify` and `plan` trace entries state whether the
module or individual parameters came from context. SQLite schema migration adds
the parameter column to existing local profiles without deleting earlier turns.
File-backed memory uses WAL mode, enforced foreign keys and a bounded busy
timeout; application-level locking keeps the shared standard-library connection
consistent across request threads.
Schema version 3 is stored in SQLite `user_version`. Older local databases are
migrated in place, while a database created by a newer application is rejected
instead of being silently downgraded. Simulation turns and quiz attempts are
independently capped per session, and the learner can export all retained rows
with corpus and quiz-bank provenance before deleting the session.

## Reliability and safety

- Invalid model parameters fail before a chart is generated.
- Tools bound multiplicative work, not just individual parameters. Event-driven
  models aggregate online and retain at most 500 raw transitions per displayed
  path, with explicit truncation flags.
- Signed and scientific-notation inputs are parsed rather than silently
  replaced by defaults; fractional counts fail integer validation.
- M/M/1 stability is checked before a stationary distribution is discussed.
- Numerical functions receive explicit seeds for reproducible tests.
- Normal notebook use remains unseeded, matching the thesis teaching design.
- LLM use is optional; offline mode supports every simulation and assessment.
- Hosted LLM and embedding calls use bounded timeouts, response-body limits
  and independent cooldown circuits. Concurrent or repeated provider failures
  degrade immediately to a verified offline answer or sparse retrieval path;
  health reports recovery state without prompts or credentials.
- Third-party reference PDFs are excluded from version control.
- Each API response carries a request ID and browser security headers.
- All API requests use a per-client sliding-window rate limit. POST requests
  are additionally bounded by body size and question length.
- The rate limiter also bounds active client-key cardinality. Runtime latency
  exposes an all-time average and bounded recent p95.
- `/live` reports process liveness; `/ready` checks memory, catalogs, knowledge,
  assessment and evaluation versions before the service receives traffic.
- Browser-side chat, assessment and reset writes are mutually exclusive. All
  fetches have explicit abort deadlines, surface the server request ID on API
  errors, and refresh the provider fallback state after an Agent run.
- `/openapi.json` describes the human-documented API as OpenAPI 3.1.
- Logs contain route, status and latency, but not the learner's question text.

Runtime counters are deliberately process-local, matching the current
single-instance deployment. A multi-instance version should place rate limits
in Redis and export metrics to an OpenTelemetry-compatible collector.
The hardened Compose profile runs the non-root image with a read-only root
filesystem, no Linux capabilities, bounded resources and a dedicated SQLite
volume. CI starts this profile, verifies readiness and OpenAPI, then removes its
temporary volume.
