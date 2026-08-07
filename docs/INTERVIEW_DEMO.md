# Five-minute interview demo

## 1. Frame the problem (30 seconds)

“The thesis produced 11 computational teaching modules. I converted them into
a tool-using teaching Agent: it routes a learner question, retrieves the exact
course evidence, executes a validated stochastic simulation, compares it with
theory, and remembers learning progress.”

## 2. Show tool use and evidence (90 seconds)

Run:

> M/M/1 queue：到达率为0.75、服务率为1、时长为2000

Point out:

- the stability check `ρ < 1`;
- empirical versus theoretical mean queue length;
- the simulation chart;
- Notebook cell citations;
- the visible `classify → retrieve → plan → tool → diagnose → memory → respond`
  state graph.

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
```

Explain that the acceptance set contains 30 Chinese and English prompts and
measures module routing, tool choice, source scope and execution trace. The
separate 22-case retrieval set reports Hit@3 and MRR. Open `/health` to show the
seven workflow nodes, active vector backend, request counters and latency.

## Honest boundaries

- The default vector backend is deterministic local hashing rather than a
  neural semantic model; a compatible neural embedding endpoint is optional.
- Misconception rules are transparent seed rules, not a trained student model.
- The practice score is a product heuristic, not a validated educational test.
- A hosted LLM is optional and is not allowed to overwrite verified numbers.

These boundaries give a clear next-step discussion: learned reranking,
LLM-as-judge evaluation with human calibration, richer quiz banks, and a
deployed multi-user identity layer.
