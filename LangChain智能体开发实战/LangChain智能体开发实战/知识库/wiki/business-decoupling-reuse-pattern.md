---
concept: business-decoupling-reuse-pattern
one_liner: 每一层能力都与具体业务解耦——换工具、换数据模型、换知识库、换任务都只动一处输入，框架骨架一行不改
stage_span: [stage-2]
prerequisites: [create-agent-entry, tool-function-contract]
related: [tool-function-contract, pydantic-schema-design, middleware-hooks, thread-id-isolation, agentic-rag-loop]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#六、换工具即换业务：复用验证
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、换 OrderInfo schema 抽订单文本
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#七、换 agent 即复用：middleware 与业务解耦
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#七、换数据即换业务：多轮订票偏好复用
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#八、换数据即换业务：transfer_funds 转账场景复用
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#七、换 Agent 不换接入：验证可复用性
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#六、换数据即换业务：复用验证
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、换成自己的长程任务：论文整理 + 自定义翻译子 Agent
---

## 是什么

把示例迁移到自己的业务时，最重要的判断是"哪些要换、哪些不动"。所有能力层实测下来给出的是同一个答案：**框架骨架是稳定的，业务由一处输入定义**。这不是设计口号，而是每一层都单独验证过的复用结论。

之所以成立，是因为每层的抽象点都落在数据而非代码上：工具列表定义能力边界、数据模型定义抽取结构、文档目录定义知识范围、任务描述定义长程目标。换业务等于换这处输入。

## 怎么用

各层的替换点与实测的改动量：

| 能力层 | 换业务只改 | 实测改动量 |
| --- | --- | --- |
| 工具调用循环 | 工具列表里的函数 | 只加一个函数进列表，其他代码 0 改动 |
| 结构化输出 | 数据模型类 | 只换类名，其余代码一字未改 |
| 中间件 | 无需改动，直接挂到新智能体 | 中间件代码 0 改动 |
| 持久化记忆 | 对话内容与会话标识取值 | 记忆机制一行不改 |
| 人工审批 | 危险工具本体 | 中断、续跑、存储器三件套一行没改 |
| 可观测接入 | 无需改动 | 接入两行代码一字未动 |
| 检索增强 | 文档目录（中文再换向量模型） | 只改一行目录路径，框架代码 100% 不变 |
| 长程脚手架 | 工具、子智能体、系统提示词 | 三大机制一行不用改 |

各层的最小改写示范：

```python
# 换工具：加进列表即得新能力
tools=[query_order, track_shipping, calc_shipping_fee, query_inventory]

# 换数据模型：抽取业务随之切换
response_format=ToolStrategy(OrderInfo)      # 原为 ReviewAnalysis

# 换知识库：一行目录
docs_dir = Path("new_docs")                   # 原为 Path("docs")

# 换子智能体：三个字段
translator = {"name": "translator", "description": "...", "system_prompt": "..."}
```

## 关键细节与参数

- **工具层实测**：新增一个工具函数进列表后，智能体立刻能在合适的问题上调用它——没有手写分发逻辑、没有改提示词、没有改循环代码。能力边界由工具列表定义，扩展能力等于扩展列表。
- **结构化输出实测**：只把数据模型类换掉，3 条订单文本全部正确抽取，状态判断准确。
- **中间件实测**：同一个审计中间件挂到工具集完全不同的两个智能体上都正常触发，两个实例的计数各自独立、互不干扰。
- **记忆实测**：对话场景从查订单换成多轮订票，存储器与会话标识机制原样生效；一个用户三轮累积 12 条消息，另一个用户会话保持隔离。
- **审批实测**：危险工具从退款换成转账，5000 元批准执行、20000 元高额被驳回，审批信息里还顺手携带了风险等级这类业务字段。
- **可观测实测**：三个全新工具、业务逻辑全不同的智能体，接入代码一字未动，trace 照样完整上报——可观测的接入与业务逻辑是彻底解耦的两件事。
- **检索增强实测**：把知识库从电商问答换成技术开发规范（12 篇换 5 篇），新知识库入库 5 个片段后正确回答了规范类问题。
- **长程脚手架实测**：任务从市场调研换成论文整理、子智能体换成自定义翻译角色，规划、委派、虚拟文件三大机制全部照常运转。

## 常见陷阱

- **迁移时连骨架一起改**：组装方式、调用入口、消息流读取方式、机制的挂载方式都属于骨架，改它们通常是走偏的信号。
- **换业务后不做验证就上线**：每层都有对应的三步自检（触发验证、机制验证、复用验证），跑通才算迁移完成。
- **忽略跟随业务变化的那一个参数**：多数层是纯粹零改动，但检索增强层换成中文语料时必须同时换向量模型，审批层换工具时必须重新检查副作用位置。
- **把"零改动"理解成"零理解"**：复用成立的前提是理解每层的规范（工具三规范、数据模型字段描述、审批四铁律），规范破了复用就不成立。
