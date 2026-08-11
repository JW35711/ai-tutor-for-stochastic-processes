# Five-minute interview demo

## 1. Frame the problem (30 seconds)

“The thesis produced 11 computational teaching modules. I converted them into
one AI Tutor with conditional routing: it reads the curriculum for navigation,
retrieves course evidence for theory questions, executes a validated Python
simulation only when requested, and remembers learning progress.”

## 2. Show tool use and evidence (90 seconds)

Run:

> M/M/1 queue：到达率为0.75、服务率为1、时长为2000

Point out:

- the stability check `ρ < 1`;
- empirical versus theoretical mean queue length;
- the simulation chart;
- Notebook cell citations;
- the conditional trace: navigation goes to curriculum, concepts go through
  retrieval and Tutor synthesis, and simulations add planning and a Python tool.

Then ask:

> 再把到达率改成0.8

Show that the Agent retains the service rate, horizon and queue tool, changes
only the arrival rate, and exposes the inherited fields in its trace. This
context still works after creating a new Agent process because parameters are
stored in SQLite rather than a Python dictionary.

## 3. Show misconception diagnosis (60 seconds)

Run:

> 布朗运动的方差是根号T，对吗？

The Agent should distinguish variance `T` from standard deviation `√T`, record
the misconception, and show it in the learner profile.

## 4. Show adaptive assessment (60 seconds)

Click **当前模块概念测验**, answer the Brownian-motion question, and show that
the quiz result updates the persistent module profile. Refresh the page or
restart the server and query `/api/profile` to demonstrate persistence.

## 5. Show engineering evidence (60 seconds)

```bash
python3 -m unittest discover -s tests -v
python3 evals/run_evaluation.py
python3 evals/run_retrieval_evaluation.py
python3 evals/run_pedagogy_evaluation.py
python3 evals/run_safety_evaluation.py
python3 evals/run_latency_benchmark.py --repetitions 2
```

Explain that the acceptance set contains 30 Chinese and English prompts and
measures module routing, tool choice, source scope and execution trace. The
separate 44-case bilingual retrieval set reports Hit@3 and MRR. Open `/health`
to show the conditional workflow, active vector backend, request counters and
latency.
The 10-case pedagogy set checks misconception corrections, neutral controls and
the required teaching-response structure.
The independent 10-case safety set checks prompt injection, unknown tools,
non-finite inputs, unstable-model claims and multiplicative work bounds.
The latency report breaks one representative prompt per module into end-to-end
and per-handler p50/p95 timings. It is explicitly labeled as a local offline
benchmark rather than a production SLA. CI uploads it with the quality reports
for comparison instead of enforcing a noisy shared-runner latency threshold.

## Honest boundaries

- The default vector backend is deterministic local hashing rather than a
  neural semantic model; a compatible neural embedding endpoint is optional.
- Misconception rules are transparent seed rules, not a trained student model.
- The practice score is a product heuristic, not a validated educational test.
- A hosted LLM is optional for concept synthesis; it is never allowed to
  create or overwrite simulation numbers.

If asked how that last boundary is enforced, point to the conditional workflow:
simulation answers come directly from validated Python tools, while provider
failure or malformed concept output falls back to the grounded offline answer.

These boundaries give a clear next-step discussion: a deterministic
answerability gate is already in place. An optional hybrid design could add a
semantic/LLM entailment judge only for ambiguous low-confidence cases, followed
by richer quiz banks and a deployed multi-user identity layer.
