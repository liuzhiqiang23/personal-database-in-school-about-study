# A 部分 · 知识库概念全量（第 5 组：可观测 + 第 6 组：检索增强 + 第 7 组：长程脚手架）

## 第五组 可观测（4 篇）

### agent-tracing-model
- **关键点**：Langfuse 是双端架构（社区版自建 host / 官方 Cloud），默认记录所有 LLM 调用的 trace。核心组件：traces（一次会话/请求的完整调用链）、spans（trace 内部子操作，如某一步 model 调用）、observations（含 generation/event，记 token 用量）。
- **接入方式三种**：①LangChain callback（最常用，create_agent 配 callback 自动埋点）；②Langfuse SDK 显式 pack；③OpenTelemetry 手动（更底层更重）。教程主推 callback。
- **trace 的层次是「对话」**：trace 之上 user id 聚合、trace 之间 sorted 为 threads/ordered。
- **关联**：langfuse-selfhost-setup、langfuse-langchain-integration、observability-platform-choice。

### langfuse-selfhost-setup
- **关键点**：本地自建走 GitHub 仓库 + Docker compose。关键配置：前端 UI 端口（默认 3000）、写路径 /public、POST /api/public/trace 写 trace、GET /api/public/traces/{id} 读 trace。
- **统一环境变量驱动**：LANGFUSE_PUBLIC_KEY（连接公钥）、LANGFUSE_SECRET_KEY（连接私钥）、LANGFUSE_HOST（自建 host 或 cloud 地址）。三项齐配才认为「启用」。默认 Cloud 是 https://cloud.langfuse.com。
- **关联**：agent-tracing-model、langfuse-langchain-integration。

### langfuse-langchain-integration
- **关键点**：接入 LangChain 用 callback——from langfuse.callback import CallbackHandler，传给 create_agent 的 callbacks 参数。模型与交互靠 LANGFUSE_* 环境变量。trace 级别「traces=一次会话」是 LangChain 默认。
- **Token 计数**：默认按 model 的 pricing 表推 token，自建 host 走本机 tokenizer，手动传 metadata 带 token 用量。
- **关联**：langfuse-selfhost-setup、agent-tracing-model。

### observability-platform-choice
- **关键点**：provider 兼容——langfuse 支持 OpenAI、Anthropic、DeepSeek…… 各家 model 的 tokenizer。要在 UI 看 token 计数，需 provider 名称能对上 langfuse 的 model 表。
- **社区版 vs Cloud**：社区版自建（数据自控、需自己维护）；Cloud（省心、无需运维）。按数据合规与运维成本取舍。
- **关联**：agent-tracing-model、langfuse-langchain-integration。

## 第六组 检索增强（4 篇）

### document-chunking
- **关键点**：切块策略——按固定长度、按章节、按语义段落。块大小与重叠影响检索命中率。embedding 模型要与切块粒度匹配，否则检索命中率低。
- **关联**：embedding-and-vectorstore、agentic-rag-loop。

### embedding-and-vectorstore
- **关键点**：embedding 把文本转成向量，向量库（Chroma/FAISS 等）负责存储与检索。相似度检索、MMR、hybrid（BM25 混合）可调。
- **hybrid（向量+BM25）**在专有名词/编号查询场景更稳。
- **关联**：document-chunking、agentic-rag-loop。

### agentic-rag-loop
- **关键点**：让 Agent 决定何时检索而非一刀切。三要素——①检索工具（knowledge_retrieval，向量库+embedding）；②Grader（retrieval_grader，判断检索结果与问题相关性，可 LLM 承担）；③路由（由模型决定要不要检索）。
- **检索循环**：query → retrieve → grade → 若不合格可改查询/多轮再检 → 合格才进生成。retrieval 工具用 create_agent 的 tools 挂载（复用第 2 章工具循环）；grader 用结构化输出（复用第 3 章 response_format）。
- **关联**：document-chunking、embedding-and-vectorstore、retrieval-grader。

### retrieval-grader
- **关键点**：grader 判断检索结果与问题相关性——不合格则别直接进生成，应决定重检/改查询。本质上可复用结构化输出（response_format 定义 Grade(BaseModel): relevant: bool）。
- **关联**：agentic-rag-loop、structured-output-response-format。

## 第七组 长程脚手架与复用（5 篇）

### deepagents-harness
- **关键点**：DeepAgents 是跑「长程（long-horizon）」任务的脚手架——把几十上百步的大任务自动拆成可管理子任务、做成 todo 清单、必要时下放给子代理，并通过虚拟文件系统让长程上下文不被撑爆。pip install deepagents，0.6.7 要求 Python ≥3.11 且 <4.0。deepagents 提供的 harness 与 create_agent 兼容，能复用工具调用循环。
- **关联**：todo-planning-mechanism、subagent-delegation、virtual-filesystem-context-engineering。

### todo-planning-mechanism
- **关键点**：todo 机制——Agent 维护一个 todo 列表，每步更新、标记完成。可配 TodoListMiddleware（第 4 章内置项）。todo 计划要随进度「迭代更新」，别一次写完就不改。
- **关联**：deepagents-harness、builtin-middleware-catalog。

### subagent-delegation
- **关键点**：子代理委派——把独立子任务交给 subagent，隔离上下文、可并行。subagent 与主 agent 共享 checkpointer/thread 体系，务必带 thread_id 才能恢复。
- **关联**：deepagents-harness、checkpointer-persistence。

### virtual-filesystem-context-engineering
- **关键点**：虚拟文件系统——用「虚拟文件」承载中间产物/资料，避免把所有内容都塞进对话上下文，是一种「上下文工程」。长程任务的核心是控制上下文膨胀。
- **关联**：deepagents-harness、subagent-delegation。

### business-decoupling-reuse-pattern
- **关键点**：换工具即换业务——Agent 能力边界由工具列表定义。只把新工具函数加进 tools=[] 列表，不改其他任何代码，create_agent 自动把新工具 docstring 注册进模型可调用范围（第 2 章「换工具即换业务」；第 3 章「换 schema 即换业务」；第 4 章「middleware 换 agent 即复用」）。这是业务解耦复用模式。
- **关联**：create-agent-entry、tool-function-contract、builtin-middleware-catalog。
