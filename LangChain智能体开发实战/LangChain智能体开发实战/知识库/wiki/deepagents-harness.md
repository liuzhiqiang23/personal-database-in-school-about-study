---
concept: deepagents-harness
one_liner: 长程脚手架不是新运行时，而是智能体工厂加一组预装中间件；三层抽象按步骤数与所需机制取舍
stage_span: [stage-2]
prerequisites: [create-agent-entry, middleware-hooks]
related: [todo-planning-mechanism, subagent-delegation, virtual-filesystem-context-engineering, builtin-middleware-catalog]
applications: [todo-planning-mechanism, subagent-delegation, virtual-filesystem-context-engineering]
sources:
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#一、开篇：长程任务为什么需要一套额外的脚手架
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、核对 v0.6.7 的 API 与内置工具
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、用 create_deep_agent 一行搭出长程 Agent
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、对照实验：create_deep_agent 与 create_agent + 手装 middleware 的差别
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、三层取舍：什么时候用 deepagents、什么时候不用
---

## 是什么

写一份多源调研报告、整理十几篇论文、按章节起草长文——这类任务步骤多、链路长，往往十几步甚至几十步才完成。直接交给一个裸的智能体会撞上三道墙：

- **越走越忘**：走到第 8 步时忘了第 3 步的计划，或重复做已做过的事；
- **上下文越堆越满**：每步的中间数据都堆进对话历史，把模型的上下文窗口塞爆；
- **中间结果无处暂存**：需要一个地方存"第 3 步检索到的数据"，等第 10 步整合时取出，而不是一直挂在上下文里占地方。

长程脚手架就是为这三道墙预打包的一套能力。它的本质必须讲清：**不是一个全新的运行时，而是智能体工厂函数加上一组预装好的中间件**。手动挑装中间件与开箱即用，是同一套机制的两种取用方式。

## 怎么用

```bash
pip install deepagents
```

```python
from deepagents import create_deep_agent
from langchain_deepseek import ChatDeepSeek

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),   # 必须显式传模型
    tools=[search_market_info],
    system_prompt="你是一个市场研究助手。",
)
print(type(agent))                                # CompiledStateGraph
print(agent.get_graph().nodes)                    # 看内部计算图节点
```

打印出的图节点直接揭示了本质：

```
['__start__', 'model', 'tools', 'TodoListMiddleware.after_model', 'PatchToolCallsMiddleware.before_agent']
```

长程任务必须放宽图迭代上限：

```python
agent.stream({"messages": [...]}, config={"recursion_limit": 100})
```

## 关键细节与参数

- **返回类型与普通智能体完全一致**（`CompiledStateGraph`），调用方式也一样——底层还是同一套图执行引擎。
- **图节点是本质的直接证据**：起始、模型、工具三个节点是基础智能体就有的，多出来的两个才是脚手架自动挂上去的——任务清单中间件以调模型后的钩子接入（规划机制的来源），工具调用标准化中间件以循环开始前的钩子接入。
- 对照手装实测：手动只挂任务清单中间件时，节点里没有工具调用标准化中间件，也没有虚拟文件系统与委派工具。由此可以把等式写完整：

```
create_deep_agent ≈ create_agent
                   + TodoListMiddleware       (规划：write_todos)
                   + FilesystemMiddleware     (虚拟文件系统：write_file/read_file/ls)
                   + SubAgentMiddleware       (委派：task)
                   + PatchToolCallsMiddleware (工具调用标准化)
```

- 三大机制的工具名：规划用 `write_todos`，虚拟文件系统用 `ls` / `read_file` / `write_file` / `edit_file`，委派用 `task`。
- **必须显式传模型**：默认空模型值自 0.5.3 起已弃用。
- **必须放宽图迭代上限**：默认值 25 对长程任务远远不够，一个 7 步调研任务实际触发约 50 多次图迭代，用默认值会直接抛 `GraphRecursionError`。长程任务一般建议设到 50–100，这是第一次跑就会遇到的坑。
- 内置工具里还有一个执行代码的工具，仅在沙箱后端可用，默认后端调用它会返回错误。
- 实测版本 0.6.7，要求 Python ≥3.11、<4.0，处于 pre-1.0 阶段——接口尚未冻结，工具名与参数名可能调整。
- **三层取舍**：

| 任务 | 推荐层 | 原因 |
| --- | --- | --- |
| 快速查天气 | 智能体工厂（不挂中间件） | 简单一次性工具调用 |
| 代码审查助手 | 长程脚手架 | 3–5 步，需要规划加文件暂存 |
| 多源市场调研 | 长程脚手架 | 7 步，需要三机制全套 |
| 限流加日志代理 | 智能体工厂加手选中间件 | 需要定制钩子，不需要全套机制 |
| 论文写作助手 | 长程脚手架 | 8 步，规划加子智能体加文件 |
| 条件分支实验 | 裸图执行引擎 | 特殊图拓扑，需要条件跳转 |

决策的关键维度是步骤数（是否 ≥3 步）与是否需要规划、委派、文件暂存。口诀：任务超 3 步、怕遗忘、怕上下文爆，就用长程脚手架。

## 常见陷阱

- **不设图迭代上限就跑长程任务**：默认值下必然中途抛错，且错误信息与业务无关，容易误判。
- **依赖默认模型值**：已弃用，必须显式传模型对象。
- **把脚手架当成万能选择**：只调一两个工具的简单任务用基础智能体最轻；需要条件分支、并行、循环等特殊图拓扑时要下沉到裸图执行引擎手控。
- **按记忆写 pre-1.0 的参数名**：落地前对照当时的官方 reference 核对，重心放在不会过期的设计理念上。
