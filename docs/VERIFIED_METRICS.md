# Verified Metrics — current baseline

This file is the single source of truth for the interview snapshot. Numbers are
reproducible offline and must not be read as a general model-quality claim.

| Suite | Current value | Reproduce |
| --- | ---: | --- |
| Pytest runtime | 329 passed, 1 warning | `python -m pytest` |
| Browser acceptance | 9 passed (desktop + 390×844 mobile) | `python -m pytest tests/e2e -q` |
| Core single/multi-turn | 30/30 + 5/5 | `python evals/run_evaluation.py` |
| Retrieval | Hit@3 1.0, MRR 0.9394 | `python evals/run_retrieval_evaluation.py` |
| Answerability/bad path | 7/7; all tracked metrics 1.0 | `python evals/run_answerability_evaluation.py` |
| Structured course coverage | 120/120 | `python evals/run_course_coverage_evaluation.py` |
| Experiment routing | 17/17 | `python evals/run_experiment_routing_evaluation.py` |
| Visualization E2E | 74/74 | `python scripts/verify_notebook_visualizations.py` |
| Multilingual offline | 43/43 | `python evals/run_multilingual_evaluation.py` |
| Pedagogy | 10/10 | `python evals/run_pedagogy_evaluation.py` |
| Safety | 20/20 | `python evals/run_safety_evaluation.py` |
| Personalization | 33/33 | `python evals/run_personalization_evaluation.py` |
| RAG credibility hard set | 119/129 | `python evals/run_rag_credibility_evaluation.py` |
| Independent holdout | report separately; do not mix with hard set | `python evals/run_holdout_evaluation.py` |

Corpus metadata: 421 indexed entries, 11 modules, 40 knowledge points, 15
tools. Generate the current manifest with the workflow command in
`.github/workflows/test.yml`; it records the corpus SHA instead of silently
overwriting historical reports. The current textbook corpus SHA at the last
baseline is `bca3e9cc6ae22642d42434f60e8243d53baee7175c799d00534fc932ab28f942`.

The hard set is an intentionally difficult credibility diagnostic. The 119/129
score is not a blocker for the interview demo; it is a visible limitation that
should not be presented as perfect general retrieval.
