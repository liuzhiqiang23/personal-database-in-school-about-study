---
concept: pii-redaction-middleware
one_liner: 脱敏中间件在消息送进模型之前替换敏感信息，内置类型只有 5 种、其余敏感字段靠自定义正则识别
stage_span: [stage-2]
prerequisites: [middleware-hooks, builtin-middleware-catalog]
related: [middleware-execution-order, observability-platform-choice]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#3、PIIMiddleware：把敏感信息挡在模型之外
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、确认 middleware 模块就位
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、3 个 middleware 同挂，看 before / after 触发顺序
---

## 是什么

脱敏中间件用来在消息送进模型之前，对个人可识别信息做替换。这是合规场景的高频需求——用户消息里的手机号、邮箱不该原样流到模型服务商那边。

它的关键性质是**脱敏发生在调模型之前**：模型从头到尾只看到脱敏后的内容。这不是"展示给人看的遮罩"，而是真正挡在了模型输入之前。实测中模型的最终回答里引用的也是遮罩后的号码，从输出端反向证明了模型从未接触过真实号码。

两种脱敏策略：`redact` 整段替换成占位符，`mask` 部分遮罩、保留尾部用于识别。

## 怎么用

同时挂内置类型与自定义正则两条规则：

```python
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order],
    middleware=[
        PIIMiddleware("email", strategy="redact"),                        # 内置类型
        PIIMiddleware("phone", detector=r"1[3-9]\d{9}", strategy="mask"), # 自定义正则
        log_pii_before,                                                   # 自定义日志，看脱敏后的消息
    ],
)
```

实测效果：

- 邮箱（`redact` 策略）：输入里的邮箱地址在送进模型前整体变成 `[REDACTED_EMAIL]`；
- 手机号（`mask` 策略）：`13812345678` 被遮罩成 `****5678`，前 7 位替换、保留后 4 位。

## 关键细节与参数

- **内置脱敏类型只有 5 种**：email、credit_card、ip、mac_address、url，**不含中国大陆手机号**。要脱敏它必须通过 `detector` 参数传正则。
- 第一个参数是脱敏类型名：用内置类型时只传名字；用自定义类型时名字可任取，但必须配 `detector` 告诉它怎么识别。
- 示例正则 `r"1[3-9]\d{9}"` 匹配中国大陆手机号（1 开头、第二位 3-9、共 11 位）。
- `mask` 策略遵循信息最小化原则：保留尾号便于人工识别、隐去完整号码。
- 换个正则（身份证号、银行卡号）就能复用同一套机制脱敏任意自定义敏感字段。

## 常见陷阱

- **以为内置类型覆盖了中文场景的常见字段**：中国大陆手机号不在内置列表里，不配正则就完全不会被脱敏，而这往往是最敏感的字段。
- **把脱敏中间件排在日志中间件之后**：执行顺序按列表正序，脱敏排在后面会让日志记录到未脱敏的原始消息。要让日志看到脱敏结果，脱敏必须排在前面。
- **只做展示层遮罩**：真正的合规要求是模型输入端就看不到原文，展示层遮罩解决不了数据外流问题。
