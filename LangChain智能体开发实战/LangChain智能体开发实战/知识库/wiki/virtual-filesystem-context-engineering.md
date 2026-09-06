---
concept: virtual-filesystem-context-engineering
one_liner: 给智能体一块可读写的暂存区，中间结果写进文件而不是堆在对话里，是最直接的一种上下文工程手段
stage_span: [stage-2]
prerequisites: [deepagents-harness]
related: [subagent-delegation, todo-planning-mechanism, checkpointer-backends]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#六、虚拟文件系统：用 write_file / read_file / ls 做上下文工程
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、把中间结果写进虚拟文件而非堆在对话里
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、把三大机制的内部状态一次看清
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、保持不变的部分（机制骨架）
---

## 是什么

第三道墙是"中间结果无处暂存"。解法是给智能体配一套虚拟文件系统：写文件、读文件、列目录，还有编辑、通配匹配、内容搜索等更细的操作。智能体可以把每一步的中间结果写成文件存起来，需要时再读回来，而不是让所有数据一直挂在对话上下文里。

这是**上下文工程**最直接的一种手段：主动决定什么留在上下文、什么挪到外部暂存。它与委派机制一起，构成对抗上下文膨胀的两条路径——委派是把处理过程隔离出去，虚拟文件系统是把处理结果挪出去。

## 怎么用

工具由脚手架自动注入，用任务驱动智能体自主使用即可：

```python
task = "请分别调研新能源汽车市场、动力电池竞争格局、电池技术路线趋势三个话题，每个话题的调研结果分别写入一个 markdown 文件，最后列出目录并读取其中一个文件验证。"
```

实测智能体自主完成了一整套操作：写文件 3 次（三个话题各写一个文件）、列目录 1 次（确认文件都在）、读文件 1 次（读回验证内容），合计文件操作 5 次。整个过程由智能体自己决定何时写、写什么、何时读——开发者只给了任务，没有手写任何文件调度逻辑。

## 关键细节与参数

- 工具集：`write_file` / `read_file` / `ls`，以及 `edit_file` / `glob` / `grep`。
- **默认后端下虚拟文件随线程消亡而消失**：这次运行写的文件换个会话就没了，适合"单次任务内暂存"。需要跨会话持久保存要换成存储型后端。
- 综合运行实测：写文件 2 次、读文件 2 次、列目录 1 次，文件操作合计 5 次，与规划、委派两个机制在同一次运行里协同工作。
- 委派与文件系统常配合使用：委派时把要读的文件路径写进任务描述，子智能体拿到就能干，无需回调主智能体。
- 验收判据：确认智能体用写文件存了中间结果、用列目录或读文件能取回（文件操作次数 ≥1）。

## 常见陷阱

- **指望默认后端跨会话保留文件**：默认是随线程消亡的暂存区，把它当持久存储会静默丢数据。
- **手写文件调度逻辑**：智能体会自主决定读写时机，开发者需要做的只是在任务描述里说清"结果分别写入文件"。
- **把它与检查点存档混为一谈**：检查点存的是对话状态、由框架自动维护；虚拟文件是智能体主动写入的工作产物，两者用途与生命周期都不同。
