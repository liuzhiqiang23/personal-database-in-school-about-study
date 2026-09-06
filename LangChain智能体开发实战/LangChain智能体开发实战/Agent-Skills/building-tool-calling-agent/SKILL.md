---
name: building-tool-calling-agent
description: 用 LangChain v1 的 create_agent 把一组业务函数组装成能自主调用工具的智能体，并从消息流里逐步核对它每一步做了什么。Use when 需要搭一个会调工具的 Agent、把已有业务函数接给模型、给 Agent 加新能力、或排查「模型不调工具 / 反过来追问参数 / 组装时报 must have a docstring」这类问题时。涵盖工具函数规范、create_agent 组装、invoke 与 stream 两种调用、单工具与并行多工具消息流解读、扩能力复用；不含结构化输出（见 extracting-structured-output）与多轮记忆（见 persisting-agent-memory）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、定义业务工具集
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#3、docstring 为什么不是可选项
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、create_agent 组装与返回对象
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、system_prompt：控制「怎么说」而非「做什么」
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、invoke 单工具问题
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、逐条拆解消息流
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、一个问题触发多个工具
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、invoke vs stream：让循环肉眼可见
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、新增 query_inventory 工具再跑
---

## 能力目标

把若干业务函数交给模型，用一次 `create_agent` 组装成可执行的智能体：模型自己决定调哪个工具、传什么参数、要不要并行调多个，开发者不写任何 `if/else` 分发逻辑；并能从返回的消息流里逐条读出 Agent 每一步的决策，为后续扩能力与排障提供依据。

## 前置

- 已装好 LangChain v1 生态与模型凭证，模型必须支持工具调用（见 bootstrapping-langchain-env）。
- 工具函数是 Agent 的能力单元：一个带类型注解与文档字符串、返回字符串的普通 Python 函数。

## 实操流程

1. 写工具函数。三条规范缺一不可：**带类型注解、带文档字符串、返回字符串**。文档字符串不是注释，它是这个工具向模型暴露的能力描述，模型据此判断何时调用：

   ```python
   # tools.py
   def query_order(order_id: str) -> str:
       """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
       return "已发货，预计明天到达"

   def calc_shipping_fee(origin: str, destination: str, weight_kg: float) -> str:
       """计算运费。origin 出发城市，destination 目的城市，weight_kg 包裹重量（公斤）。"""
       fee = round(10 + weight_kg * 3, 1)
       return f"从{origin}到{destination}，重量 {weight_kg} kg，预估运费 {fee} 元"
   ```

   函数体可以是任意真实逻辑（查库、调 REST API、读文件），开发期先返回固定字符串便于观察循环本身。

2. 一次 `create_agent` 组装。注意 v1 的官方入口是 `from langchain.agents import create_agent`：

   ```python
   # agent_core.py
   from langchain.agents import create_agent
   from tools import query_order, track_shipping, calc_shipping_fee

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[query_order, track_shipping, calc_shipping_fee],
       system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
   )
   print("agent 类型:", type(agent).__name__)
   ```

   ```bash
   python agent_core.py
   ```

   打印出的类型是 `CompiledStateGraph`——组装的产物是一张编译好的可执行图，因此天然带 `invoke`（一次性执行）与 `stream`（流式执行）两个调用入口。

3. 用 `invoke` 发一个只需单个工具的问题，把返回的消息流逐条打印出来：

   ```python
   from langchain_core.messages import HumanMessage

   result = agent.invoke({"messages": [HumanMessage(content="订单 A1001 是什么状态？")]})
   for i, msg in enumerate(result["messages"]):
       print(f"[{i}] {type(msg).__name__}", getattr(msg, "tool_calls", None), msg.content)
   ```

   正常输出是 4 条：HumanMessage、带 `tool_calls` 的 AIMessage、ToolMessage、最终 AIMessage。`AIMessage.tool_calls` 是字典列表，每项含 `name`、`args`、`id`；ToolMessage 的 `tool_call_id` 等于对应请求的 `id`，多工具并发时靠它把结果路由回正确的请求。

4. 发一个需要两件独立事情的问题，验证并行工具调用。**问题里必须把参数给全**，否则模型会反过来追问而不是猜一个默认值：

   ```python
   q = "帮我查一下订单 A1001 的最新物流状态，同时帮我算一下 1.5kg 商品从北京寄到上海的运费。"
   result = agent.invoke({"messages": [HumanMessage(content=q)]})
   print("消息总条数:", len(result["messages"]))
   ```

   预期消息总数是 5 条而不是 6 条：两次工具调用挂在**同一条** AIMessage 上并行发起，随后是两条 ToolMessage、再是最终回答。

5. 需要把循环一步步展示给人看时改用 `stream`，它按图节点吐增量：

   ```python
   for chunk in agent.stream({"messages": [HumanMessage(content="订单 A1001 是什么状态？")]}):
       for node, payload in chunk.items():
           print("节点:", node, payload["messages"][-1])
   ```

   节点名是 `model` 与 `tools`（不是 `agent`），chunk 数等于循环步数。一次性拿最终答案用 `invoke`；需要实时反馈、进度可视化用 `stream`。

6. 给 Agent 加新能力时，只往 `tools=[]` 列表里多加一个函数，其他代码一行不改：

   ```python
   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[query_order, track_shipping, calc_shipping_fee, query_inventory],
       system_prompt="你是一个订单运营助手……",
   )
   ```

   新工具的文档字符串会自动注册进模型的可调用范围，问一个库存问题它立刻会调用它。

## 校验回路

按三步自检，三项都过才算这个 Agent 真正跑通：

1. **单工具**：问一个只需一个工具的问题，消息流里出现该工具的 `tool_calls` 与对应 ToolMessage，最终回答复用了工具返回的内容。
2. **多工具**：问一个需要两个工具的问题（参数给全），统计 `工具调用总次数 ≥ 2`，且并行时两次调用挂在同一条 AIMessage 上。
3. **扩能力**：再加一个工具进列表、问一个新问题，确认不改其他代码它就被调用。

排障入口固定是消息流：逐条看是「模型没调工具」「参数缺失被追问」还是「工具返回有误」。

## 常见陷阱

- **工具漏写文档字符串**：报错发生在 `create_agent()` 组装阶段而非 `invoke()` 运行阶段，信息是 `ValueError: Function must have a docstring if description not provided.`——程序根本起不来。补文档字符串，或在创建工具时显式传 `description`。
- **指望改系统提示词让模型改调用行为**：系统提示词控制「怎么说」不控制「做什么」。同一组工具换提示词，回答风格变、工具调用序列不变。要改调用判断，改工具的文档字符串措辞。
- **复合问题里漏给参数**：缺少必填参数时模型遵循不猜参数原则，宁可追问也不编默认值，表现为「只调了一个工具就停下反问」。把参数补进问题即可。
- **按旧资料解析 stream 事件**：v1 的节点名确定为 `model` 与 `tools`，旧版资料里的节点名可能不同，迁移时以 `model` 为准。
