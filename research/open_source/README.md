# Open-source implementation references

This folder records small, local-only snapshots inspected while designing the
interview version of the teaching Agent. The snapshots under `vendor/` are
excluded from Git. They are references, not production dependencies.

Before adapting any implementation into `src/`:

1. keep the upstream project and commit below in the change notes;
2. retain the applicable copyright and license notices;
3. rewrite the interface for this project's smaller architecture;
4. add project-specific tests before enabling the feature;
5. list materially reused code in `THIRD_PARTY_NOTICES.md`.

## Reviewed projects

### DeepTutor

- Repository: https://github.com/HKUDS/DeepTutor
- Reviewed commit: `37c3db6df7e886aee4f61c97ec5e618b8ab379e8`
- License: Apache License 2.0
- Local files:
  - `smart_retriever.py`: multi-query retrieval and aggregation pattern.
  - `source_inventory.py`: cumulative, source-aware conversation context.
  - `memory_document.py`: structured learner-memory document pattern.
  - `mastery_choices.py`: deterministic multiple-choice normalization.
  - `agentic_loop.py`: bounded tool loop and protocol-validation pattern.

Use the retrieval, source inventory, learner memory and mastery ideas in a
smaller form. Do not import DeepTutor's complete runtime or dependency graph.

### OpenTutorAI Community Edition

- Repository: https://github.com/Open-TutorAi/open-tutor-ai-CE
- Reviewed commit: `196c547291da5df57b68165691e47ca7ffdbb137`
- License: BSD 3-Clause
- Local files:
  - `provider_registry.py`: provider registration pattern.
  - `retrieval_service.py`: retrieval and embedding configuration schema.
  - `test_retrieval.py`: retrieval API contract-test examples.

Use the provider abstraction and configuration shape. Its current retrieval
service is mainly configuration management, not a drop-in vector RAG engine.

### Study Buddy

- Repository: https://github.com/michael-borck/study-buddy
- Reviewed commit: `224fec8c83a163796fece55cb2f7f16e8ffae253`
- License: MIT
- Local files:
  - provider interface and OpenAI/Ollama adapters;
  - streaming chat route;
  - chat component.

Use these files only as UI and streaming references because they are written
for a TypeScript, Next.js and Electron stack, while this project uses Python.

### Mail Agent

- Repository: https://github.com/54younger/mail_agent
- Reviewed commit: `375be17`
- License: Fair Core License 1.0, MIT Future License
- Reviewed areas: left navigation shell, editorial dashboard hierarchy,
  warm-neutral light palette, KPI cards, focus states and responsive layout.

No Mail Agent source code, assets or brand elements are copied. The teaching
Agent may independently use the general dashboard ideas to organize its own
modules, workflow evidence and learner profile. This avoids creating or
redistributing a derivative under the upstream Fair Core terms.

## Dependency reference

LangGraph is the preferred workflow dependency for the future state graph:
https://github.com/langchain-ai/langgraph. Use its public Python API instead
of copying framework source code.

## Excluded projects

- Studyield is useful for teach-back and multi-agent product ideas, but its
  AGPL-3.0 code is not copied into this MIT project.
- Unlicensed repositories and gists are excluded.
- Generic stochastic-process packages may be used as test oracles, but the
  executable teaching tools must remain aligned with Modules 00--10.
