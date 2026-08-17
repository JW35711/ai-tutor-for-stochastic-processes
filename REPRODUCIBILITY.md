# Reproducibility guide

This document describes how to reproduce the stochastic-process teaching
material and the StochLab prototype.

## 1. Environment

Recommended:

- Python 3.10–3.12
- a new virtual environment
- the package versions constrained by `requirements.txt`

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Record the exact environment when preparing an assessed archive:

```bash
python --version
pip freeze > environment-freeze.txt
```

`environment-freeze.txt` is a local submission artefact. Add it to the assessed
archive only when requested; it is not required for normal repository use.

## 2. Notebook execution order

Run the notebooks from top to bottom in this order:

1. `00_Monte_Carlo.ipynb`
2. `01_Bernoulli&Poisson.ipynb`
3. `02_Random_Walk_Part1.ipynb`
4. `03_Random_Walk_Part2.ipynb`
5. `04_Random_Walk_Part3.ipynb`
6. `05_Markov_Chain_Part1.ipynb`
7. `06_Markov_Chain_Part2.ipynb`
8. `07_Markov_Chain_Part3.ipynb`
9. `08_Exploratory_Module_1.ipynb`
10. `09_Exploratory_Module_2.ipynb`
11. `10_Exploratory_Module_3.ipynb`

Use **Kernel → Restart Kernel and Run All Cells** for each notebook. A clean run
must not rely on variables created by another notebook.

## 3. Random-seed policy

- Normal notebook execution uses a fresh NumPy random generator without a
  fixed seed, so rerunning a notebook produces another valid realisation.
- Record important parameter values and sample sizes next to the result or in
  its caption.
- Reproducibility means that the same model, procedure and statistical
  behaviour can be obtained in a compatible environment; it does not require
  identical random values.
- A fixed seed may be supplied temporarily when debugging a specific result,
  but it is not required for the teaching experiments.

## 4. Numerical checks

For each main module, compare empirical output with an appropriate reference:

- Monte Carlo: convergence of an estimator and its sampling error;
- Poisson process: mean count `lambda * t` and exponential waiting times;
- random walk: endpoint mean and variance;
- Brownian motion: terminal mean zero and variance `T`;
- Markov chain: row-stochastic matrix, empirical frequencies and stationary
  distribution;
- queueing and reliability: parameter constraints and theoretical benchmark
  quantities where available.

Small discrepancies are expected in stochastic simulation. They should decrease
with increasing sample size and should be interpreted statistically rather than
as exact equality tests.

## 5. Agent verification

The Agent extension uses only the Python standard library:

```bash
python3 -m unittest discover -s tests -v
python3 server.py
```

Verify both endpoints:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"模拟强度为2、时长为5的泊松过程"}'
```

## 6. Repository and submission checklist

- [ ] The final notebooks are present under `notebooks/`.
- [ ] Every notebook runs from a clean kernel.
- [ ] Selected figures can be traced to their generating notebook.
- [ ] `requirements.txt` matches the imports used by the notebooks.
- [ ] README and module names agree.
- [ ] No API keys, local environments, caches or `.DS_Store` files are tracked.
- [ ] Third-party material under `reference/` is not published.
- [ ] The Agent unit tests pass.
- [ ] Any separate course-report PDF and editable source are packaged outside
      this application repository when a submission process requires them.
