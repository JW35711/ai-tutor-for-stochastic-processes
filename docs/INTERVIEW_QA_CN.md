# AI 教学 Agent 面试讲解稿

## 60 秒项目介绍

我的毕业项目原本包含 11 个随机过程教学 Notebook。我把这些课程材料重构成了
一个可执行的教学 Agent：它先识别学生问题所属的课程模块，再从对应 Notebook
检索证据，选择 15 个受控 Python 工具之一完成仿真，把经验结果与理论值对照，
识别明确的概念误区，并将练习和测验记录写入 SQLite 学习档案。

整个过程由官方 LangGraph StateGraph 的显式条件节点和三类职责 Agent 组成，API 会返回工具参数、Notebook cell、混合检索
分数和执行轨迹。语言模型只是可选的表达层，任何改动数值或丢失来源的改写都会被
程序拒绝。当前 baseline 有 116 个 Agent 治理案例，覆盖单轮、多轮、检索、教学、安全和证据充分性行为，
并保留完全离线运行能力。当前 baseline 有 327 个核心治理案例，并额外加入 129 个自然/困难 RAG 可信度案例，覆盖全部 40 个知识点；旧版 207 个治理案例仍作为历史说明保留。

## 为什么这是 Agent，而不只是聊天机器人

它不是把问题直接交给大模型生成答案，而是完成一个有状态的决策与执行闭环：

1. Curriculum Agent 根据输入、先修关系和学习状态决定学习目标；
2. 检索受课程范围约束的证据，并经过 answerability gate；
3. Tutor Agent 解释概念，或选择工具并解释已验证结果；
4. Assessment Agent 独立评估 quiz/practice 结果；
5. Assessment → Curriculum → Tutor 的 handoff 更新学习建议和反馈。

这是三个职责清晰的 bounded agents，而不是开放式自主 Agent。边界是有意设计的：教育和
数学场景更重视可验证性，不应该让模型任意生成函数名、代码或数据源。

## 三个 Agent 如何分工

Curriculum Agent 只读取 `data/curriculum.json`、先修关系和 SQLite 学习状态，输出
下一学习目标；Assessment Agent 只评估 quiz/practice 结果并标记是否需要复习；Tutor
Agent 只负责证据充分性约束下的解释、提示、比较和仿真反馈。

官方 LangGraph `StateGraph` 显式表达这些 handoff。RAG、Python 工具和 SQLite 是共享
服务，不被包装成 Agent，也不会因为多 Agent 名称而增加额外 LLM 调用。

## RAG 是怎么做的

知识库由 11 张人工整理的模块知识卡和 11 个 Notebook 中抽取的 Markdown cells
组成。检索先使用路由结果限制 module，再结合三部分分数：

- IDF 加权关键词与中英文字符特征；
- 向量余弦相似度；
- 主题、人工知识卡和完整短语 bonus。

默认向量后端是 384 维本地 hashing vector，它可解释、确定且不需要密钥，但不冒充
神经语义模型。配置兼容 embedding endpoint 后可分批建立神经向量索引；请求失败、
行号异常或维度变化时会回退到本地后端。

检索不是只靠“看起来相关”验收。44 个中英文 module-scoped case 计算 Hit@3 和 MRR，
当前本地基线为 Hit@3 1.0、MRR 1.0；报告同时保留每题名次、命中的人工相关性
短语和前三个来源，不能只展示一个汇总分数。

## 怎样防止数学幻觉

数值真相链路完全由 Python 工具负责。Agent 只允许调用注册表中的 15 个函数，参数
先解析再由模型函数校验，例如 M/M/1 只有在到达率小于服务率时才讨论平稳分布。

LLM 收到的是已经验证过的草稿。生成后，程序再次检查草稿中的每个数值锚点和准确
Notebook locator。只要有一个缺失或变化，就设置 `llm_applied=false` 并退回离线
答案。因此“不要改数字”不只是 prompt 要求，而是后置验证条件。

## 多轮对话怎样实现

每轮保存 module、tool 和已验证参数。下一轮如果只说“把到达率改成 0.8”，系统会
继承上一轮的 M/M/1 工具、服务率和时长，只替换明确提到的参数。继承字段会出现在
plan trace 中。状态保存在 SQLite，不依赖单个 Python 进程，因此重启 Agent 后仍能
继续同一 session。

