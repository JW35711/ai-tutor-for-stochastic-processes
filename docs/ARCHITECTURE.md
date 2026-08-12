# Architecture

The project separates probabilistic computation from language generation. The
Python tools own all numerical results; the optional DeepSeek/OpenAI-compatible
model synthesizes a grounded explanation from the original student question
and retrieved evidence. This release is a responsibility-bounded three-agent
educational system (`Curriculum Agent`, `Assessment Agent` and `Tutor Agent`)
orchestrated by LangGraph. RAG, Python tools and SQLite remain shared services,
not agents.

The answer boundary is enforced after generation: every number in a verified
tool-result summary and every exact Notebook source locator must remain
present. Numbers that merely occur inside a retrieved teaching excerpt are not
confused with numerical outputs. A candidate that drops or changes a required
anchor is discarded, and the offline draft is returned. Prompt instructions
are therefore not the only grounding control.

```mermaid
flowchart LR
    Q[Student question] --> I{Intent}
    I -->|navigation| C[Curriculum Agent]
    I -->|concept / why / comparison| R[Hybrid RAG]
    I -->|simulation| R
    R -->|concept| E[Evidence gate]
    E -->|bounded supplement| R
    E -->|answerability decision| A[Tutor Agent]
    R -->|simulation| P[Plan and validate]
    P --> T[One of 15 Python tools]
    T --> A
    I -->|practice / quiz| X[Assessment Agent]
    X --> C
    A --> M[(SQLite memory)]
    X --> M
    C --> A
    C --> UI[Web UI]
    M --> UI
```

## Components

| Component | Responsibility | Why it is separate |
| --- | --- | --- |
| `graph/workflow.py` | Compiles the official LangGraph `StateGraph` and conditional edges | One explicit graph preserves navigation, tutoring, bounded evidence retrieval and simulation branches |
| `graph/state.py` | Defines the typed `TutorState` carried by LangGraph | Graph observability is separated from domain services and API state |
| `agents/curriculum.py` | Decides what the learner should study next from curriculum, prerequisites and mastery | Course progression cannot be invented by a model |
| `agents/assessment.py` | Scores quiz/practice evidence and flags review needs | Learning evaluation is separate from teaching explanation |
| `agents/tutor.py` | Applies answerability and chooses the teaching response policy | The Tutor explains; it does not rescore or compute simulations |
| `agents/contracts.py` | Defines `CurriculumDecision`, `AssessmentResult` and `TutorContext` | Agent handoffs are structured and independently testable |
| `workflow.py` | Keeps the backwards-compatible `AgentState` and node contracts | Existing integrations can inspect domain state without depending on LangGraph internals |
| `module_registry.py` | Routes Chinese and English questions to Modules 00–10 | Routing can be evaluated independently |
| `knowledge.py` | Indexes curated cards, Markdown cells, reviewed lecture-note chunks and textbook chunks, then hybrid-ranks evidence | Retrieval remains traceable and replaceable |
| `embeddings.py` | Provides local hash and optional OpenAI-compatible vectors | Neural retrieval is optional, while offline behavior remains deterministic |
| `processes/` | Runs 15 validated stochastic simulations | The LLM cannot invent or modify numerical output |
| `pedagogy.py` | Detects explicitly stated misconceptions | Diagnoses are transparent rather than hidden in a prompt |
| `assessment.py` | Serves and grades module concept checks | Quiz results provide evidence beyond tool execution |
| `memory.py` | Persists turns, tool parameters, quizzes, KP mastery and learning events in SQLite | Learner state and follow-up context survive server restarts |
| `mastery.py` | Applies the bounded deterministic KP mastery policy | Only assessed learner evidence changes mastery; Tutor explanations and retrieval do not |
| `data/notebook_experiments.json` | Registry generated from notebook order, Markdown context, code cells and saved outputs | Keeps notebook experiments and visualization targets traceable to reusable tools and renderers |
| `scripts/audit_notebook_visualizations.py` | Detects notebook visualization cells and compares them with the registry | Future unregistered figures become a deterministic coverage failure |
| `runtime.py` | Implements rate limiting, request metrics and structured events | HTTP protection remains independent of tutoring logic |
| `openapi.py` | Publishes the versioned machine-readable HTTP contract | Clients can inspect routes without coupling to handler code |
| `version.py` | Defines application and API versions once | UI, health, headers and OpenAPI cannot silently disagree |
| `validation.py` | Shares session contracts across core and HTTP layers | Direct Agent calls cannot bypass lifecycle-safe identifiers |
| `provenance.py` | Canonically hashes module, tool, parameters, result and corpus | Equivalent execution evidence has a stable portable fingerprint |
| `evaluation_manifest.py` | Validates the evaluation summary shown in health and UI | Dashboard counts cannot silently drift from case files |
| `tool_catalog.py` | Exposes function descriptions, module ownership and parameter contracts | Tool use is inspectable without reading orchestrator code |
| `recommendation.py` | Selects one next practice from coverage and evidence | Personalization remains inspectable and avoids diagnostic claims |
| `teaching_team.py` | Provides a backwards-compatible role-level trace projection for interview observability | It is not an agent registry; actual handoffs come from `observability.agents_invoked` |
| `agent.py` | Orchestrates retrieval, tools, verification and response | Provides a single API boundary |
| `evals/` | Measures routing, tool, citation and trace accuracy | Agent changes have a repeatable acceptance gate |

