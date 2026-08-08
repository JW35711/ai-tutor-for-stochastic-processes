# Responsible AI and educational boundaries

## Intended use

StochLab is supplementary material for learning introductory stochastic
processes. It helps a learner inspect simulated paths, compare empirical and
theoretical quantities, answer small concept checks and revisit explicit
misconceptions. It is not an autonomous instructor, examination system or
psychometric assessment.

## Truth and provenance controls

- Only the 15 reviewed Python functions produce numerical results.
- Every tool validates model-specific bounds before returning a chart.
- Retrieval is restricted to the routed course module and returns exact
  Notebook cell locators plus score components.
- A language model is optional and only rewrites a deterministic answer.
- A rewrite is discarded if any numeric or Notebook-source anchor is missing.
- The seven-node trace states which module, evidence, parameters and tool were
  used; it does not expose hidden chain-of-thought.

The learner can still receive a statistically unusual sample path. The UI
therefore presents empirical and theoretical values together instead of
describing one run as proof.

## Learner model

The profile deliberately calls its score *practice evidence*. Successful tool
runs, concept-check attempts and explicit misconception triggers are stored as
different signals. The score is a transparent product heuristic and must not
be used for grading, admission, hiring or diagnosis.
Quiz exposure is counted by distinct question ID rather than raw submissions,
so repeatedly submitting an already revealed answer does not create fake topic
coverage. Attempts and accuracy remain visible separately.

The six misconception rules fire only when a learner states a known trigger.
Absence of a trigger does not prove understanding. The current rule set and
quiz bank are too small to support population-level claims about learning.

## Data handling

The single-instance demo stores session IDs, learner questions, parameters,
quiz results and misconception findings in local SQLite. Request logs exclude
question text and learner identifiers. A learner can reset one session through
the UI or `DELETE /api/sessions/{id}`.

Before public use, the operator must add authentication, define retention and
deletion periods, publish a privacy notice and avoid sharing a SQLite file
between users or instances. Model and embedding providers may have separate
data policies; enabling them is an operator decision, not a requirement for
the offline application.

The demo supports an optional `MEMORY_RETENTION_DAYS` startup purge. It deletes
complete stale sessions rather than partial turns, is disabled by default, and
is visible through the health response.

## Abuse and prompt-injection boundary

Every executable simulation validates both individual parameters and the
multiplicative work factor, such as paths times steps or expected event count.
Finite-state Markov input is capped at 50 states. These bounds prevent a
syntactically valid learner prompt from expanding into an unbounded local CPU
or memory request.
Event-driven tools compute aggregate statistics online and retain at most 500
raw transitions for each displayed path. A `series_truncated` or
`event_times_truncated` flag makes that display-only sampling explicit.
Positive continuous parameters use a numerically safe lower bound, stationary
weights are scaled before normalization, and JSON serialization rejects
non-finite values instead of emitting non-standard `NaN` or `Infinity` tokens.

A learner question cannot choose an arbitrary Python name, shell command, file
path or URL. It can only select one of 15 registered functions and supply
numeric parameters that are parsed and validated. The RAG corpus is local and
read-only. Retrieved text is evidence, not an instruction channel, and a hosted
model cannot overwrite the tool result accepted by the API.
Hosted rewrites also have independent response-byte and text-character limits;
an oversized provider answer is discarded in favor of the bounded offline
draft.

Regression tests cover the function whitelist, prompt text containing an
unregistered Python call, and parameterized SQLite session deletion. These
tests do not replace authentication or external penetration testing.

The server still needs an authenticated reverse proxy before public exposure.
Its in-process rate limiter and request limits protect an interview deployment,
not a hostile multi-tenant service.

## Evaluation interpretation

The repository's 67 acceptance cases are regression tests for this curriculum:
30 single-turn, 5 multi-turn, 22 retrieval and 10 pedagogy cases. A perfect
pass rate means the checked behaviors did not regress. It is not evidence of
general mathematical reasoning quality, fairness across learner populations or
improved learning outcomes. A course deployment would require instructor
review, learner studies and calibrated assessment instruments.
