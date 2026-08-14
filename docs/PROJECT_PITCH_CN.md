# 项目介绍话术

## 30 秒

我把 11 个随机过程教学 Notebook 做成了一个可执行的 AI Tutor。系统用课程路由和 RAG
回答概念问题，用受控 Python 工具运行 15 类随机过程仿真，并把练习、测验和知识点证据
写入 SQLite。它支持三种语言、guest/registered learner identity 和多轮 experiment
follow-up；没有模型密钥时也能离线运行。

## 90 秒：AI Agent 方向

这不是把每个问题都交给大模型。LangGraph 只负责显式的条件工作流：navigation 读取
curriculum，concept/why/comparison 走 evidence retrieval 和 Tutor synthesis，simulation
经过 plan、参数校验和 Python tool，practice/quiz 交给 Assessment 并更新 learner memory。
证据充分性 gate 区分 supported、partial、conflict、none 和 out-of-scope；模型不能修改
工具数字。Curriculum、Assessment、Tutor 是三个边界清晰的职责 Agent，RAG、SQLite 和
Python 是共享服务。

## 3 分钟：AI App / Applied AI / Education

工程重点是可追踪闭环：每个知识点有稳定 ID 和来源，仿真结果有 run hash，回答保留 source
locators，浏览器有 8 个真实 Playwright acceptance tests，CI 同时跑单元、评测、浏览器和
Docker。账户层使用 SQLite 用户表、scrypt 密码哈希、随机 token 的哈希和 HttpOnly
SameSite cookie；认证用户的 learner identity 覆盖任意前端 session id。教育边界也明确：
mastery 只是 practice evidence，不是心理测量或成绩。下一阶段可在 deterministic gate
之后为低置信歧义样本增加可选 semantic judge，但当前 v1 不依赖它。
