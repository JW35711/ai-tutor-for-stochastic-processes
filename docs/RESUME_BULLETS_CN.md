# 简历 bullet variants

## AI Agent

- 将 11 个随机过程教学 Notebook 重构为课程型 AI Tutor：基于 LangGraph 条件工作流、课程路由与 RAG 证据回答 40 个知识点，并通过 answerability gate 区分 supported、partial、conflict 与 out-of-scope。
- 设计 15 个白名单 Python 仿真工具和多轮 experiment context；参数校验、结构化可视化、来源定位和 run hash 保证数值只来自 Python，不由 LLM 编造。
- 用 SQLite 持久化练习、测验、知识点 practice evidence 与 tutor context，补充 scrypt 账户、HttpOnly session、三语 UI 和 8 个真实 Playwright 浏览器验收测试。

## AI App

- 构建包含 Overview、Course、AI Tutor、Simulation Lab、My Progress 的轻量 Web 应用，支持 11 modules、40 knowledge points、15 tools 与 421 RAG entries。
- 完成从请求校验、检索、证据充分性、LLM synthesis 到 Python simulation 的可观测闭环，CI 同时运行 pytest、离线评测、浏览器 E2E 和 Docker smoke test。
- 实现 guest/registered learner identity 隔离、scrypt 密码哈希、随机 token 哈希和 HttpOnly SameSite cookie，认证身份覆盖任意前端 session id。

## Applied AI / Education

- 面向《Introduction to Stochastic Processes with Applications》设计可执行补充教学材料，让学生在概念解释、练习、测验和仿真之间建立可追踪学习路径。
- 将 Notebook、讲义 PDF 和 curated cards 统一为带 page/cell locator 的课程知识库；KaTeX 展示公式，LLM 仅做 grounded explanation，数值由 Python 工具验证。
- 用透明的 practice evidence 和 next recommendation 支持复习，不把有限的练习数据包装成心理测量意义上的 mastery。
