---
concept: observability-platform-choice
one_liner: 自托管与托管服务两条可观测路径的决定因素不是技术而是合规——数据能否出境
stage_span: [stage-1, stage-2]
prerequisites: [agent-tracing-model]
related: [langfuse-selfhost-setup, langfuse-langchain-integration, pii-redaction-middleware]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#八、路径选型：Langfuse self-host 与 LangSmith SaaS 的取舍
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、前置假设清单
  - experiments/langchain/stage-1-bootstrap/handbook.md#一、LangChain 是什么:项目定位与本节目标
---

## 是什么

可观测有两条主流路径：把整套观测服务部署在自己机器上的自托管平台，和框架方提供的托管服务。它们的能力差别不大，真正分野在数据归属——一条把 trace 存在本地，一条把每次调用的输入输出上报到境外服务器。

框架自身的定位文档就把可观测列为围绕智能体生命周期的核心能力板块之一，配套的托管追踪与评估平台是官方方案。

## 怎么用

托管服务的接入比自托管更省事，业务代码零改动，只需三个环境变量：

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls-...        # 在 smith.langchain.com 获取
export LANGSMITH_PROJECT=my-project
```

设好这三个变量，框架会自动上报 trace，连回调处理器都不用建。自托管路径则需要显式建回调处理器并挂到调用配置上（见 langfuse-langchain-integration）。

## 关键细节与参数

| 维度 | 自托管平台 | 托管服务 |
| --- | --- | --- |
| **接入方式** | 显式建回调处理器并挂到调用配置 | 仅 3 个环境变量，业务代码零改动 |
| **数据归属** | 本地容器（关系库、列式库、对象存储），不离开本机 | 上报到境外服务器 |
| **合规性** | 数据不出境，金融、医疗、政务可用 | 数据出境，受限场景不可用 |
| **成本** | 免费、无调用量上限 | 免费额度每月 5000 条 trace |
| **运维** | 需自己起并维护容器栈 | 无需运维，开箱即用 |

选型的核心决定因素不是技术、而是合规：

- 数据不能出境的场景：只能自托管，托管服务出局。
- 个人项目、学习、内部原型：两者都行，托管服务更省事、零代码改动。

另有环境前提差异：自托管需要本机装容器运行时；托管服务不需要，但需要能访问境外网络。

## 常见陷阱

- **按"省事"选型而忽略数据流向**：托管服务的省事代价是每次调用的输入输出都离开本机，敏感业务上这是不可逆的合规问题。
- **以为脱敏能替代路径选型**：消息脱敏挡住的是模型服务商侧的敏感字段，与 trace 数据整体的存放地是两件事。
- **未实际验证托管路径就当作已跑通**：环境变量层面的对比不等于真实上报，正式采用前需拿到有效密钥后跑通一次。
