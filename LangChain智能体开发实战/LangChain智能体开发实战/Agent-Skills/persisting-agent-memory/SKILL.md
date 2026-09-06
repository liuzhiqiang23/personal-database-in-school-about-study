---
name: persisting-agent-memory
description: 给 LangChain Agent 挂上 checkpointer 与 thread_id，让它在同一会话里记住前文、不同用户之间互不串台，并按需从内存存档升级到重启不丢的持久化存档。Use when 需要把一问一答的 Agent 变成多轮连续对话、做多用户会话隔离、让记忆在进程重启后仍在、或排查「Agent 忘了上一句」「两个用户记忆串台」「SQLite 存档报文件锁错误」这类问题时。涵盖 checkpointer 挂载、thread_id 会话隔离、三档存储选型与迁移、跨进程持久化验证；不含查看存档内部与历史重放（见 inspecting-checkpoint-state）。
allowed-tools: Bash(python:*), Bash(pip:*)
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、给 create_agent 传 checkpointer=InMemorySaver()
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、第一轮：告知订单号 A1001
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、第二轮：不重提订单号，验证 Agent 记住 A1001
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、换 thread_id=u2，验证不记得 A1001
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、交叉提问验证不串台
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、SqliteSaver：跨进程持久化
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#3、checkpointer 三档差异
---

## 能力目标

用一个参数把无状态的 Agent 变成有记忆的连续会话体：同一会话里用户不必重复交代关键信息，不同会话之间记忆完全隔离，且能按部署阶段在内存存档、本地文件存档、数据库存档三档之间切换而业务代码不变。

## 前置

- 已能用 `create_agent` 组装 Agent（见 building-tool-calling-agent）。
- 记忆不是模型「记住」的：模型本身无状态，是存档器把历史存下来、每轮调用前自动回填给模型。存档器有两件套——checkpointer（存档本体）与 `thread_id`（这是谁的存档）。
- 开发档的 `InMemorySaver` 随编排运行时一并装好，无需额外装包。

## 实操流程

1. 实例化存档器并挂到 `create_agent`，其余组装方式一行不改：

   ```python
   # step1_checkpointer_agent.py
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
   print("agent.checkpointer:", type(agent.checkpointer).__name__)
   ```

   返回类型仍是 `CompiledStateGraph`，`invoke` / `stream` 照常可用——记忆是叠加上去的能力，不是另一套 API。

2. 调用时用第二个参数 `config` 传会话标识，这才是真正打开记忆的开关：

   ```python
   # step2_multi_turn.py
   config_u1 = {"configurable": {"thread_id": "u1"}}

   agent.invoke({"messages": [{"role": "user",
                 "content": "你好，我的订单号是 A1001，请帮我记住。"}]}, config_u1)
   r2 = agent.invoke({"messages": [{"role": "user",
                 "content": "我刚才说的订单号是什么？"}]}, config_u1)
   print(r2["messages"][-1].content)
   ```

   ```bash
   python step2_multi_turn.py
   ```

   第二轮输入里没有订单号，Agent 仍答得出——历史被自动读回、拼在这一轮新消息前面交给模型。第三轮再用指代（「这个订单」）提问，它会先从历史认出指代对象、再自主调用工具去查，记忆与工具调用循环叠加生效。

3. 多用户隔离：同一个 agent 实例，换 `thread_id` 即换独立记忆空间，不需要为每个用户建一个 agent：

   ```python
   # step5_isolation.py
   config_u2 = {"configurable": {"thread_id": "u2"}}
   r = agent.invoke({"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]}, config_u2)
   print(r["messages"][-1].content)     # 应回答「您还没有提供订单号」
   ```

   生产里直接把用户标识当会话标识：`thread_id = str(user.id)`，也可以用邮箱或会话令牌，任意字符串都行，只要同一会话固定、不同会话互异。

4. 需要重启不丢时升级到文件存档。它要单独装包，并用上下文管理器管理连接：

   ```bash
   pip install langgraph-checkpoint-sqlite
   ```

   ```python
   # step6_sqlite_saver.py
   from langgraph.checkpoint.sqlite import SqliteSaver

   db_path = "/tmp/langchain_checkpoint.db"
   with SqliteSaver.from_conn_string(db_path) as checkpointer:
       agent = create_agent(model="deepseek:deepseek-chat", tools=[...], checkpointer=checkpointer)
       agent.invoke({"messages": [{"role": "user", "content": "我是李四，我的订单是 A1003。"}]},
                    {"configurable": {"thread_id": "u1"}})
   ```

   迁移成本只有 `checkpointer=` 这一处，`invoke` 与状态查询代码一行不动。

5. 按部署阶段选档，接口完全一致、只是存储介质不同：

   | 存档器 | 存储介质 | 重启后 | 额外安装 | 适用阶段 |
   | --- | --- | --- | --- | --- |
   | `InMemorySaver` | 进程内存 | 记忆全清 | 无 | 开发、调试、单元测试 |
   | `SqliteSaver` | 本地 SQLite 文件 | 记忆保留 | `pip install langgraph-checkpoint-sqlite` | 本地持久、单机演示 |
   | `PostgresSaver` | PostgreSQL 数据库 | 记忆保留 | `pip install langgraph-checkpoint-postgres` | 生产、多实例、高并发 |

## 校验回路

1. **多轮记忆**：同一 `thread_id` 下连跑至少三轮，第二轮起故意不重提关键信息（订单号、病历号、航班号），确认 Agent 仍能答出。
2. **会话隔离**：开两个不同 `thread_id` 各存不同信息后交叉提问，确认各答各的、互不知道对方的信息。
3. **跨进程持久化**（用文件存档时）：第一阶段写入并确认 DB 文件字节数增长，第二阶段新建 agent 实例、重新打开同一个 DB 路径再提问，确认仍答得出第一阶段的信息。

## 常见陷阱

- **挂了存档器却仍然「忘事」**：多半是调用时没传 `config`，或两次调用的 `thread_id` 不是同一个。记忆的开关是 `config` 里的会话标识，不是存档器本身。
- **把 SQLite 存档文件放在 ExFAT 外置磁盘上**：ExFAT 不支持 POSIX 文件锁，SQLite 的 WAL 模式会失败。DB 文件放主盘路径（如 `/tmp/` 或家目录）。
- **拿内存存档当持久化**：它把状态存在进程内存里，进程一退全部消失。需要重启后还记得就换文件存档；上生产、要多实例与高并发再换数据库存档。
- **给每个用户建一个 agent 实例**：不必要。一个 agent 实例配不同会话标识就承载无限会话，存档器内部按标识分隔命名空间。
