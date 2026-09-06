---
concept: parallel-tool-calls
one_liner: 模型识别到多件互不依赖的任务时，会在同一条消息里并行发出多个工具请求；参数不全时它选择追问而不是瞎猜
stage_span: [stage-2]
prerequisites: [tool-calling-loop, message-stream-anatomy]
related: [deepseek-provider-integration, subagent-delegation]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、一个问题触发多个工具
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#3、迁移后如何验证跑通
---

## 是什么

面对"同时做两件独立的事"的复合任务，智能体不必把任务拆成两轮串行执行——模型可以在一个回合里同时发出多个工具调用请求，这称为并行工具调用（parallel function calling）。判断依据是模型自己的推理：它识别出"查物流"和"算运费"互不依赖，于是并行发起。

这个能力属于模型侧，不是框架强加的：使用的型号需要支持并行工具调用，`deepseek-chat` 实测支持。

## 怎么用

构造一个需要两个工具才能回答、且参数给全的问题：

```
帮我查一下订单 A1001 的最新物流状态，同时帮我算一下 1.5kg 商品从北京寄到上海的运费。
```

真实消息流：

```
  [0] HumanMessage → 帮我查一下订单 A1001 的最新物流状态，同时帮我算一下 1.5kg 商品从北京寄到上海的运费。
  [1] AIMessage → tool_call #1: track_shipping({'order_id': 'A1001'})
  [1] AIMessage → tool_call #2: calc_shipping_fee({'origin': '北京', 'destination': '上海', 'weight_kg': 1.5})
  [2] ToolMessage → content: 2026-05-30 08:00 上海转运中心 → 正在派送中
  [3] ToolMessage → content: 从北京到上海，重量 1.5 kg，预估运费 14.5 元
  [4] AIMessage（最终回答）→ 好的，查询结果如下：...
消息总条数: 5
工具调用总次数: 2
被调用的工具: ['track_shipping', 'calc_shipping_fee']
```

## 关键细节与参数

- **消息总数是 5 条而不是 6 条**：两次工具调用挂在**同一条 AI 消息**（index=1）上并行发起，而不是各占一条消息顺序调用。这是判断"发生了并行"最直接的证据。
- 两条工具消息各自靠 `tool_call_id` 路由回对应的请求，这正是消息流路由机制的实战价值。
- 验证并行是否生效的机械判据：`工具调用总次数 ≥ 2` 且它们出现在同一条 AI 消息里。

## 常见陷阱

- **问题里少给参数，导致模型追问而非并行**：最初的问法"订单 A1001 从北京寄到上海运费多少"没给重量，模型只调了查订单工具，然后反过来追问"请问商品有多重"。模型遵循"不猜参数"原则，宁可追问也不编默认值。要触发多工具协作，必须把两件任务的参数都写明确、让它们明确并列。
- **把追问当成失败**：追问是信息驱动的正常行为，不是模型能力不足。真实产品里这反而是安全特性——参数不全就不执行。
- **假设所有模型都支持并行**：并行工具调用是模型能力，换型号后需要重新验证，方法是看多个工具请求是否挂在同一条消息上。
