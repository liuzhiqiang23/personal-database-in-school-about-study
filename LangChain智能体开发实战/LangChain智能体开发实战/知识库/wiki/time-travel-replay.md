---
concept: time-travel-replay
one_liner: 把某个历史快照编号填进调用配置就能从那一刻重新出发，但只能从状态完整的稳态快照重放
stage_span: [stage-2]
prerequisites: [state-snapshot-inspection, checkpointer-persistence]
related: [thread-id-isolation, interrupt-resume-replay]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#3、时间旅行：从历史快照重放
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、get_state_history：看完整时间线
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#4、迁移前置知识假设清单
---

## 是什么

既然每个历史时刻都有一个快照编号，就能"回到过去"：把某个历史快照的编号填进调用配置，从那一刻重新出发继续对话。这就是时间旅行。

它的语义很干净：从历史点重放，智能体看到的只有那一刻之前的上下文。实测中从第一轮结束的快照出发追问"我的订单号是多少"，智能体答出了第一轮的订单号，却"不知道"第二轮才查的另一个订单——因为那时它还没发生。

## 怎么用

先从历史里筛出可用的起点，再把它的编号填进配置：

```python
# 从历史快照里挑一个「稳态」快照（next == ()）
stable = [h for h in agent.get_state_history(config) if h.next == ()]
target = stable[-1]                                   # 第一轮结束时的快照

replay_config = {
    "configurable": {
        "thread_id": "xxx",
        "checkpoint_id": target.config["configurable"]["checkpoint_id"],
    }
}
agent.invoke({"messages": [{"role": "user", "content": "我们聊了什么？我的订单号是多少？"}]}, replay_config)
```

## 关键细节与参数

- **重放起点必须是 `next == ()` 的稳态快照**——即对话已经走完整轮、停在终态的快照。这是实操踩出来的工程铁律。
- 实测里三轮带工具调用的对话共产生 13 个快照，其中稳态快照只有 3 个。
- 配置里同时需要会话标识与快照编号：标识定位是哪条会话，编号定位是哪一刻。
- 从稳态快照重放不影响该会话此前的其他存档，历史链仍然完整。

## 常见陷阱

- **从进行中的快照重放**：挑到 `next=('tools',)` 的快照时，它的最后一条模型消息带着工具调用、却还没有对应的工具返回消息，状态不完整。从这种快照重放会被模型接口直接拒绝，返回 400 错误 `An assistant message with tool_calls must be followed by tool messages`。
- **没做筛选就取历史第一个元素**：历史倒序返回，直接取首个元素拿到的是最新快照，未必是想回到的那一刻，也未必稳态。修复办法就是先按 `next == ()` 过滤。
- **把时间旅行当成撤销**：它是从历史点分叉继续，不是删除之后发生的事。
