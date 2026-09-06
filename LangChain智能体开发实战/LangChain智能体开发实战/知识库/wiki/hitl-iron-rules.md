---
concept: hitl-iron-rules
one_liner: 写审批工具有四条不能违反的纪律，其中把中断包进宽泛异常捕获会让审批被静默绕过、危险动作照常执行
stage_span: [stage-2]
prerequisites: [human-in-the-loop-interrupt, interrupt-resume-replay]
related: [middleware-flow-control, hitl-implementation-routes]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#七、四铁律：写人在回路工具不能踩的坑
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、铁律反例：interrupt 被 try/except 吞掉，审批彻底失效
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#3、迁移后如何验证跑通（含验收任务）
---

## 是什么

审批机制本身不复杂，但有四条纪律一旦违反，审批会在毫不知情的情况下失效——危险动作照常执行，而日志上看不出任何异常。官方把它们归纳为四条：

1. **中断绝不包进宽泛的异常捕获**——中断靠抛异常暂停，宽泛的捕获会把这个异常吞掉，审批被直接绕过。
2. **不条件跳过中断**——不要在中断之外用条件判断决定"这次要不要审批"。需要条件审批时，条件应体现在审批信息里或在中断返回后判断，而不是用外层条件把中断整个跳过。
3. **副作用幂等**——中断之前的代码续跑时会重跑一遍，任何副作用都必须能安全地重复执行。
4. **不序列化复杂对象**——中断抛出的数据会被存进检查点，应传可序列化的简单结构（字典、字符串、数字），不要传数据库连接、文件句柄这类对象。

第一条最隐蔽，也最值得用反例演示。

## 怎么用

错误写法与正确写法的对照：

```python
# 错误版（违反第一条）
@tool
def refund_order_BAD(order_id: str, amount: float) -> str:
    try:
        approval = interrupt({"order_id": order_id, "amount": amount})
    except Exception:
        approval = "approve"   # 异常被吞，等于默认批准——危险
    ...

# 正确版
@tool
def refund_order_GOOD(order_id: str, amount: float) -> str:
    approval = interrupt({"order_id": order_id, "amount": amount})  # 直接调，不包捕获
    ...
```

条件审批的正确写法（阈值进审批信息，不跳过中断）：

```python
@tool
def transfer_funds(to_account: str, amount: float) -> str:
    """转账。金额超过 10000 标记为高风险，需重点审批。"""
    approval = interrupt({
        "action": "transfer_funds",
        "to_account": to_account,
        "amount": amount,
        "needs_review": amount > 10000,   # 阈值判断放进审批信息
    })
    if approval == "approve":
        return f"转账已执行：{to_account} ¥{amount}"
    return f"转账被驳回：{to_account}"
```

## 关键细节与参数

- **中断的底层真相**：它靠抛出名为 `GraphInterrupt` 的异常传递暂停信号（实测确认）。宽泛捕获会顺带把它吞掉。
- 反例实测结果：错误版里被捕获的异常类型显示为 `GraphInterrupt`，`__interrupt__` 是否出现 = `False`，图根本没暂停、直接按默认批准把退款执行了；正确版 `__interrupt__` 出现 = `True`，正常暂停等待人工。
- **确需异常处理时用精确的异常类型**（如只捕获值错误），绝不用裸的宽泛捕获。
- 条件跳过之所以危险：被跳过的那次动作根本不存档，机制在低风险路径上等于不存在。
- 三步自查闭环：触发暂停（返回字典有中断键、快照的下一步不为空）→ 批准路径（动作执行、快照回到终态）→ 换会话标识跑拒绝路径（动作**没有**执行）。两条路径都跑通才算闭环。

## 常见陷阱

- **在工具里习惯性写宽泛的异常捕获**：这是最常见也最危险的违反，后果是审批形同虚设而系统表现完全正常。
- **用外层条件"优化"低风险动作的审批**：低风险动作因此不进存档，条件一旦判断失误就没有任何兜底。
- **往审批信息里塞连接对象**：存档时序列化失败，暂停链路直接断掉。
- **只验证批准路径**：拒绝路径必须单独验证，且要换一个会话标识重跑，确认危险动作确实没有执行。
