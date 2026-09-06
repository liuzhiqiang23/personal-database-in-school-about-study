---
concept: tool-calling-loop
one_liner: 智能体的核心范式是模型在一个循环里自主调用工具、读结果、再决定下一步，直到任务完成
stage_span: [stage-1, stage-2]
prerequisites: [create-agent-entry, tool-function-contract]
related: [message-stream-anatomy, parallel-tool-calls, invoke-vs-stream]
applications: [middleware-hooks, checkpointer-persistence, agentic-rag-loop, agent-tracing-model]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、运行与结果解读
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#一、开篇：用一个订单助手理解 Agent 的「工具调用循环」
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、invoke 单工具问题
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、写装饰器式 middleware 并挂载
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#一、开篇：Agent 为什么比传统 Web 更难调试
---

## 是什么

智能体与传统程序的分界线就在这个循环上。传统程序像一份写死的操作手册：开发者用 `if/else` 判断用户意图、决定调哪个函数，每个分支都得提前规定好。智能体则是把工具交出去、把任务说清楚，**调用哪个工具、何时调、调几次，由模型自己推理决定**，开发者不再手写分发逻辑。

官方对智能体的定义是"a model calling tools in a loop until a given task is complete"（模型在循环中调用工具，直到任务完成）。循环由四步构成：

1. **推理**：模型读到用户问题，判断需要调用哪个工具、传什么参数；
2. **调工具**：框架按模型的决定执行对应函数；
3. **结果喂回**：工具返回值被重新交给模型；
4. **继续推理直到完成**：模型基于工具结果，要么再调下一个工具，要么生成最终回答。

这个循环是后续所有能力的地基：中间件的挂载时机按它划分，记忆存的是它产生的消息，可观测追踪的是它的每一步，检索增强不过是把检索器变成循环里的一个工具。

## 怎么用

发起一次调用，然后遍历返回的消息流，就能看见完整一轮循环：

```python
from langchain_core.messages import HumanMessage

result = agent.invoke({"messages": [HumanMessage(content="订单 A1001 是什么状态？")]})

for i, msg in enumerate(result["messages"]):
    print(f"  [{i}] {type(msg).__name__} → ...")
```

真实终端输出（单工具问题，四条消息一一对应循环四步）：

```
消息流（工具调用循环）:
  [0] HumanMessage → 订单 A1001 是什么状态？
  [1] AIMessage → tool_calls: [('query_order', {'order_id': 'A1001'})]
  [2] ToolMessage → content: 已发货，预计明天到达
  [3] AIMessage（最终回答）→ 订单 A1001 当前的状态是已发货，预计明天到达。
消息总条数: 4
```

## 关键细节与参数

- **一次调用 = 多轮模型调用**：含一次工具调用的问题需要两轮模型调用——第一轮决定调哪个工具，工具结果喂回后第二轮生成最终回答。中间件的 `before_model` / `after_model` 因此在一次调用里触发两次，而 `before_agent` / `after_agent` 只在整个循环头尾各触发一次。
- 工具结果真实参与生成：最终回答会复用工具返回的措辞（实测最小示例里工具返回"永远晴天"，最终回答直接沿用了这个说法），这是"结果确实喂回了模型"的可验证证据。
- 循环步数随任务增长：一次退款咨询实测跑出 3 次模型调用、多次工具调用、7 条消息；一次多源调研在长程脚手架下触发约 50 多次图迭代。
- 循环步数没有内建上限，需要时用调用次数中间件或图的迭代上限参数来约束（见 builtin-middleware-catalog、deepagents-harness）。
- 实测一次最小示例的联网调用耗时约 5.6 秒。

## 常见陷阱

- **以为"模型会自己调工具"是理所当然**：这依赖所选型号支持工具调用，不支持的型号根本不会发出工具调用请求，循环走不通。
- **参数不全时以为模型会猜**：实测中问"订单从北京寄到上海运费多少"而未给重量，模型只查了订单、然后反过来追问重量，宁可追问也不编默认值。构造多工具任务时参数要给全。
- **把多轮模型调用误当成异常**：看到日志里模型被调了两次不是 bug，是循环的正常形态；调用次数限制设成 1 会直接把这条循环拦腰截断。
- **用传统日志排查失败**：一次请求里藏着 3 到 5 次模型决策，失败可能发生在任何一步，翻一条请求日志拼不出全貌——这正是可观测追踪要解决的问题。