## 教学能力如何评估

项目没有把“成功运行仿真”直接称为掌握知识。学习画像分开记录：

- 成功的受验证实验；
- 概念题正确率；
- 明确触发的概念误区。

页面称之为 practice evidence，而不是心理测量意义上的 mastery。10 个教学案例覆盖
六类误区和四个中性对照，检查纠正内容是否真正进入回答，以及成功回答是否包含
实验结果、理论理解、引导问题和来源。

## 为什么评测全通过仍不能说明产品有效

当前 488 个 case 是针对本课程的回归测试，只能证明已定义行为没有退化。它不能证明模型
具备通用数学推理能力，也不能证明学生学习效果提高。真正进入课程还需要教师审核、
学生试用、前后测设计和经过校准的题库。这是项目刻意保留的 Responsible AI 边界。

## 如果要支持线上多用户，下一步怎么做

当前架构适合单实例演示。线上化会依次加入：

1. 身份认证和 session 所有权校验；
2. PostgreSQL 学习记录与 Redis 分布式限流；
3. OpenTelemetry traces、集中指标和告警；
4. embedding 缓存与可学习 reranker；
5. 教师审核后台、内容版本和数据留存策略；
6. 人工标注的教学质量评测与线上 A/B 实验。

## 你做了哪些生产化处理

我把“能在本机跑”与“可以安全接收请求”分开处理：`/live` 只检查进程，`/ready`
还会验证 SQLite、11 模块、15 工具、知识索引、题库和评测语料版本。请求都有 ID、
稳定错误码、严格 JSON 类型、body/问题长度限制和两层限流边界。SQLite 使用 WAL、
外键、busy timeout、显式 schema version、留存天数和每会话事件上限。

仿真工具不仅限制单个参数，也限制 paths×steps 或期望事件总数。事件驱动模型在线
累计统计，只保留有界的画图样本。容器以非 root 用户运行；Compose 再加只读根目录、
capability 全部移除、禁止提权和 PID/CPU/内存限制。CI 会真实启动该配置并检查
`/ready` 与 `/openapi.json`。

## 性能怎么回答

不要把开发机数字说成线上 SLA。仓库提供独立 latency benchmark，对 11 个模块各选
一个代表问题，输出端到端和七节点的 p50/p95。当前本机单轮基线显示主要耗时在数值
工具节点，而分类、检索和内存写入明显更小。CI 保存报告用于比较，但不对共享 runner
设置容易抖动的硬阈值。真正上线后再以目标硬件、并发量和 SLO 做压测。

## 学习数据怎样做到可追溯和可删除

每个来源带课程语料 `corpus_sha256`，每次测验带题库 `bank_sha256`。学生可以分别
导出单次 Agent 运行和完整学习档案；完整档案含仿真历史、测验历史、当前推荐、内容
版本与留存策略。`DELETE /api/sessions/{id}` 只删除该 session。当前原型没有身份
认证，因此公开部署前必须在反向代理和数据库层增加用户身份与 session 所有权校验。

## 开源项目参考边界

我研究了 DeepTutor、OpenTutorAI、Study Buddy 和同学的 Mail Agent。借鉴的是检索
抽象、学习状态、provider 配置和 dashboard 信息层级。Mail Agent 使用 Fair Core
许可，因此本项目没有复制它的代码、素材或品牌，只独立实现通用布局思想。每个参考
仓库的 commit 和许可证都记录在 `research/open_source/README.md`。

## 五分钟演示顺序

1. 打开 Dashboard，指出 11 modules、15 tools 和动态评测指标。
2. 输入 M/M/1 示例，展示理论稳定性、图、工具参数和 Notebook 证据。
3. 展开证据摘录和 sparse/vector 分数，再展示七节点 trace。
4. 追问“把到达率改成 0.8”，展示持久化参数继承。
5. 输入布朗运动方差误区，展示透明纠正和学习画像。
6. 打开 `/health`、`/ready`、`/api/tools` 和 `/openapi.json`，说明工程监控、就绪
   判定与工具/API 参数契约。
