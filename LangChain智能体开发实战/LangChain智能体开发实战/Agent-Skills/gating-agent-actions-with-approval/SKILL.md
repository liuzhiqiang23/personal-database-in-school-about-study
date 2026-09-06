---
name: gating-agent-actions-with-approval
description: 给 LangChain Agent 的不可逆动作加一道人工审批闸门：工具执行前暂停、把审批信息抛给人、批准才继续、拒绝就不执行。Use when 需要让 Agent 在退款、转账、删数据、发邮件这类高危操作前等人点头，或排查「暂停没触发」「审批被绕过」「续跑时副作用重复发生」「续跑报 TypeError string indices must be integers」这类问题时。涵盖危险工具改造、暂停信号判定、批准与拒绝两条续跑路径、节点重执行行为、四条工具编写纪律；不含存档器本身的用法（见 persisting-agent-memory）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、定义 mock 危险工具 refund_order（在工具内调 interrupt）
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、invoke 返回含 __interrupt__，而不是把异常抛给调用方
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、两种实现路线：手写 interrupt 与 HumanInTheLoopMiddleware
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、打印审批横幅与详情
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、批准续跑，退款执行
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、最反直觉的行为：resume 时节点从头重执行
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、拒绝续跑
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#七、四铁律：写人在回路工具不能踩的坑
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、铁律反例：interrupt 被 try/except 吞掉，审批彻底失效
---

## 能力目标

把任意一个不可逆的业务动作改造成「先暂停、抛出审批信息、等人工决定、再决定执行与否」的闸门式工具：批准时动作照常执行，拒绝时动作根本不发生，且暂停期间的执行状态被完整存档、可跨请求恢复。

## 前置

- 暂停与续跑靠三件套：`interrupt`（在工具内调用，让执行暂停并抛出待审批信息）、`Command(resume=...)`（把人工决定回传、从断点续跑）、存档器（暂停期间保存执行状态）。前两者都在 `langgraph.types` 下，随编排运行时一并安装。
- **存档器是硬前提**：没有 checkpointer，暂停无法成立（见 persisting-agent-memory）。
- `interrupt` 是一个普通函数对象，不是异常类，写工具时按函数调用即可。

## 实操流程

1. 改造危险工具：在真正执行动作**之前**调一次 `interrupt`，参数是一个自定义 dict——审批界面要展示什么就往里塞什么：

   ```python
   from langgraph.types import interrupt
   from langchain.tools import tool

   @tool
   def refund_order(order_id: str, amount: float) -> str:
       """给指定订单退款。order_id 为订单号，amount 为退款金额（元）。"""
       approval = interrupt({
           "action": "refund_order",
           "order_id": order_id,
           "amount": amount,
       })
       if approval == "approve":
           return f"退款已执行：{order_id} ¥{amount} 成功"
       return f"退款已拒绝：{order_id} ¥{amount} 被驳回"
   ```

   `interrupt()` 的返回值就是人工后续回传的值，工具内用它决定走哪条分支。真正的动作逻辑必须写在这行之后。

2. 组装带存档器的 Agent，并把系统提示词写死到位——明确要求「用户要求退款时立即调用退款工具，不需要先查询」，否则模型可能先绕去查订单、迟迟不触发闸门：

   ```python
   from langgraph.checkpoint.memory import InMemorySaver
   agent = create_agent(model="deepseek:deepseek-chat", tools=[refund_order],
                        system_prompt="用户要求退款时必须立即调用 refund_order，不需要先查询。",
                        checkpointer=InMemorySaver())
   ```

