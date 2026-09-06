---
name: applying-builtin-middleware
description: 给 LangChain Agent 一行声明挂上开箱即用的内置 middleware，直接获得模型与工具调用限流、敏感信息脱敏、失败重试、模型降级等横切能力。Use when 需要控住 Agent 的模型调用成本、防止失控循环、把用户消息里的邮箱手机号挡在模型之外、给不稳定的工具加自动重试、或排查「内置 middleware 参数报 TypeError」「脱敏没生效」这类问题时。涵盖内置清单、限流参数与超限行为、脱敏内置类型与自定义正则、重试与降级签名差异；不含自己写钩子（见 writing-agent-middleware）与人工审批（见 gating-agent-actions-with-approval）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、确认 middleware 模块就位
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、ModelCallLimitMiddleware：给 Agent 装一个调用次数闸门
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、其他常用内置 middleware 一览
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#3、PIIMiddleware：把敏感信息挡在模型之外
---

## 能力目标

不写任何钩子逻辑，直接实例化框架自带的 middleware 挂进 `create_agent(..., middleware=[...])`，让 Agent 立刻具备限流、脱敏、重试、降级这类生产必需的横切能力，并知道每个内置项的真实参数签名与超限行为。

## 前置

- 已能用 `create_agent` 组装 Agent（见 building-tool-calling-agent）。
- 全部内置 middleware 从 `langchain.agents.middleware` 一处导入。

## 实操流程

1. 先确认模块就位并看清可用清单：

   ```python
   from langchain.agents.middleware import (
       ModelCallLimitMiddleware, ToolCallLimitMiddleware,
       PIIMiddleware, ToolRetryMiddleware, ModelRetryMiddleware,
       ModelFallbackMiddleware, SummarizationMiddleware,
   )
   ```

   ```bash
   source .venv/bin/activate
   python step1_middleware_base.py
   ```

   v1 当前导出 14 个内置 middleware，覆盖这些横切场景：

   | 内置项 | 用途 |
   | --- | --- |
   | `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` | 模型、工具调用次数限流 |
   | `PIIMiddleware` | 敏感信息脱敏 |
   | `ModelRetryMiddleware` / `ToolRetryMiddleware` | 调用失败自动重试 |
   | `ModelFallbackMiddleware` | 主模型失败时降级到备用模型 |
   | `SummarizationMiddleware` / `ContextEditingMiddleware` | 上下文摘要、裁剪 |
   | `HumanInTheLoopMiddleware` | 关键操作前插入人工审批 |
   | `TodoListMiddleware` / `LLMToolSelectorMiddleware` / `LLMToolEmulator` | 任务清单、工具筛选、工具模拟 |
   | `ShellToolMiddleware` / `FilesystemFileSearchMiddleware` | Shell 工具、文件搜索 |

2. 控成本、防失控循环，挂调用次数闸门。三个核心参数：`thread_limit`（整个会话累计上限）、`run_limit`（单次运行上限）、`exit_behavior`（超限行为，`'end'` 安静结束或 `'error'` 抛异常）：

   ```python
   # step3_call_limit.py
   from langchain.agents.middleware import ModelCallLimitMiddleware

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[query_order, track_shipping],
       middleware=[ModelCallLimitMiddleware(run_limit=2)],
   )
   ```

   ```bash
   python step3_call_limit.py
   ```

   估算 `run_limit` 时按循环真实轮数给：一个含一次工具调用的问题需要两轮模型调用，`run_limit=2` 刚好够用；设成 1 且 `exit_behavior='error'` 会在第二轮抛 `ModelCallLimitExceededError: Model call limits exceeded: run limit (1/1)`，括号里是「已用 / 上限」。需要业务感知被限流就用 `'error'`，尽力而为的场景保持默认 `'end'`。

3. 把敏感信息挡在模型之外。第一个参数是脱敏类型名，内置类型只需传名字，自定义类型必须配 `detector` 正则；策略 `redact` 整段替换、`mask` 部分遮罩保留尾部：

   ```python
   # step4_pii_middleware.py
   from langchain.agents.middleware import PIIMiddleware

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[query_order],
       middleware=[
           PIIMiddleware("email", strategy="redact"),
           PIIMiddleware("phone", detector=r"1[3-9]\d{9}", strategy="mask"),
       ],
   )
   ```

   ```bash
   python step4_pii_middleware.py
   ```

   脱敏发生在消息送进模型之前，因此模型全程只看到脱敏后的内容。换一个正则（身份证号、银行卡号）就能复用同一套机制。

4. 给不稳定的工具加自动重试：

   ```python
   from langchain.agents.middleware import ToolRetryMiddleware
   middleware = [ToolRetryMiddleware(max_retries=2, backoff_factor=2.0)]
   ```

   默认 `max_retries=2`、`backoff_factor=2.0`（每次重试等待翻倍）、`retry_on=(Exception,)`、`on_failure='continue'`（重试耗尽后继续而非抛错）。比手写 try/except 多了退避策略。

5. 配主模型失败时的降级链。它用**位置参数**，第一个是首选降级目标、之后是继续降级的链：

   ```python
   from langchain.agents.middleware import ModelFallbackMiddleware
   middleware = [ModelFallbackMiddleware("deepseek:deepseek-chat", "openai:gpt-4o")]
   ```

## 校验回路

- **限流生效**：把 `run_limit` 设成小于真实轮数、`exit_behavior='error'`，跑一个含工具调用的问题，确认抛出 `ModelCallLimitExceededError` 且消息里的 `(已用/上限)` 数字符合预期；再调回够用的值，确认 Agent 正常完成。
- **脱敏生效**：输入一条含邮箱与手机号的消息，检查送进模型的内容里邮箱变成占位符、手机号只剩后四位；更硬的证据是模型的最终回答里引用的也是遮罩后的号码——说明它从未接触真实号码。
- **重试生效**：让工具随机失败一次，确认它被实际调用了两次且第二次成功、Agent 未崩。

## 常见陷阱

- **假设内置 middleware 都用关键字参数**：参数风格并不统一。限流类用关键字参数（`run_limit=2`），降级类用位置参数（`first_model, *additional_models`）。按 `fallback_model=...` 这种写法调用降级类会直接 `TypeError`。挂载前先确认真实签名。
- **以为脱敏内置类型覆盖中文手机号**：内置类型只有 email、credit_card、ip、mac_address、url 五种，**不含中文手机号**。脱敏中文手机号必须自己传 `detector` 正则（如 `r"1[3-9]\d{9}"`），类型名可任取。
- **限流额度按「问题数」估**：额度算的是模型调用次数，一个含工具调用的问题就要两轮。按问题数设额度会在第一个复合问题上就被拦掉。
- **内置与自定义混挂时顺序随手写**：列表里靠前的先执行 `before_*`。要让日志记到脱敏后的消息，脱敏项必须排在日志项前面。
