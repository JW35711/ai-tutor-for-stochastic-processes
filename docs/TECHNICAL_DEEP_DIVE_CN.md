# Technical Deep Dive

## A. Request lifecycle
Browser request → validation/rate limit → LangGraph route → agent handoff → response contract.
每个 HTTP request 有 request id 和总延迟；诊断模式额外显示 routing、retrieval、LLM、tool。

## B. Routing
先做 deterministic module/concept/sub-intent matching，再用 evidence fallback。概念问题不
经过 simulation；只有明确 simulation 或 active experiment follow-up 才进入 plan/tool。

## C. RAG
421 条 notebook、curated、lecture-note 和 textbook entries 走 hybrid sparse/vector retrieval。
answerability gate 区分相关性和充分性，最多两轮补充检索，保留 corpus SHA 和 source locator。

## D. Evidence sufficiency
`SUPPORTED` 正常回答，`PARTIAL` 只回答已支持内容并澄清缺口，`CONFLICT` 明示相互矛盾来源，
`NONE` 不猜，`OUT_OF_SCOPE` 返回课程范围说明。

## E. LLM boundary
OpenAI-compatible/DeepSeek 只负责 grounded teaching synthesis。提示包含原问题、requirements、
answerability 和 evidence；simulation numbers 从不交给模型计算。

## F. Simulation safety
15 个 Python tools 有白名单、参数上下界、工作量上限和结构化 renderer contract。非法参数
在 tool 前失败；结果包含 verified flag、parameters、run hash 和 visualization payload。

## G. Multi-turn context
SQLite `tutor_context` 只保留 active experiment、参数和简短 summary。`Show me`、`Set lambda
to 4`、`What changed?` 复用同一 experiment，而不是重新猜测工具。

## H. Learning state
Assessment 写入 turns/assessments/concept_mastery/learning_events；Tutor、navigation 和
simulation 不改变 mastery。recommendation 是可解释的 course-order policy。

## I. Accounts
`users`、`auth_sessions`、`learner_identities` 与既有 learner tables 共用 SQLite。用户名
规范化后唯一；密码是 versioned scrypt；cookie 只存随机 token，服务端存 token hash；认证
身份始终覆盖任意客户端 `session_id`。

## J. Frontend
Vanilla JS 保持五个独立 views，Tabler-like layout；Course、Tutor、Simulation Lab、Progress
都复用后端 APIs。KaTeX 对 `$...$`、`$$...$$`、`\(...\)`、`\[...\]` 做 DOM 渲染。

## K. Observability and tests
pytest 覆盖 deterministic contracts；8 个 Playwright tests 启动真实 server、隔离 SQLite、
记录 console/page errors/5xx 并在失败时保存截图和 JSON。CI 分开 fast runtime tests、eval、
Docker 和 browser job。

## L. Known boundary

这是单实例、单 Tutor 应用，不是 LangGraph 之外的 Multi-Agent 平台；没有 OAuth、邮箱找回、
2FA、教师后台或分布式 session store。复杂隐式矛盾检测和心理测量仍是未来工作。
