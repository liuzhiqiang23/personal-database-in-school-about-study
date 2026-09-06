---
concept: message-stream-anatomy
one_liner: 消息流是读懂智能体每一步做了什么的索引，四类消息各司其职，工具结果靠 tool_call_id 路由回对应请求
stage_span: [stage-1, stage-2]
prerequisites: [tool-calling-loop]
related: [parallel-tool-calls, state-snapshot-inspection, agent-tracing-model]
applications: [middleware-flow-control, state-snapshot-inspection, human-in-the-loop-interrupt]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、运行与结果解读
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、逐条拆解消息流
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、invoke 单工具问题
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、get_state_history：看完整时间线
---

## 是什么

一次调用返回的 `result["messages"]` 是一条消息链，记录了循环每一步的痕迹。它既是理解原理的窗口，也是排障时的第一手证据——智能体行为不符预期时，逐条读消息流就能定位是"模型没调工具""参数缺失被追问"还是"工具返回有误"。

三类消息各司其职：`HumanMessage` 是输入；`AIMessage` 承载模型的决策与最终回答；`ToolMessage` 承载工具执行结果。消息类型就是"读懂智能体在哪一步做了什么"的索引。

## 怎么用

逐条打印每条消息的类型与关键字段：

```python
for i, msg in enumerate(result["messages"]):
    print(f"type    : {type(msg).__name__}")
    print(f"content : {msg.content}")
    print(f"tool_calls: {getattr(msg, 'tool_calls', None)}")
```

真实字段级输出：

```
── 消息 [1] ────────────────────────────
  type    : AIMessage
  content : 好的，我来查询一下订单 A1001 的当前状态。
  tool_calls:
    - name  : query_order
      args  : {'order_id': 'A1001'}
      id    : call_00_L7m10XIu...

── 消息 [2] ────────────────────────────
  type    : ToolMessage
  content : 已发货，预计明天到达
  tool_call_id: call_00_L7m10XIu...
```

## 关键细节与参数

- **`AIMessage.tool_calls` 是字典组成的列表**，每个字典含 `name`（工具名）、`args`（参数）、`id`（调用编号）三个字段。
- **`AIMessage` 可以同时有 `content` 和 `tool_calls`**：模型能一边说"好的，我来查询一下"一边发出工具调用请求，两者并不互斥。也存在 `content` 为空、只带 `tool_calls` 的形态。
- **`ToolMessage.tool_call_id` 等于发起请求那条 `AIMessage` 里 `tool_calls[].id`**：这是结果路由机制。一个回合里同时发出多个工具调用时，靠这个 id 保证每条工具返回对应回正确的请求。自定义构造 `ToolMessage` 时漏掉这个字段，模型会因"有工具调用却没有对应结果"而返回 400 错误。
- **一次工具调用在消息流里占 3 条**（带 `tool_calls` 的 AI 消息 + 工具消息 + 最终 AI 消息），加上用户消息，单工具问答共 4 条。
- 从检查点存档里读到的消息类型标识是小写形态：`human`、`ai`、`tool`。
- 存档保存的是**完整消息列表而非对话摘要**，模型调工具时的决策（藏在 `tool_calls` 字段里）与工具返回结果原样保留。

## 常见陷阱

- **把空 `content` 的 AI 消息当成模型失灵**：模型决定调工具时，这条消息的文本内容可能为空，关键信息全在 `tool_calls` 字段里。
- **自造工具结果时漏 `tool_call_id`**：在中间件里捕获工具异常、自行构造 `ToolMessage` 回填时，必须带 `tool_call_id=request.tool_call["id"]`，否则模型报 400。
- **按消息条数猜工具调用次数**：并行工具调用时多个请求挂在同一条 AI 消息上，消息条数会少于"每工具 3 条"的直觉估算（见 parallel-tool-calls）。
