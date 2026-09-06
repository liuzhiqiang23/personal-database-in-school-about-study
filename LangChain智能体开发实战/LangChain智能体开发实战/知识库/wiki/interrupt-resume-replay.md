---
concept: interrupt-resume-replay
one_liner: 续跑时暂停所在的节点会从第一行重新执行一遍，中断之前的副作用会再发生一次
stage_span: [stage-2]
prerequisites: [human-in-the-loop-interrupt]
related: [hitl-iron-rules, time-travel-replay]
applications: [hitl-iron-rules]
sources:
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、最反直觉的行为：resume 时节点从头重执行
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、拒绝续跑
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#4、迁移前置知识假设清单
---

## 是什么

这是整套审批机制里最反直觉、也最容易造成生产事故的行为：**续跑时，暂停所在的节点会从头重新执行一遍**。

可以把中断理解成一个"时间切割点"：第一次执行到它，节点暂停并把状态存档；续跑时，节点**从第一行重新跑起**，但这一次中断不再真正暂停，而是直接返回续跑传入的值，于是执行流才越过切割点继续往下。

这不是 bug，而是图执行引擎续跑机制的核心行为，也是"副作用必须幂等"这条纪律的根本原因。

## 怎么用

在中断调用的前后各插一行标记，用一份全局执行日志把它看清楚：

```python
@tool
def refund_order(order_id: str, amount: float) -> str:
    log.append("START")            # interrupt 之前
    print("BEFORE interrupt")
    approval = interrupt({...})     # 时间切割点
    print("AFTER interrupt")       # interrupt 之后
    log.append("AFTER_INTERRUPT")
    ...
```

实测结果：

- 第一次调用：`BEFORE interrupt` 打印 1 次，日志只有 `[1] START`——节点跑到中断就停住了，中断之后的行没机会执行。
- 第二次调用（传续跑指令）：`BEFORE interrupt` **又打印一次**，日志新增 `[2] START`，然后才是 `[3] AFTER_INTERRUPT`。

最终 `START` 出现 2 次、`AFTER_INTERRUPT` 只出现 1 次。批准路径下工具执行计数是 2 而不是 1。

## 关键细节与参数

- **中断之前的代码在续跑时会被重新执行一遍**；中断之后的代码只有续跑那一次才跑得到。
- **重执行与审批结果无关**：拒绝路径的执行计数同样是 2，与批准路径完全对称——重执行是续跑机制本身的行为。
- 由此得到一条铁的工程纪律：**中断之前绝不能有不可重复的副作用**。若在中断之前写了数据库、扣了款、发了邮件，续跑时这些副作用会再发生一遍。
- 与之配套的写法要求是：真正的业务动作（扣款、删表、发信）必须放在中断**之后**的分支里。

## 常见陷阱

- **在中断之前记账或写库**：这是最典型的重复副作用来源，且第一次跑通测试时完全看不出来——只有真正走过一次审批续跑才会暴露。
- **把执行计数为 2 当成框架 bug 去排查**：它是预期行为，正确的应对是让副作用幂等，而不是想办法阻止重执行。
- **迁移旧工具时直接加一行中断**：迁移前必须逐行检查工具内已有的动作在中断之前还是之后，需要时调整语句顺序。
