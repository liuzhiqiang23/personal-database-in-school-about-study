---
concept: checkpointer-backends
one_liner: 三档存储器构成「开发、本地持久、生产」的升级路径，接口完全一致，切换只改一个参数
stage_span: [stage-2]
prerequisites: [checkpointer-persistence]
related: [thread-id-isolation, local-environment-traps, virtual-filesystem-context-engineering]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#六、持久化升级：从 InMemorySaver 到 SqliteSaver
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、SqliteSaver：跨进程持久化
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、重启丢 vs 重启留：对比验证
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#3、checkpointer 三档差异
---

## 是什么

内存版存储器有一个绕不开的边界：它把状态存在**进程内存**里，进程一退出，所有会话的记忆全部消失。开发调试够用，但凡需要"重启后还记得"的场景就得换档。

三档存储器构成一条线性升级路径，接口完全一致、只是存储介质不同：

| 存储器 | 存储介质 | 重启后 | 额外安装 | 适用阶段 |
| --- | --- | --- | --- | --- |
| `InMemorySaver` | 进程内存 | 记忆全清 | 无（随图执行引擎自带） | 开发、调试、单元测试 |
| `SqliteSaver` | 本地 SQLite 文件 | 记忆保留 | `pip install langgraph-checkpoint-sqlite` | 本地持久、单机演示 |
| `PostgresSaver` | PostgreSQL 数据库 | 记忆保留 | `pip install langgraph-checkpoint-postgres` | 生产、多实例、高并发 |

设计要点是接口统一：三档之间切换，业务代码不变，只换一处参数。

## 怎么用

本地持久化档位（推荐用上下文管理器管理连接）：

```bash
pip install langgraph-checkpoint-sqlite
```

```python
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = "/tmp/langchain_checkpoint.db"          # 主盘路径

with SqliteSaver.from_conn_string(db_path) as checkpointer:
    agent = create_agent(model=..., tools=..., checkpointer=checkpointer)
    # ...对话、查询...
```

跨进程验证：阶段 1 建立含订单号的对话并落盘，阶段 2 用新实例重新打开同一个数据库文件再问：

```
=== 阶段 1: 用 SqliteSaver 建立对话 ===
[OK] checkpoint 已落盘，messages 数: 2
[OK] DB 文件大小: 20480 bytes (20.0 KB) — 确认落盘

=== 阶段 2: 重新打开 DB（模拟重启后恢复）===
用户: 我刚才说的订单号是多少？（新进程实例、重新打开 DB）
Agent: 您刚才说的订单号是 A1003。
```

## 关键细节与参数

- **迁移成本只有一个参数**：从内存版换到 SQLite 版，只改 `checkpointer=` 这一处，`invoke` / `get_state` / `get_state_history` 的调用代码一行不动。
- 内存版的"重启"= 新建一个实例，原有状态完全消失，实测重启后智能体回答"您没有提供订单号"；SQLite 版的"重启"= 重新用同一个数据库路径打开连接，实测无缝恢复。
- 落盘可用文件大小验证（实测 20480 字节、另一次 4096 字节）。
- 选型逻辑很直接：开发阶段图快用内存版；需要重启不丢用 SQLite 版；上生产、要支撑多实例和高并发就上 PostgreSQL 版。

## 常见陷阱

- **把数据库文件放在不支持 POSIX 文件锁的文件系统上**：ExFAT 格式的外置磁盘上 SQLite 的 WAL 模式会失败。数据库文件必须放在主盘（如 `/tmp/` 或用户主目录）。
- **以为 SQLite 档位随引擎自带**：它需要单独安装存储器包，漏装会在导入时失败。
- **在生产用内存版**：多实例部署时各实例内存互不可见，用户请求打到不同实例就等于失忆。
- **手工管理数据库连接**：推荐用上下文管理器，避免连接未正确关闭导致的落盘问题。
