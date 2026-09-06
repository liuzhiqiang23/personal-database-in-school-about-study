---
name: inspecting-checkpoint-state
description: 打开 LangChain Agent 的会话存档，用 get_state 与 get_state_history 看清某一会话当前存了什么、每一步产生了哪些快照，并从指定历史快照重放继续对话。Use when 需要调试「Agent 记住了什么 / 为什么答错」、审计一次会话的完整消息与执行位置、做时间旅行重放对比、或排查「从历史点重放报 400 an assistant message with tool_calls must be followed by tool messages」时。涵盖状态快照字段解读、消息历史展开、快照时间线、稳态快照筛选与重放；不含如何给 Agent 加记忆（见 persisting-agent-memory）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、get_state 返回 StateSnapshot
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、get_state_history：看完整时间线
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#3、时间旅行：从历史快照重放
---

## 能力目标

把一个已挂存档器的 Agent 的会话状态原样打开：读出当前快照里的全部消息与执行位置、列出从头到尾每一步的快照时间线、并能挑一个历史时刻重新出发继续对话，用于调试记忆问题、审计会话、对比不同分支的回答。

## 前置

- Agent 必须已挂存档器并带会话标识调用过（见 persisting-agent-memory）；没有存档就没有快照可查。
- 查询入口是 agent 对象上的 `get_state(config)` 与 `get_state_history(config)`，`config` 与调用时用的是同一个。

## 实操流程

1. 取当前快照并打印全部字段：

   ```python
   # step4_get_state.py
   config = {"configurable": {"thread_id": "u1"}}
   snapshot = agent.get_state(config)

   print("字段:", list(snapshot._fields))
   print("messages 总数:", len(snapshot.values["messages"]))
   print("next =", snapshot.next)
   print("checkpoint_id =", snapshot.config["configurable"]["checkpoint_id"])
   print("metadata =", snapshot.metadata)
   ```

   ```bash
   python step4_get_state.py
   ```

   快照共 8 个字段，按用途读：

   | 字段 | 含义 |
   | --- | --- |
   | `values` | 当前对话状态，核心是 `values["messages"]` 完整消息历史 |
   | `next` | 下一步要执行的图节点。`()` 表示已到终点 |
   | `config` | 本快照的定位信息，含会话标识与快照唯一编号 |
   | `metadata` | 元信息，含 `source`、`step`（第几个执行推进单位） |
   | `created_at` | 快照创建时间 |
   | `parent_config` | 上一个快照的定位信息，快照靠它串成链 |
   | `tasks` | 待执行任务（人工审批场景才有值） |
   | `interrupts` | 中断点（人工审批场景才有值） |

   `next` 是判断 Agent 停在哪一步的关键：`()` 已出最终回答、`('model',)` 等待模型、`('tools',)` 等待工具执行。

2. 展开消息历史逐条看类型，定位「模型在哪一步做了什么」：

   ```python
   for i, m in enumerate(snapshot.values["messages"]):
       print(f"[{i:02d}] type={type(m).__name__}",
             getattr(m, "tool_calls", None), (m.content or "")[:40])
   ```

   存的是完整消息列表而不是对话摘要：模型调工具时的请求藏在 `tool_calls` 字段里、工具返回是单独一条工具消息。一次工具调用在历史里占三条（模型请求、工具结果、模型作答）。

3. 看完整时间线，每个执行推进单位对应一个快照：

   ```python
   for h in agent.get_state_history(config):
       print(f"step={h.metadata['step']}  next={h.next}  "
             f"checkpoint_id={h.config['configurable']['checkpoint_id']}")
   ```

   历史**倒序返回**：第一条是最新快照，最后一条是 `step=-1` 的初始空快照。两轮带工具调用的对话约产生 10 个快照。

4. 从历史点重放。**只能从 `next == ()` 的稳态快照出发**，先 filter 再把它的快照编号填进 config：

   ```python
   # ext4_time_travel.py
   stable = [h for h in agent.get_state_history(config) if h.next == ()]
   target = stable[-1]          # 最早的那个稳态快照，即第一轮结束时

   replay_config = {
       "configurable": {
           "thread_id": "u1",
           "checkpoint_id": target.config["configurable"]["checkpoint_id"],
       }
   }
   agent.invoke({"messages": [{"role": "user", "content": "我们聊了什么？我的订单号是多少？"}]},
                replay_config)
   ```

   从历史点重放看到的只有那一刻之前的上下文——它会记得第一轮的信息，对第二轮之后发生的事一无所知。这正是时间旅行的语义，可用来对比「如果那一步换个问法会怎样」。

## 校验回路

- `get_state` 返回的 `values["messages"]` 条数与你实际跑过的轮数吻合（每轮无工具调用记 2 条，每次工具调用额外 +2）。
- `next` 在对话跑完后是 `()`；若不是，说明 Agent 停在半途（等待工具或等待审批），据此定位卡点。
- `get_state_history` 打印出连续的 `step` 序列，最末一条是 `step=-1`。
- 重放调用不报错、且回答内容只覆盖目标快照之前的上下文。

## 常见陷阱

- **从进行中的快照重放**：`next=('tools',)` 的快照停在循环半中间——最后一条模型消息带着工具调用请求、却还没有对应的工具结果。从这种快照重放，模型接口会直接返回 400 `An assistant message with tool_calls must be followed by tool messages`。修复办法就是那行 filter：只取 `next == ()` 的稳态快照。
- **把历史当正序读**：历史是倒序返回的，`history[0]` 是最新、`history[-1]` 是初始空快照。按正序假设取「第一轮」会取错快照。
- **拿不带会话标识的 config 去查**：查询用的 `config` 必须与调用时的会话标识一致，否则查到的是另一个会话或空状态。
- **误以为存的是摘要**：存的是全量消息，长会话的存档会随轮数线性增长，做审计时按需截取而不是全量打印。
