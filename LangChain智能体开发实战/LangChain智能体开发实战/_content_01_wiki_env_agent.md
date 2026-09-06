# A 部分 · 知识库概念全量（第 1 组：环境生态 + 第 2 组：智能体核心与输出契约）

本部分覆盖知识库 API 概念文章的环境与生态、智能体核心与输出契约两大能力域，逐篇提取关键定义、用法、场景与关联概念。

## 第一组 环境与生态（4 篇）

### python-env-and-venv-setup
- **关键点**：Python 环境隔离是第一个坑。macOS 系统自带 python3 常为 3.9（不满足 langchain 的 3.10+ 要求），需用 Homebrew 等安装的高版本解释器建 venv。虚拟环境必须用满足版本要求的解释器创建。
- **核心命令**：`/opt/homebrew/bin/python3.13 -m venv .venv && source .venv/bin/activate`。
- **关联**：local-environment-traps、langchain-package-stack。

### langchain-package-stack
- **关键点**：LangChain v1 是分层包生态，框架、编排运行时、模型提供方集成包各自独立发布、按需安装。核心三件套 langchain + langgraph + langchain-deepseek。装 langchain-deepseek 会连带拉入 langchain-openai 与 openai（DeepSeek 走 OpenAI 兼容协议）。
- **核验版本统一用 importlib.metadata**：`from importlib.metadata import version`，langgraph 顶层无 __version__。
- **关联**：deepseek-provider-integration、python-env-and-venv-setup。

### deepseek-provider-integration
- **关键点**：DeepSeek 通过环境变量 DEEPSEEK_API_KEY 读凭证。model 参数用「提供方:模型名」格式（如 "deepseek:deepseek-chat"）。**必须用 deepseek-chat**（支持工具调用与并行调用），**不能用 deepseek-reasoner**（官方明确不支持工具调用与结构化输出）。
- **凭证安全**：不在终端回显明文、验证时只打印前 3 字符 + 长度脱敏。
- **关联**：langchain-package-stack、structured-output-strategy-compat。

### local-environment-traps
- **关键点**：收集本地环境陷阱——系统 Python 偏旧、Ignoring invalid distribution -pip 警告（外置 SSD 上 ~ 前缀残留文件）、查 langgraph 版本属性报错等。都是「环境没对齐」导致的非代码问题。
- **关联**：python-env-and-venv-setup、invoke-vs-stream。

## 第二组 智能体核心与输出契约（10 篇）

### create-agent-entry
- **关键点**：create_agent 是 Agent 的工厂函数，把「模型 + 工具 + system_prompt」组装成可执行的 CompiledStateGraph。返回类型是 langgraph.graph.state.CompiledStateGraph，天然有 invoke / stream。
- **依赖**：middleware、checkpointer、response_format 都是它的可选参数，分别对应后续章节的能力。
- **关联**：tool-calling-loop、message-stream-anatomy、invoke-vs-stream。

### tool-function-contract
- **关键点**：工具函数 = 带类型注解 + docstring 的普通 Python 函数。**docstring 是硬约束而非可选**——框架把所有工具 docstring 拼成能力清单交给模型；漏写则在 create_agent 组装阶段报 ValueError: Function must have a docstring if description not provided.，这是「快速失败」设计。
- **两条出路**：写 docstring，或创建工具时显式传 description 参数。
- **关联**：create-agent-entry、tool-calling-loop。

### tool-calling-loop
- **关键点**：核心循环四步——推理 → 调工具 → 结果喂回 → 继续推理直到完成。Agent 中「调用哪个函数、何时调、调几次」由模型推理决定，开发者不写分发逻辑。
- **关联**：create-agent-entry、message-stream-anatomy、parallel-tool-calls。

### message-stream-anatomy
- **关键点**：四种消息类型——HumanMessage（输入）、AIMessage（承载决策与最终回答）、ToolMessage（工具结果）。AIMessage 可同时有 content 和 tool_calls（「边说话边行动」）。ToolMessage 靠 tool_call_id 对应回 AIMessage 里 tool_calls[].id。AIMessage.tool_calls 是字典列表，每个含 name / args / id。
- **一次工具调用在 messages 里占 3 条**（ai + tool + ai）。
- **关联**：tool-calling-loop、parallel-tool-calls、structured-output-response-format。

### parallel-tool-calls
- **关键点**：deepseek-chat 支持并行工具调用。两个独立任务挂在同一条 AIMessage 里并行发起（消息总数更少），而非顺序调用。结果路由仍靠 tool_call_id 保证对应正确。
- **关联**：message-stream-anatomy、tool-calling-loop。

### system-prompt-boundary
- **关键点**：system_prompt 控制模型「怎么说」，不控制「做什么」。调哪个工具由工具 docstring + 用户问题共同决定，system_prompt 不参与这一层。
- **关联**：create-agent-entry、tool-function-contract。

### invoke-vs-stream
- **关键点**：invoke 返回 dict（result["messages"] 是跑完的完整消息列表）；stream 返回生成器（每个 chunk 只含当前步骤增量）。stream 的 chunk 数等于循环步数。节点名是 model 不是 agent。
- **关联**：message-stream-anatomy、create-agent-entry。

### pydantic-schema-design
- **关键点**：结构化输出的 schema 用 Pydantic 定义——继承 BaseModel、类型注解声明字段、实例化自动校验。Field(description=...) 不只是给人看，会被框架传给模型引导「字段该填什么」。要锁定字段取值用 Literal 类型或在描述列出可选项。
- **关联**：structured-output-response-format、structured-output-strategy-compat。

### structured-output-response-format
- **关键点**：给 create_agent 传 response_format 参数开启结构化输出，结果落在 result["structured_response"] key（校验过的对象，可 .字段名 取值）。response_format 接受三种写法：直接传 schema 类、显式 ToolStrategy、显式 ProviderStrategy。
- **开启后 result 只有两个 key**：messages 和 structured_response。结构化对象不混在消息里。
- **结构化两层保护**：field description 引导（下沉提示词工程）+ Pydantic 强制校验。
- **关键坑**：老做法「让模型输出 JSON 再手动解析」在 v1 被移除——那是类型不安全、键名不可控的字符串。
- **关联**：pydantic-schema-design、structured-output-strategy-compat。

### structured-output-strategy-compat
- **关键点**：两种策略——ToolStrategy（工具调用兜底，适用面广，任何支持工具调用的模型都能用；把 schema 字段封装成「工具」参数，让模型以「调用工具」方式「填写」字段，再提取参数做 Pydantic 校验）；ProviderStrategy（provider 原生结构化输出 API，约束更直接可靠，但前提是该 provider 提供该端点）。
- **兼容性矩阵**：DeepSeek deepseek-chat（ToolStrategy ✅ / ProviderStrategy ❌）；OpenAI GPT-4o（两者都可，ProviderStrategy 更稳）；Anthropic Claude 3.5（两者都可，ProviderStrategy 更稳）；本地 Ollama（ToolStrategy ✅ / ProviderStrategy 一般不支持）。
- **DeepSeek 上 ProviderStrategy 报 400 BadRequestError "This response_format type is unavailable now" 是预期内兼容性边界**，正确做法是退回 ToolStrategy，而非换模型。
- **关联**：structured-output-response-format、deepseek-provider-integration。
