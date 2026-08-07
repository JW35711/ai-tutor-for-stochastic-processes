# AI Tutor for Stochastic Processes

An educational AI Agent prototype extending the degree project:
**Simulation and Visualization of Stochastic Mechanisms: Applications to
Engineering Course Development**.

The final thesis notebooks are mirrored here as the Agent's approved teaching
material. The repository also contains reusable simulation tools, an exercise,
tests, and a web demonstration. The thesis-only computational repository is
available at
[simulation-visualization-stochastic-processes](https://github.com/JW35711/simulation-visualization-stochastic-processes).

## Degree-project aim

The project develops computational teaching material for an introductory
course on stochastic processes. Each notebook follows a common workflow:

1. introduce a stochastic model;
2. state the simulation rule;
3. generate a sample path or realisation;
4. repeat the experiment when studying a distribution or average;
5. compare simulation with a theoretical reference value;
6. interpret the graphical output.

The notebooks supplement mathematical analysis rather than replacing it. Their
purpose is to make stochastic mechanisms visible, reproducible and easier to
explore.

## Notebook modules

| Module | Notebook | Main topic |
| --- | --- | --- |
| 0 | `00_Monte_Carlo.ipynb` | Monte Carlo simulation workflow |
| 1 | `01_Bernoulli&Poisson.ipynb` | Bernoulli and Poisson processes, waiting times |
| 2 | `02_Random_Walk_Part1.ipynb` | Discrete-time random walks and gambler's ruin |
| 3 | `03_Random_Walk_Part2.ipynb` | Continuous-time random walks |
| 4 | `04_Random_Walk_Part3.ipynb` | Brownian motion and random-walk approximation |
| 5 | `05_Markov_Chain_Part1.ipynb` | Discrete-time Markov chains and PageRank |
| 6 | `06_Markov_Chain_Part2.ipynb` | Continuous-time chains and birth-death processes |
| 7 | `07_Markov_Chain_Part3.ipynb` | Reliability, buffers and the M/M/1 queue |
| 8 | `08_Exploratory_Module_1.ipynb` | Non-homogeneous Poisson processes by thinning |
| 9 | `09_Exploratory_Module_2.ipynb` | Growing self-avoiding walks |
| 10 | `10_Exploratory_Module_3.ipynb` | Coalescing particles on a circle |

The mathematical scope covers counting processes, random-motion models,
discrete- and continuous-time Markov chains, reliability and queueing. The
three exploratory modules change one modelling assumption at a time:
time-homogeneous intensity, path independence, and a single-particle state.

## Run the thesis notebooks

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
jupyter lab
```

Open the notebooks in `notebooks/` and run them in numerical order. See
[REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the clean-environment procedure,
random-seed policy and submission checklist.

## AI teaching-agent extension

The current Agent prototype turns seven of the eleven thesis modules into
executable tools:

- Monte Carlo estimation;
- homogeneous Poisson processes;
- one-dimensional random walks;
- continuous-time random walks;
- standard Brownian motion;
- finite-state Markov chains;
- continuous-time Markov chains and finite birth-death processes.

For each question, the Agent classifies the topic, retrieves a source-aware
course note, validates parameters, chooses a simulation tool, compares the
empirical result with theory, and returns a guided explanation with the
execution trace.

```mermaid
flowchart LR
    U[Student question] --> C[Topic classification]
    C --> R[Course-material retrieval]
    R --> P[Parameter planning]
    P --> T[Simulation tool]
    T --> V[Theory comparison]
    V --> E[Guided explanation]
    E --> UI[Web UI, sources and trace]
```

Numerical computation is performed by Python, not by the language model. An
optional OpenAI-compatible model can improve the wording, but it receives the
verified numerical result and is instructed not to alter numbers or sources.

### Run the Agent

The Agent core and web demo require no third-party packages:

```bash
python3 server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000), then try:

- `模拟强度为2、时长为5的泊松过程，使用20条路径`
- `用50条路径模拟100步随机游走，并比较理论均值`
- `模拟T为1、网格数为200的布朗运动，解释终点方差`
- `模拟500步马尔可夫链并比较平稳分布`
- `连续时间马尔可夫链：故障率为0.25、修复率为0.15、时长为200`
- `模拟出生死亡过程：出生率为0.35、死亡率为0.3、容量为6、时长为500`
- `用10000个样本做蒙特卡洛实验估计π`

To enable an OpenAI-compatible model:

```bash
export LLM_API_KEY="your-key"
export LLM_MODEL="your-model"
export LLM_BASE_URL="https://your-provider.example/v1"
python3 server.py
```

The application remains usable in offline-safe mode when these variables are
unset.

### Agent API and tests

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"模拟100步随机游走，并比较理论均值"}'

python3 -m unittest discover -s tests -v
```

The test suite checks reproducibility, theoretical agreement, transition-matrix
validation, topic routing, tool execution, citations and session memory.

## Repository structure

```text
.
├── data/                   # Curated source-aware knowledge cards
├── exercises/              # Additional exercises
├── figures/                # Selected thesis figures
├── notebooks/              # Modules 0–10
├── src/
│   ├── agent.py            # Agent orchestration
│   ├── knowledge.py        # Retrieval and source metadata
│   ├── llm.py              # Optional compatible LLM client
│   └── processes/          # Reusable simulation tools
├── tests/                  # Numerical and Agent tests
├── web/                    # Interview-demo interface
├── REPRODUCIBILITY.md
└── server.py
```

The local `reference/` directory is intentionally excluded from version
control. It contains third-party course and reference material rather than
project deliverables.

## Reproducibility policy

The teaching notebooks do not fix a random seed during normal execution, so a
rerun produces another valid realisation. Reproducibility means using the same
model, parameters and procedure and obtaining the same statistical behaviour,
not identical values. Simulation outputs should be interpreted together with
their theoretical reference values.

## Current Agent limitations

- Retrieval is transparent lexical retrieval rather than a vector index.
- Offline topic routing uses deterministic rules.
- Session memory resets when the process restarts.
- The lightweight web chart does not replace the notebook's Matplotlib figures.

The next Agent iteration will add a LangGraph state graph, vector RAG over the
final thesis, persistent learner profiles, misconception diagnosis and a
30-question evaluation set.

## License

MIT
