---
concept: invoke-vs-stream
one_liner: invoke 跑完整个循环一次性返回完整消息列表，stream 按循环步数逐块吐出增量，二者是同一循环的两种颗粒度
stage_span: [stage-1, stage-2]
prerequisites: [create-agent-entry, tool-calling-loop]
related: [message-stream-anatomy, todo-planning-mechanism]
applications: [todo-planning-mechanism, virtual-filesystem-context-engineering]
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、invoke vs stream：让循环肉眼可见
  - experiments/langchain/stage-1-bootstrap/handbook.md#五、本节小结与后续方向
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、给长程任务挂上待办清单
---

## 是什么

编译出的图对象自带两种调用方式。`invoke` 是一次性执行：跑完整个循环后返回一个字典，`result["messages"]` 是完整消息列表。`stream` 是流式执行：返回一个生成器，循环每推进一步就吐出一个 chunk，chunk 里只含当前步骤的增量消息。

两者不是不同的能力，而是同一条循环的两种观察颗粒度：stream 的 chunk 数等于循环步数，与 invoke 的消息条数一一对应。

## 怎么用

一次性拿最终结果：

```python
result = agent.invoke({"messages": [{"role": "user", "content": "订单 A1001 是什么状态？"}]})
print(result["messages"][-1].content)
```

逐步观察循环推进：

```python
for chunk in agent.stream({"messages": [{"role": "user", "content": "..."}]}):
    print(chunk)
```

实测对比输出：

```
方式 A: invoke
返回类型: <class 'dict'>
消息条数: 4

方式 B: stream
─ 流式 chunk #1 ─   节点: model    [AIMessage] → tool_calls: ['query_order']
─ 流式 chunk #2 ─   节点: tools    [ToolMessage] → 已发货
─ 流式 chunk #3 ─   节点: model    [AIMessage] → 订单 A1001 当前状态为已发货，预计明天到达。
流式 chunk 总数: 3
```

流式调用还是读取图内部状态的入口，长程任务里可以直接从 chunk 里取出规划清单：

```python
for chunk in agent.stream({"messages": [...]}, config={"recursion_limit": 100}):
    if "todos" in chunk:
        print(chunk["todos"])
```

## 关键细节与参数

- **返回类型不同**：`invoke` 返回 dict，`stream` 返回生成器。
- **chunk 数 = 循环步数**：3 个 chunk 对应 model（决策加调工具）→ tools（执行）→ model（最终回答），与 invoke 的 4 条消息颗粒度不同但内容对应。
- **节点名是 `model` 和 `tools`，不是 `agent`**：这一点在 v1 中是确定的，参考旧版资料时以 `model` 为准。
- 适用场景：`invoke` 适合直接拿最终答案的单轮问答；`stream` 适合需要实时反馈的场景——长任务进度可视化，或让循环"一步步走"给人看。生产环境中 `stream` 通常带来更好的体验：实时响应而非等待数秒后突然出结果。
- 两种方式在挂上检查点存储器、结构化输出、中间件之后都照常可用，调用形态不变。

## 常见陷阱

- **想读图的内部状态却用了 `invoke`**：规划清单这类中间状态要靠流式调用从 chunk 里实时读取，一次性调用只能看到终态。
- **解析流式事件时用了错误的节点名**：按旧版资料写 `agent` 节点名会取不到数据。
- **长程任务流式跑时忘了放宽图迭代上限**：步数多的任务会撞上默认迭代上限并抛错，需显式设置（见 deepagents-harness）。