## Retrieval

At startup, the retriever loads 11 curated knowledge cards, extracts Markdown
teaching cells from all 11 notebooks, merges reviewed lecture-note chunks from
`data/reference_chunks.json`, and loads generated textbook chunks from
`artifacts/textbook_chunks.json` when present. The current release corpus has
421 entries across 11 modules and 40 knowledge points. It combines IDF-weighted sparse terms,
Chinese character bigrams and trigrams, and cosine similarity over a vector
index. Results are restricted to the routed module and expose sparse, title,
vector and bonus score components, the backend name, source type and exact
source locator. Notebook sources use `#cell-N`; lecture-note sources use page
locators such as `reference/lectnotes_technmath.pdf#page-69`.

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
A third twenty-case safety gate covers registry confinement, data-exfiltration
and HTML-injection prompts, invalid numeric inputs, non-stationary queue claims
and multiplicative simulation budgets across tool families.

The committed evaluation manifest includes the corpus fingerprint used by its
reports. At startup the service compares that value with the live index and
exposes `corpus_match`; the UI refuses to present a stale pass count.
Manifest version 2 also stores the SHA-256 of each exact case file, so changing
case wording without changing the case count cannot preserve an old pass claim.
The assessment bank has its own SHA-256 fingerprint. Each graded attempt stores
that fingerprint, so a future question edit does not make historical evidence
look as though it came from the new bank.

## Conditional workflow

The official LangGraph `StateGraph` carries a typed `TutorState` and executes
only the branch required by the request:

```text
START → route
route → Curriculum Agent → navigation → Tutor Agent → END
route → concept → retrieve → evidence → (bounded supplement → evidence)* → Tutor Agent → END
route → simulation → retrieve → evidence → plan → Python tool → diagnose → Tutor Agent → END
route → Assessment Agent → SQLite memory → Curriculum Agent → Tutor Agent → END
route → out_of_scope → Tutor Agent safe response → END
```

Each handler owns a small set of state fields and returns a trace description.
The evidence gate preserves the statuses `SUPPORTED`, `PARTIAL`, `CONFLICT`,
`NONE` and `OUT_OF_SCOPE`; supplementary retrieval is bounded by two follow-up
rounds. A normal concept question invokes only the Tutor Agent after retrieval;
assessment invokes all three agents because it needs a learning-state handoff.
The three agents have no hidden calls to one another: LangGraph makes each
transition explicit.

Every trace entry also records `status` and `duration_ms`. If a node raises,
the failed node and exception type are appended before the error propagates.
This gives the UI node-level latency and failure evidence without exposing
private reasoning text.

The response may expose `teaching_team`, a backwards-compatible role-level
projection of the same trace for debugging and interviews. It does not change
execution semantics or create extra agents; use `observability.agents_invoked`
and `handoffs` for the actual three-agent path.

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
includes a reason code, learner-facing reason, editable suggested question and
a conservative review interval. The interval is inspired by spaced-repetition
systems but remains a transparent heuristic over local practice evidence.

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
- Hosted concept synthesis receives only the original question, bounded course
  context and retrieved evidence. Simulation numbers never enter that path;
  Python tools remain their sole owner.
- The provider payload excludes session IDs, histories, learner profiles and
  raw simulation arrays. A failed or malformed provider response falls back to
  the concise grounded offline answer.
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
