---
concept: todo-planning-mechanism
one_liner: 长程任务开工前先写一份待办清单并持续更新三态，让智能体每一步都看得到「还剩哪些没做」
stage_span: [stage-2]
prerequisites: [deepagents-harness, invoke-vs-stream]
related: [subagent-delegation, virtual-filesystem-context-engineering, builtin-middleware-catalog]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#四、规划机制：write_todos 让长程任务不遗漏
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、给长程任务挂上待办清单
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、把三大机制的内部状态一次看清
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#七、三机制综合验证：一次运行看齐全套能力
---

## 是什么

规划机制解决的是"越走越忘"。做法是：拿到一个多步骤任务后，智能体先调用写待办工具把任务拆成若干条待办项，每完成一批就更新清单状态，直到全部完成。清单存在智能体状态里，它每一步都能看到"还剩哪些没做"，于是不会遗漏、也不会重复。

这个机制来自框架内置的任务清单中间件——长程脚手架直接复用，没有重造轮子。它是"脚手架 = 智能体工厂加预装中间件"这一判断最直接的证据。

## 怎么用

机制自动注入，无需手动配置；观察它的方式是流式调用时读状态里的清单：

```python
task = "请帮我调研新能源汽车电池市场 4 个维度：主要厂商及市占率、核心技术路线、市场规模预测、主要风险因素，最后整合成简报。"

for chunk in agent.stream({"messages": [{"role": "user", "content": task}]},
                          config={"recursion_limit": 100}):
    if "todos" in chunk:
        print(chunk["todos"])   # 打印当前待办清单
```

## 关键细节与参数

- **第一次调用就完成拆解**：实测拿到任务后立即生成 6 条待办（一条"制定调研计划"加五个具体调研步骤），第一条设为进行中、其余设为待办。
- **清单会在执行中动态细化**：实测把"搜索厂商"进一步拆出一条子项，最终扩展到 7 条并全部完成。
- **写待办工具被反复调用**：实测调用 6 次——一次初始规划加五次状态更新；另一次综合运行里调用 4 次。智能体每完成一批任务就回头更新清单。
- **每条待办走三态机**：待办（`pending`）→ 进行中（`in_progress`）→ 已完成（`completed`）。状态流转完全由智能体自主维护，不需要开发者写任何调度代码；它是工作状态而不是开发者打的标签。
- **状态实时可追踪**：清单是状态对象的内置字段，流式运行时直接从数据块里读到，不需要额外挂钩子。实测能清晰看到从"全部待办"到"部分完成"再到"全部完成"的三个阶段。
- 验收判据：跑一个 ≥3 步的任务，确认写待办工具被调用、清单从待办逐步走到全部完成。

## 常见陷阱

- **用一次性调用观察规划过程**：清单是中间状态，只有流式调用才能实时看到它的变化，一次性调用只能看到终态。
- **给短任务硬套规划机制**：一两步的任务不需要清单，额外的规划轮次只是浪费调用。
- **忘了放宽图迭代上限**：规划带来的额外轮次会让长程任务更快撞上默认迭代上限。