3. 发起会触发危险动作的请求，用户消息也要用明确措辞（「立即退款」而非「帮我看看退款」）：

   ```python
   # step2_invoke_interrupt.py
   result = agent.invoke(
       {"messages": [{"role": "user", "content": "立即给订单 A1001 退款 299 元"}]},
       config={"configurable": {"thread_id": "refund-001"}},
   )
   print("__interrupt__" in result, result.get("__interrupt__"))
   print("next =", agent.get_state({"configurable": {"thread_id": "refund-001"}}).next)
   ```

   ```bash
   python step2_invoke_interrupt.py
   ```

   调用本身**正常返回**、不会把异常抛到调用方。判断是否停在审批点就看返回 dict 里有没有 `__interrupt__` 键；状态查询会显示 `next = ('tools',)`。

4. 把待审批信息取出来推给人。两个视角互补：`result['__interrupt__'][0].value` 是工具抛出的精炼审批字段（也可从状态的 `tasks[0].interrupts` 拿，内容一致）；模型消息里的 `tool_calls` 则保留了它这一轮完整的决策链，可用于追溯它为什么要这么做。

5. 人工批准后用同一个会话标识续跑：

   ```python
   # step5_resume_approve.py
   from langgraph.types import Command

   result = agent.invoke(Command(resume="approve"),
                         config={"configurable": {"thread_id": "refund-001"}})
   ```

   拒绝路径唯一的差别就是这个值：

   ```python
   agent.invoke(Command(resume="reject"), config={"configurable": {"thread_id": "refund-002"}})
   ```

   传回的值原样成为工具内 `interrupt()` 的返回值，工具的 `if` 据此分叉。它不限于两个字符串——可以是带审批意见的对象、条件参数，全看工具怎么消费。

6. 按四条纪律复核你的工具代码，缺一条审批都可能在无察觉的情况下失效：

   1. `interrupt` 绝不包进 `try/except`——它靠抛异常暂停，宽泛捕获会把信号吞掉。
   2. 不用外层 `if` 条件跳过 `interrupt`。要做条件审批，把阈值判断作为审批信息的一个字段抛出去（如 `"needs_review": amount > 10000`），或在返回值上判断，而不是跳过调用。
   3. 副作用幂等——`interrupt` 之前的代码在续跑时会重跑一遍。
   4. 只抛可序列化的简单结构（dict、字符串、数字），不要抛数据库连接、文件句柄。

## 校验回路

1. **触发暂停**：发起一个会调用危险工具的请求，返回 dict 里**有** `__interrupt__` 键、状态的 `next` 不为空。
2. **批准路径**：`Command(resume="approve")` 续跑后，工具消息显示动作已执行、状态 `next == ()`。
3. **拒绝路径**：换一个会话标识重跑，`Command(resume="reject")` 续跑后确认动作**没有**执行。

两条路径都跑通才算闭环。想更彻底，在 `interrupt` 前后各加一行打印跑一次——正常现象是前面那行打印两次、后面那行打印一次。

## 常见陷阱

- **把 `interrupt` 包进 `try/except Exception`**：暂停信号是一个 `GraphInterrupt` 异常，宽泛捕获会把它吞掉，`__interrupt__` 根本不出现，Agent 误以为工具正常完成、按默认分支把危险动作执行了——审批形同虚设。工具内确需异常处理时只捕获精确类型（如 `except ValueError`）。
- **在 `interrupt` 之前写副作用**：续跑时暂停所在的节点**从第一行重新执行**，此前写库、扣款、发邮件会再发生一遍。所有不可重复的动作一律放到 `interrupt` 之后。工具执行计数在续跑后是 2 不是 1，属正常现象，与批准还是拒绝无关。
- **两条实现路线的续跑格式混用**：自己在工具里调 `interrupt` 时，续跑传普通值 `Command(resume="approve")`；改用声明式审批中间件时，续跑必须传 dict `Command(resume={"decisions": [{"type": "approve"}]})`，误传字符串会报 `TypeError: string indices must be integers`。两条路线二选一，不要混。
- **续跑时换了会话标识**：续跑必须与暂停时用同一个 `thread_id`，否则找不回断点存档。
- **提示词与用户措辞含糊导致闸门不触发**：模型可能先调查询类工具兜圈子。系统提示词写明「立即调用」，用户消息用明确动作措辞。
