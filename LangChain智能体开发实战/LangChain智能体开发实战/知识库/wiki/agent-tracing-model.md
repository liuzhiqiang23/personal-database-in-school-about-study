---
concept: agent-tracing-model
one_liner: 追踪把一次请求内藏着的多次模型与工具调用记录成一棵可展开的树，三类节点各带自己的耗时与消耗
stage_span: [stage-2]
prerequisites: [tool-calling-loop, message-stream-anatomy]
related: [langfuse-langchain-integration, observability-platform-choice]
applications: [langfuse-langchain-integration, observability-platform-choice]
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#一、开篇：Agent 为什么比传统 Web 更难调试
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#五、读懂 trace 树：可观测的原理就在这棵树上
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、三类节点：CHAIN / GENERATION / TOOL
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#3、从 trace 读出一个工程结论：Agent 为什么贵
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#六、可观测的反面价值：用 trace 定位一次工具失败
---

## 是什么

传统 Web 系统出问题，翻一条请求日志、看一行堆栈基本就能定位。智能体不一样：一次用户请求背后是 3 到 5 次模型决策和若干次工具调用，失败可能发生在任何一步——是模型选错了工具？参数不对？还是工具自己抛了错？用户只看到"查不了"三个字，开发者面对的却是一条不透明的调用链。

追踪（Tracing）就是把这条藏在框架内部的调用链完整记录下来，画成一棵能展开的树。术语上：一条完整调用链叫一条 **trace**，树里的每个节点（一次模型调用、一次工具调用）叫一个 **observation** 或 **span**。

树上的节点分三类：

| 节点类型 | 含义 | 携带的关键信息 |
| --- | --- | --- |
| **CHAIN** | 框架内部调度节点（图、模型节点、工具节点等） | 只有延迟，无 token |
| **GENERATION** | 一次模型调用 | 模型名、输入/输出 token、延迟 |
| **TOOL** | 一次工具调用 | 工具名、输入参数、输出结果 |

这条调用链是框架在执行时通过回调机制自动产生的，开发者无需手写任何埋点。

## 怎么用

跑一次带工具调用的请求后，从追踪列表进入单条 trace，展开树逐节点查看：

- 最外层是图的一次执行（根节点），往里依次是模型决策节点、工具调度节点、具体的工具调用节点；
- 点中任意节点，右侧展开它的输入、输出、token 消耗和延迟；
- 工具节点里完整保存了实际传给工具的参数与返回结果——**不用在工具里加任何打印或日志，就能看到智能体到底传了什么给工具**。

排障场景对照：

| 场景 | 排障过程 | 耗时 |
| --- | --- | --- |
| 没有追踪 | 用户只反馈"某类输入查不了"，只能从代码开始猜：翻日志、加打印、复现用户步骤 | 可能 20 分钟 |
| 有追踪 | 直接打开那条失败 trace，展开出错的工具节点，看到输入参数与抛出的错误 | 约 2 分钟 |

## 关键细节与参数

- 实测一次"查订单加查物流"的请求：观测项数量 **9**、延迟 3.77 秒、token 976 进 184 出——一次看似简单的查询，框架内部跑了 9 个嵌套节点。
- 一次三工具、三次模型调用的退款咨询实测产生 **13 个嵌套 span**。
- **一个可从树上直接读出的工程结论**：三次模型调用的输入 token 分别是 427、527、756，逐步递增——因为每一步模型决策的输入都包含此前所有工具调用的结果，上下文在累积。三次调用累计 1710 输入 token、382 输出 token，而用户只问了一句话。这就是智能体比单次问答更烧 token 的原因。
- **工具是最常见的失败点**（参数格式错误、外部服务超时、数据不存在），失败工具节点里直接带着输入参数与错误信息，无需额外埋点。
- 观测对象需满足"至少 3 步调用、其中至少 1 次工具调用"，否则树退化成一根光杆，看不出门道。

## 常见陷阱

- **指望传统请求日志拼出全貌**：一次请求含多次内部调用，日志只能记到入口和出口，中间的模型决策与工具参数拼不出来。
- **只在成功链路上验证可观测**：追踪最不可替代的价值在失败时，验收时应专门制造一次工具失败并确认能在树上定位到它。
- **看到 token 数比预期高就怀疑计费**：上下文累积是循环的固有特性，token 随步数递增属正常。
