# StochLab 面试演示脚本

## 60 秒

1. 展示五个视图和 `11 modules / 40 knowledge points / 15 tools`。
2. 在 Course 打开 Module 05，进入 Markov Property，点击 Learn。
3. 在 AI Tutor 问 “What is the Markov property?”，展开课程来源。
4. 点击 Practice，先提交一个不完整答案，再点 Hint 和 Retry；最后打开 Progress。
5. 说明没有 API key 时仍使用简短、基于课程证据的离线 fallback。

## 3 分钟

先注册一个演示账户，重复上面的 Course → Learn → Practice → Progress 路径。做一次错误
quiz（红色选择）再做正确 quiz（绿色选择），解释只有练习和测验改变 practice evidence。
进入 AI Tutor，依次输入：

```text
What is a Poisson process?
Why are the waiting times exponential?
Show me.
Set lambda to 4.
What changed?
```

指出概念回答不会调用工具，明确 simulation 才会调用 Python 工具；图表、参数、来源和
follow-up 都属于同一个 experiment context。退出账户，再登录，展示学习记录仍在。

## 5 分钟

切换 English / 中文 / Svenska，分别展示 UI 语言和 query 语言可以不同。打开 Simulation
Lab，搜索 Poisson 或 Brownian，编辑参数并运行，说明数值只由 Python tool 产生，LLM 只
解释结果。回到 Progress 刷新页面，最后登出并重新登录。必要时展示 `/health`、`/ready`、
`/openapi.json` 和 `?debug=1`，说明 request id、workflow、source locators 与 latency
只在诊断层出现，不暴露给普通学生。

## 兜底路径

没有密钥、provider 超时、错误参数或问题超出课程范围时，服务保持可用；学生只看到简短
英文/中文/瑞典语提示，不会看到 stack trace、原始 PDF 长摘录或伪造的模拟数字。
