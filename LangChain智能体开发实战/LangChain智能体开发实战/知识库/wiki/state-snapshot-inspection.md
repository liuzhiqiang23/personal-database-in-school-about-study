---
concept: state-snapshot-inspection
one_liner: get_state 打开存档看当前状态快照、get_state_history 看完整时间线，是调试记忆与定位暂停点的主要手段
stage_span: [stage-2]
prerequisites: [checkpointer-persistence, message-stream-anatomy]
related: [thread-id-isolation, time-travel-replay, human-in-the-loop-interrupt]
applications: [time-travel-replay, human-in-the-loop-interrupt]
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#四、打开 checkpoint 引擎盖：get_state 看快照
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、get_state 返回 StateSnapshot
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、get_state_history：看完整时间线
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、invoke 返回含 __interrupt__，而不是把异常抛给调用方
---

## 是什么

存档不是黑盒。图对象提供两个读取入口：`get_state(config)` 返回指定会话**当前**的一份状态快照，`get_state_history(config)` 返回从头到尾每一步的全部快照。它们是调试记忆问题、确认智能体停在哪一步的主要手段。

状态快照共 8 个字段：

| 字段 | 含义 |
| --- | --- |
| `values` | 当前对话状态，核心是完整的消息历史 |
| `next` | 下一步要执行的图节点，空元组表示已到终点 |
| `config` | 本快照的定位信息，含会话标识与快照唯一编号 |
| `metadata` | 元信息，含来源、第几个执行步等 |
| `created_at` | 快照创建时间 |
| `parent_config` | 上一个快照的定位信息，快照之间靠它串成链 |
| `tasks` | 待执行任务（人工审批场景会有值） |
| `interrupts` | 中断点（人工审批场景会有值） |

## 怎么用

看当前快照：

```python
snapshot = agent.get_state(config_u1)
print("StateSnapshot 字段:", list(snapshot._fields))
print("messages 总数:", len(snapshot.values["messages"]))
print("next =", snapshot.next)
```

看完整时间线：

```python
for h in agent.get_state_history(config):
    print(f"step={h.metadata['step']}  checkpoint_id={h.config['configurable']['checkpoint_id']}")
```

实测输出片段：

```
[OK] get_state 返回类型: <class 'langgraph.types.StateSnapshot'>
--- values (当前 State) ---   messages 总数: 8
--- next (下一步执行节点) ---  next = ()      ← 对话已结束，处于 END 节点
--- config (含 checkpoint_id) --- checkpoint_id = 1f15c0d0-a392-65ea-8008-926dc03d7383
--- metadata --- {'source': 'loop', 'step': 8, ..., 'ls_integration': 'langchain_create_agent'}
```

## 关键细节与参数

- **`next` 字段揭示停在哪一步**：`()` 表示对话处于终态；`('model',)` 表示停在等待模型；`('tools',)` 表示停在等待工具执行。人工审批暂停时，这个字段正是 `('tools',)`。这个字段在时间旅行里会变成一条硬约束。
- **`metadata.ls_integration` 的值是 `'langchain_create_agent'`**，坐实了一个底层事实：智能体工厂函数不是独立实现，底层就是图执行引擎——返回的编译图对象、检查点机制都是引擎的能力，工厂函数是引擎之上的一层便捷封装。
- **历史快照倒序返回**：第一个是最新快照，最后一个是初始空快照（步号 -1）。实测两轮对话共产生 10 个快照（步号 -1 到 8），三轮带工具调用的对话产生 13 个。
- **每个执行步对应一个快照编号**，是定位某一历史时刻的锚点。
- 展开消息可见四种类型：用户输入、模型回复（调工具时内容为空、携带工具调用字段）、工具返回、最终文字回复；一次工具调用在消息里占 3 条。

## 常见陷阱

- **以为存档存的是对话摘要**：它存的是完整消息列表，每条消息原样保留，体积随轮次线性增长。
- **按正序遍历历史快照**：历史是倒序返回的，取"第一轮结束时的快照"要从末尾方向找。
- **忽略 `next` 就去做重放或续跑**：状态不完整的进行中快照不能作为重放起点（见 time-travel-replay）。
