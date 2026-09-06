---
concept: create-agent-entry
one_liner: create_agent 把「模型 + 工具 + 提示词」这份声明式配置编译成一张可执行的 LangGraph 图，是 LangChain v1 搭智能体的官方入口
stage_span: [stage-1, stage-2]
prerequisites: [langchain-package-stack, deepseek-provider-integration]
related: [tool-function-contract, system-prompt-boundary, invoke-vs-stream]
applications: [tool-calling-loop, structured-output-response-format, middleware-hooks, checkpointer-persistence, agentic-rag-loop, deepagents-harness]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#1、Demo 脚本结构
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、create_agent 组装与返回对象
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、用 ToolStrategy 包装 schema 传给 create_agent
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、给 create_agent 传 checkpointer=InMemorySaver()
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、用 create_deep_agent 一行搭出长程 Agent
---

## 是什么

`create_agent` 是 LangChain v1 里搭建智能体的官方入口，导入路径为 `from langchain.agents import create_agent`。它接收一份声明式配置——模型、工具列表、系统提示词，以及可选的结构化输出、中间件、检查点存储器——**编译**出一个可执行对象。

关键在于返回值：类型是 `langgraph.graph.state.CompiledStateGraph`。这揭示了它的本质——不是"把工具绑到模型上"，而是把配置编译成一张 LangGraph 可执行图。正因为返回的是编译好的图对象，它天然拥有 `invoke`（一次性执行）与 `stream`（流式执行）两种调用能力，也天然能接住 LangGraph 的状态、检查点、中断等图级能力。

这个返回类型在所有场景下保持恒定：加不加结构化输出、加不加检查点存储器、乃至换用长程脚手架入口，返回的都是 `CompiledStateGraph`。能力是叠加上去的，不是另起一套 API。

## 怎么用

最小组装：三个参数各司其职——`model` 指定底层模型，`tools` 是工具函数列表，`system_prompt` 定义角色与说话风格。

```python
from langchain.agents import create_agent
from tools import query_order, track_shipping, calc_shipping_fee

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
)
print("agent 类型:", type(agent))   # <class 'langgraph.graph.state.CompiledStateGraph'>
```

按需叠加能力，都是在同一个调用上加参数：

```python
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(ReviewAnalysis),   # 结构化输出
)

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order],
    middleware=[log_before, ModelCallLimitMiddleware(run_limit=2)],   # 横切逻辑
    checkpointer=InMemorySaver(),                                     # 多轮记忆
)
```

## 关键细节与参数

- 组装成功后可直接读取挂载物，例如 `agent.checkpointer` 返回挂上去的检查点存储器实例（类型 `InMemorySaver`）。
- 组装是**编译期**动作：工具规范不合格时在这一步就报错，而不是等到调用阶段（见 tool-function-contract）。
- 图的内部节点名是 `model` 与 `tools`（不是 `agent`），流式调用与中间件挂载点都以此为准。
- 长程脚手架入口 `create_deep_agent` 与它同源：返回同样的 `CompiledStateGraph`，差别只是自动预装了若干中间件（见 deepagents-harness）。
- 智能体的能力边界由 `tools` 列表定义——新增能力只需往列表里加函数，无需改动其他任何代码。

## 常见陷阱

- **import 路径写错**：v1 的官方入口是 `from langchain.agents import create_agent`，参考旧版资料容易写成别的路径。
- **误以为加了能力就换了对象类型**：挂上检查点存储器或结构化输出后仍是 `CompiledStateGraph`，`invoke` / `stream` / `get_state` 全部照常可用；发现调用方式"不认识"时，通常是参数传法不对而非对象变了。
- **在图节点名上沿用旧版资料**：解析流式事件时节点名是 `model` 和 `tools`，旧版资料里的节点名可能不同，迁移时以 `model` 为准。
