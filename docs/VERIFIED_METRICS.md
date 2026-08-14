# Verified Metrics — current release snapshot

This file is the single source of truth for the interview snapshot. Values are
reproducible offline checks, not a general model-quality claim. The runtime and
browser suites are intentionally separate: `tests/` contains Python runtime
tests and `e2e/` contains real-browser tests.

| Suite | Current value | Reproduce |
| --- | ---: | --- |
| Runtime unittest | 319 passed, 1 warning | `python -m unittest discover -s tests -v` |
| Browser acceptance | 11 passed (desktop + 390×844 mobile) | `python -m pytest e2e -q` |
| Full pytest discovery | 341 passed, 1 warning | `python -m pytest -q` |
| Core single/multi-turn | 30/30 + 5/5 | `python evals/run_evaluation.py` |
| Retrieval | Hit@3 1.0, MRR 0.9394 | `python evals/run_retrieval_evaluation.py` |
| Answerability/bad path | 7/7; tracked bad-path cases pass | `python evals/run_answerability_evaluation.py` |
| Structured course coverage | 120/120 | `python evals/run_course_coverage_evaluation.py` |
| Experiment routing | 17/17 | `python evals/run_experiment_routing_evaluation.py` |
| Visualization E2E | 74/74 | `python scripts/verify_notebook_visualizations.py` |
| Multilingual offline | 43/43 | `python evals/run_multilingual_evaluation.py` |
| Pedagogy | 10/10 | `python evals/run_pedagogy_evaluation.py` |
| Safety | 20/20 | `python evals/run_safety_evaluation.py` |
| Personalization | 33/33 | `python evals/run_personalization_evaluation.py` |
| RAG credibility hard set | 99/129 | `python evals/run_rag_credibility_evaluation.py` |
| Independent holdout | 15/32 end-to-end; 21/32 routing-pass in manifest | `python evals/run_holdout_evaluation.py` |

## Corpus and evaluation governance

Corpus metadata: 421 indexed entries, 11 modules, 40 knowledge points and 15
tools. The current textbook corpus SHA is:

```text
bca3e9cc6ae22642d42434f60e8243d53baee7175c799d00534fc932ab28f942
```

The hard set and holdout are intentionally difficult natural-question
diagnostics. Their scores are not presented as RAG accuracy. The current
offline rerun is the release baseline; older artifacts that report 119/129 or
other totals are historical and must not be read as the current result.

The current generated manifest is **447/488**. Its informational holdout suite
uses the routing-pass view, while the standalone holdout command reports the
end-to-end `PASS` count; both are kept explicit so they are not conflated.

The CI workflow runs runtime tests, deterministic evaluation suites, Docker
contract checks and the independent browser job. It records corpus/version
metadata in the generated evaluation manifest rather than overwriting
historical reports.

## Reproduce the complete local gates

```bash
python -m unittest discover -s tests -v
python -m pytest e2e -q
python evals/run_evaluation.py --output /tmp/evaluation_report.json
python evals/run_multilingual_evaluation.py --output /tmp/multilingual_report.json
python evals/run_retrieval_evaluation.py --output /tmp/retrieval_report.json
python evals/run_pedagogy_evaluation.py --output /tmp/pedagogy_report.json
python evals/run_safety_evaluation.py --output /tmp/safety_report.json
python evals/run_answerability_evaluation.py > /tmp/answerability_report.json
python evals/run_course_coverage_evaluation.py --output /tmp/course_coverage_report.json
python evals/run_experiment_routing_evaluation.py --output /tmp/experiment_routing_report.json
python scripts/verify_notebook_visualizations.py --output /tmp/visualization_e2e_report.json
python evals/run_personalization_evaluation.py --output /tmp/personalization_report.json
python evals/run_rag_credibility_evaluation.py --output /tmp/rag_credibility_report.json
python evals/run_holdout_evaluation.py --output /tmp/course_holdout_report.json
```
