# C 部分 · Agent-Skills 全量解读（13 个技能）

知识库负责让 Agent「懂」（理解概念），技能负责让 Agent「会做」（可执行的、标准化的操作步骤）。本部分逐个说明每个技能做什么、何时用、与知识库对应章节的分工。技能均来自 `Agent-Skills/` 目录，标准 frontmatter（name / description / allowed-tools / sources）格式，可直接导入 `~/.claude/skills/`。

## 环境与安装

### bootstrapping-langchain-env
- **做什么**：从零搭建一个可跑的 LangChain v1 环境——核对 Python 版本、建立隔离 venv、安装分层生态包（langchain + langgraph + langchain-deepseek）、配置模型凭证（DEEPSEEK_API_KEY）、核验版本，最后跑通最小示例。
- **何时用**：新机器 / 新项目起步，或环境报版本、依赖问题时。
- **分工**：对应第 1 章 + 知识库「python-env-and-venv-setup / langchain-package-stack / local-environment-traps」。

## 智能体核心

### building-tool-calling-agent
- **做什么**：用 create_agent 组装一个工具调用 Agent——定义带 docstring 的业务工具、组装、invoke/stream 运行、遍历 messages 拆解工具调用循环、验证多工具并行协作。
- **何时用**：开始写任何 Agent 时。
- **分工**：对应第 2 章 + 知识库「create-agent-entry / tool-function-contract / tool-calling-loop / message-stream-anatomy / parallel-tool-calls / invoke-vs-stream」。

### extracting-structured-output
- **做什么**：让 Agent 返回校验过的结构化对象——用 Pydantic 定义 schema、给 create_agent 传 response_format（ToolStrategy/ProviderStrategy）、从 result["structured_response"] 取值、批量计算。
- **何时用**：需要把 Agent 结果交给下游程序、要做计数/过滤/排序时。
- **分工**：对应第 3 章 + 知识库「pydantic-schema-design / structured-output-response-format / structured-output-strategy-compat」。

## 中间件

### writing-agent-middleware
- **做什么**：写自定义横切逻辑中间件——用装饰器式（@before_model 等）或类式（继承 AgentMiddleware）实现 6 个 hook，理解执行顺序（before 正序 / after 逆序 / wrap 嵌套），实现日志、计数等。
- **何时用**：凡是「每个地方都要加的一段代码」（日志、计数、状态统计）。
- **分工**：对应第 4 章 + 知识库「middleware-hooks / middleware-execution-order」。

### applying-builtin-middleware
- **做什么**：直接应用 14 个内置 middleware——限流（ModelCallLimitMiddleware）、脱敏（PIIMiddleware）、重试（Model/ToolRetry）、降级（ModelFallback）、上下文摘要、HITL、TodoList 等，一行声明即可。
- **何时用**：不想手写、直接用现成能力时。
- **分工**：对应第 4 章 + 知识库「builtin-middleware-catalog / pii-redaction-middleware / middleware-flow-control」。

## 记忆与状态

### persisting-agent-memory
- **做什么**：给 Agent 装上持久化记忆——加 checkpointer（InMemorySaver/SqliteSaver/PostgresSaver）、用 thread_id 隔离会话、实现多轮连续对话与跨进程持久化。
- **何时用**：需要「连续对话」「记住前文」「不同用户隔离」时。
- **分工**：对应第 5 章 + 知识库「checkpointer-persistence / thread-id-isolation / checkpointer-backends」。

### inspecting-checkpoint-state
- **做什么**：检查状态快照——用 get_state 看 StateSnapshot（8 字段）、get_state_history 看完整时间线、时间旅行重放。
- **何时用**：调试 Agent「为什么这么想」、回放历史、定位中断点。
- **分工**：对应第 5 章 + 知识库「state-snapshot-inspection / time-travel-replay」。

## 人工审批

### gating-agent-actions-with-approval
- **做什么**：给 Agent 的危险动作加人工审批闸门——用 interrupt + Command(resume=...) 或 HumanInTheLoopMiddleware，让关键动作在危险边缘等人确认。
- **何时用**：真实转账、不可撤回邮件、删数据等高风险动作。
- **分工**：对应第 6 章 + 知识库「human-in-the-loop-interrupt / interrupt-resume-replay / hitl-iron-rules / hitl-implementation-routes」。

## 可观测

### deploying-langfuse-selfhost
- **做什么**：自建 Langfuse——Docker compose 拉起、配 LANGFUSE_* 三项环境变量、UI 端口、traces/spans/observations 结构。
- **何时用**：数据要自控、不想上云时。
- **分工**：对应第 7 章 + 知识库「langfuse-selfhost-setup / observability-platform-choice」。

### tracing-langchain-agent
- **做什么**：给 LangChain Agent 接 Langfuse 追踪——用 CallbackHandler 接入 create_agent 的 callbacks、配 metadata（user_id）、看 trace 里的 prompt/响应/token 成本。
- **何时用**：开发调试「每一步发生了什么」、上线排查问题。
- **分工**：对应第 7 章 + 知识库「agent-tracing-model / langfuse-langchain-integration」。

## 检索增强

### building-agentic-rag
- **做什么**：搭 Agentic RAG——检索工具（向量库+embedding）、grader（结构化输出）、由 Agent 决定何时检索、检索循环 query→retrieve→grade→生成。
- **何时用**：知识库问答、票据助手、企业资料问答等「并不总是需要检索」的场景。
- **分工**：对应第 8 章 + 知识库「document-chunking / embedding-and-vectorstore / agentic-rag-loop」。

### grading-retrieved-documents
- **做什么**：给检索结果打分——用结构化输出定义 Grade(relevant: bool)，判断检索结果与问题相关性，不合格则决定重检/改查询。
- **何时用**：RAG 检索质量不稳定、需要过滤噪音时。
- **分工**：对应第 8 章 + 知识库「retrieval-grader / agentic-rag-loop」。

## 长程任务

### building-long-horizon-agent
- **做什么**：搭长程任务 Agent——用 deepagents harness + todo 规划 + 子代理委派 + 虚拟文件系统，扛住十几步以上长链路。
- **何时用**：任务固有步骤 ≥10 步、需阶段性产出、需隔离上下文。
- **分工**：对应第 9 章 + 知识库「deepagents-harness / todo-planning-mechanism / subagent-delegation / virtual-filesystem-context-engineering」。

## 技能与课程分工总览

| 能力域 | 技能 | 对应章节 |
|--------|------|----------|
| 环境与安装 | bootstrapping-langchain-env | 第 1 章 |
| 智能体核心 | building-tool-calling-agent | 第 2 章 |
| 智能体核心 | extracting-structured-output | 第 3 章 |
| 中间件 | writing-agent-middleware | 第 4 章 |
| 中间件 | applying-builtin-middleware | 第 4 章 |
| 记忆与状态 | persisting-agent-memory | 第 5 章 |
| 记忆与状态 | inspecting-checkpoint-state | 第 5 章 |
| 人工审批 | gating-agent-actions-with-approval | 第 6 章 |
| 可观测 | deploying-langfuse-selfhost | 第 7 章 |
| 可观测 | tracing-langchain-agent | 第 7 章 |
| 检索增强 | building-agentic-rag | 第 8 章 |
| 检索增强 | grading-retrieved-documents | 第 8 章 |
| 长程任务 | building-long-horizon-agent | 第 9 章 |

> 13 个技能与 9 章课程逐一对应：**章节讲「为什么/原理」，技能给「怎么做/标准步骤」**，知识与技能互补。已全部复制到 `~/.claude/skills/`，重启 Claude Code 会话后即可见于 Skill 工具列表。
