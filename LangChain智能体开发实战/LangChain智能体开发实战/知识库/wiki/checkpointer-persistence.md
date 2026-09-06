---
concept: checkpointer-persistence
one_liner: 模型本身无状态，多轮记忆来自检查点存储器——它在每个执行边界存档，下一轮调用前把历史自动回填给模型
stage_span: [stage-2]
prerequisites: [create-agent-entry, tool-calling-loop]
related: [thread-id-isolation, state-snapshot-inspection, checkpointer-backends]
applications: [thread-id-isolation, state-snapshot-inspection, time-travel-replay, checkpointer-backends, human-in-the-loop-interrupt]
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#一、开篇：从「一问一答的健忘」到「有记忆的连续会话」
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、给 create_agent 传 checkpointer=InMemorySaver()
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、第二轮：不重提订单号，验证 Agent 记住 A1001
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、确认环境与 interrupt / Command 就位
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、选一个「值得被观测」的 Agent 作为对象
---

## 是什么

默认组装出的智能体是**无状态**的：每次调用都是独立的一问一答，模型不记得上一轮说过什么。用户第一句报了订单号、第二句问"我刚说的订单号是什么"，无状态的智能体只能回答"您还没有告诉我"——它不是答错，而是根本没有"上一句"的概念。

检查点存储器（checkpointer）就是那个"记事本"：智能体每走完一步，就把当前的完整对话状态存一份档；下一次调用时，框架自动把存档读回来、拼在这一轮的新消息前面，再一起交给模型。

一句话概括机制：**记忆不是模型"记住"的，是检查点存储器把历史存下来、每轮调用前自动回填给模型的**。模型本身依然无状态，有状态的是这个外部存储。它同时也是人工审批机制的硬前提——没有它，中断无法暂停。

## 怎么用

组装时多传一个参数即可：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import query_order, track_shipping, calc_shipping_fee

checkpointer = InMemorySaver()

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
    checkpointer=checkpointer,
)
print("agent.checkpointer:", type(agent.checkpointer).__name__)   # InMemorySaver
```

真正触发记忆的开关是调用时传的会话标识：

```python
config_u1 = {"configurable": {"thread_id": "u1"}}

agent.invoke({"messages": [{"role": "user", "content": "我的订单号是 A1001，请帮我记住。"}]}, config_u1)
agent.invoke({"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]}, config_u1)
# → 答出 A1001，而这一轮输入里根本没有这个订单号
```

## 关键细节与参数

- **存档发生在每个 super-step 边界**：图执行被拆成若干推进单位，每走完一个就存一份含全部消息的完整档。
- **加了检查点存储器后返回类型仍是 `CompiledStateGraph`**，与不加时完全一致——记忆是叠加上去的能力，不是另起一套 API；挂上去的实例可通过 `agent.checkpointer` 直接访问。
- 内存版存储器随图执行引擎一并安装，导入路径 `langgraph.checkpoint.memory`，无需额外装包。
- **记忆与工具调用循环叠加生效**：实测第三轮用户说"帮我查一下这个订单的状态"（未点名订单号），智能体先从历史里认出指代、再自主调用查询工具，三轮跑完存档累积 8 条消息。
- 存的是完整消息列表而非对话摘要，模型调工具的决策与工具返回结果原样保留。

## 常见陷阱

- **只挂了存储器却没传会话标识**：光挂存储器不够，`invoke` 的第二个参数必须带会话标识，否则记忆不会被触发。
- **两次调用传了不同的会话标识**：智能体"忘了"前文时，先查这两点——是不是漏传了存储器，或两次调用的会话标识不是同一个。
- **默认模型自己会记住上一句**：模型无状态是这套机制的前提；把记忆归因于模型会导致排查方向完全走偏。
- **忘记内存版存储器的边界**：它把状态存在进程内存里，进程退出即全部消失，需要重启不丢时必须换档（见 checkpointer-backends）。
