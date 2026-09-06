---
concept: builtin-middleware-catalog
one_liner: 框架随附 14 个开箱即用中间件（限流、重试、降级、摘要、审批等），一行声明即启用，但参数风格不统一必须先核签名
stage_span: [stage-2]
prerequisites: [middleware-hooks]
related: [middleware-execution-order, pii-redaction-middleware, hitl-implementation-routes, todo-planning-mechanism]
applications: [deepagents-harness, hitl-implementation-routes]
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#四、内置 middleware：一行声明换横切能力
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、ModelCallLimitMiddleware：给 Agent 装一个调用次数闸门
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、其他常用内置 middleware 一览
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#4、迁移前置假设清单
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、核对 v0.6.7 的 API 与内置工具
---

## 是什么

自己写中间件之外，框架随附了一批开箱即用的中间件，覆盖最常见的横切场景。用法是"一行声明"——不用写任何钩子逻辑，直接实例化挂到中间件列表即可。v1 当前导出 14 个：

| 内置中间件 | 用途 |
| --- | --- |
| `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` | 模型 / 工具调用次数限流 |
| `PIIMiddleware` | 敏感信息脱敏 |
| `ModelRetryMiddleware` / `ToolRetryMiddleware` | 模型 / 工具调用失败自动重试 |
| `ModelFallbackMiddleware` | 主模型失败时降级到备用模型 |
| `SummarizationMiddleware` / `ContextEditingMiddleware` | 上下文摘要 / 裁剪 |
| `HumanInTheLoopMiddleware` | 关键操作前插入人工审批 |
| `TodoListMiddleware` / `LLMToolSelectorMiddleware` / `LLMToolEmulator` | 任务清单 / 工具筛选 / 工具模拟 |
| `ShellToolMiddleware` / `FilesystemFileSearchMiddleware` | Shell 工具 / 文件搜索 |

这份清单还是理解长程脚手架的钥匙：长程智能体脚手架预装的规划机制就来自其中的任务清单中间件，没有重造轮子。

## 怎么用

调用次数闸门（控成本、防失控循环）：

```python
from langchain.agents.middleware import ModelCallLimitMiddleware

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[log_before, ModelCallLimitMiddleware(run_limit=2)],
)
```

工具重试（比手写异常捕获多了退避策略）：

```python
ToolRetryMiddleware(max_retries=2, backoff_factor=2.0, retry_on=(Exception,), on_failure='continue')
```

模型降级（注意是位置参数）：

```python
ModelFallbackMiddleware("deepseek:deepseek-chat", "openai:gpt-4o")
```

## 关键细节与参数

- **调用次数限制**三个核心参数：`thread_limit`（整个会话线程累计上限）、`run_limit`（单次运行内上限）、`exit_behavior`（超限行为，`'end'` 默认安静结束、`'error'` 抛异常）。
  - 实测 `run_limit=2` 时含一次工具调用的问题恰好不超限、正常完成；`run_limit=1` 加 `exit_behavior='error'` 时第 2 次模型调用直接抛 `ModelCallLimitExceededError: Model call limits exceeded: run limit (1/1)`，错误里的 `(1/1)` 表示"已用 1 次 / 上限 1 次"。
  - 两种退出行为对应两种工程取向：安静结束适合"尽力而为、不报错"的场景；抛异常适合需要明确感知被限流并做处理的场景。
- **工具重试**默认重试 2 次、退避乘数 2.0（每次重试等待时间翻倍）、默认捕获所有异常、重试耗尽后继续而非抛错。实测里随机失败的工具第 1 次失败、自动重试后第 2 次成功。
- **模型降级的真实签名是 `(first_model, *additional_models)`——位置参数**，第一个是首选降级目标、之后是再次降级的链。
- 内置中间件与自定义中间件在执行顺序上同等对待，均按列表顺序参与正序/逆序规律。

## 常见陷阱

- **假设内置中间件都用关键字参数**：参数风格并不统一——调用次数限制用关键字参数，模型降级用位置参数。按关键字写法调用降级中间件会直接抛类型错误。挂载前先确认真实签名。
- **把限流上限设得低于循环需要的轮数**：含一次工具调用的问题至少需要两轮模型调用，上限设为 1 会把正常循环拦腰截断。
- **用限流替代业务级拦截**：调用次数限制是按次数机械地拦，无法按内容判断；按业务逻辑拦截并注入自定义回复要用执行流控制（见 middleware-flow-control）。
