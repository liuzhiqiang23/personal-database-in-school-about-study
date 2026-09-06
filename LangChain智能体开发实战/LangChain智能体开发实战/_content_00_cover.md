# LangChain 智能体开发实战 · 学习笔记

> 本学习笔记由《LangChain智能体开发实战》学习资料包系统整理而成，覆盖资料包全部知识点，按 A~E 框架组织：A 知识库概念全量、B 课件逐节全量、C Agent-Skills 全量解读、D 适配指南、E 练习清单。全部内容来自真实执行的实验记录，每条命令、每个版本号、每个参数均可复现。

## 资料包结构与四层说明

本资料包由九天智课出品，全部内容来自一台 Mac mini（M4 / macOS 26.4.1 / arm64）上的真实执行，不是示意图。包内结构为四层：

| 层次 | 内容 | 作用 |
|------|------|------|
| 课件（PDF / Markdown） | 212 页完整课件，9 个主题 | 按「学习顺序」讲，从环境搭建到长程智能体 |
| 知识库（41 篇 + 图谱） | 41 篇概念文章 + 可视化知识图谱 | 按「概念」组织，查具体问题更快 |
| Agent-Skills（13 个技能） | 13 个可导入的 Agent 技能 | 知识库让 Agent「懂」，技能让 Agent「会做」 |
| 使用说明 | 这份使用说明 | 结构导航 |

## 9 章课件目录

| 章节 | 内容 |
|------|------|
| 第 1 章 | 从零到一跑通 LangChain v1 环境 |
| 第 2 章 | 智能体核心 create_agent 与工具调用循环 |
| 第 3 章 | 结构化输出：让 Agent 返回可编程消费的数据 |
| 第 4 章 | 中间件系统：限流、脱敏、重试、降级 |
| 第 5 章 | 持久化记忆：让 Agent 记住多轮对话 |
| 第 6 章 | 人在回路：危险动作前暂停等人审批 |
| 第 7 章 | 可观测性：接入 Langfuse 看清每一步调用 |
| 第 8 章 | Agentic RAG：让 Agent 自己决定何时检索 |
| 第 9 章 | DeepAgents：扛住十几步以上的长链路任务 |

## 8 大能力域导航

知识库 41 篇概念文章可归入 8 大能力域（本笔记整合为 7 组，检索增强与长程脚手架分开）：

1. **环境与生态**（4 篇）：python-env-and-venv-setup、langchain-package-stack、deepseek-provider-integration、local-environment-traps
2. **智能体核心与输出契约**（10 篇）：create-agent-entry、tool-function-contract、tool-calling-loop、message-stream-anatomy、parallel-tool-calls、system-prompt-boundary、invoke-vs-stream、pydantic-schema-design、structured-output-response-format、structured-output-strategy-compat
3. **中间件与横切**（5 篇）：middleware-hooks、middleware-execution-order、builtin-middleware-catalog、pii-redaction-middleware、middleware-flow-control
4. **状态、记忆与审批**（9 篇）：checkpointer-persistence、thread-id-isolation、state-snapshot-inspection、time-travel-replay、checkpointer-backends、human-in-the-loop-interrupt、interrupt-resume-replay、hitl-iron-rules、hitl-implementation-routes
5. **可观测**（4 篇）：agent-tracing-model、langfuse-selfhost-setup、langfuse-langchain-integration、observability-platform-choice
6. **检索增强**（4 篇）：document-chunking、embedding-and-vectorstore、agentic-rag-loop、retrieval-grader
7. **长程脚手架与复用**（5 篇）：deepagents-harness、todo-planning-mechanism、subagent-delegation、virtual-filesystem-context-engineering、business-decoupling-reuse-pattern

## 13 个 Agent-Skills 一览

| 能力域 | 技能 |
|--------|------|
| 环境与安装 | bootstrapping-langchain-env |
| 智能体核心 | building-tool-calling-agent、extracting-structured-output |
| 中间件 | writing-agent-middleware、applying-builtin-middleware |
| 记忆与状态 | persisting-agent-memory、inspecting-checkpoint-state |
| 人工审批 | gating-agent-actions-with-approval |
| 可观测 | deploying-langfuse-selfhost、tracing-langchain-agent |
| 检索增强 | building-agentic-rag、grading-retrieved-documents |
| 长程任务 | building-long-horizon-agent |

## 统一实测基线

- 系统：macOS 26.4.1 arm64（Mac mini M4）
- Python：3.13.13
- 包版本：langchain 1.3.2、langchain-core 1.4.0、langgraph 1.2.2、langchain-deepseek 1.0.1、langchain-openai 1.2.2、openai 2.38.0
- 模型：DeepSeek deepseek-chat（支持工具调用与并行调用；deepseek-reasoner 不支持工具调用与结构化输出）
- 工具：langfuse v4.7.1、deepagents 0.6.7（Python ≥3.11 且 <4.0）
