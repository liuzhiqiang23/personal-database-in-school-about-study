---
concept: middleware-execution-order
one_liner: 多个中间件同挂时遵循同一条铁律——before 按列表正序、after 按列表逆序、wrap 层层嵌套，列表顺序即依赖关系配置
stage_span: [stage-2]
prerequisites: [middleware-hooks]
related: [builtin-middleware-catalog, pii-redaction-middleware]
applications: [pii-redaction-middleware, middleware-flow-control]
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#五、执行顺序铁律：before 正序 / after 逆序 / wrap 嵌套
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、3 个 middleware 同挂，看 before / after 触发顺序
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、wrap_model_call 嵌套：俄罗斯套娃式的包裹
---

## 是什么

真实工程里一个智能体往往同时挂好几个中间件，这时"多个中间件按什么顺序触发"就成了必须确定的事——因为中间件之间常有依赖（脱敏必须发生在日志之前，日志才记得到脱敏后的消息）。

规律只有一条：**正序进、逆序出**。它有三种表达形态：

```
before_model 正序     →  [M1 → M2 → M3]
wrap_model_call 嵌套  ↓  M1 { M2 { M3 { LLM } } }
after_model 逆序      ←  [M3 ← M2 ← M1]
```

这是栈式结构，像穿衣服和脱衣服：进入时按顺序一层层穿上，退出时反过来一层层脱下。掌握它之后，`middleware=[...]` 的列表顺序就成了安排依赖关系的开关。

## 怎么用

挂三个都实现同一钩子的中间件，各自打印标识：

```python
class OrderM(AgentMiddleware):
    def __init__(self, tag): self.tag = tag
    def before_model(self, state, runtime):
        print(f"→ [before_model] {self.tag}  (消息数={len(state['messages'])})")
    def after_model(self, state, runtime):
        print(f"← [after_model]  {self.tag}")

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[OrderM("M1"), OrderM("M2"), OrderM("M3")],   # 列表顺序即执行顺序基准
)
```

实测触发序列：

```
→ [before_model] M1   ┐
→ [before_model] M2   │  before 正序：M1 → M2 → M3
→ [before_model] M3   ┘
← [after_model]  M3   ┐
← [after_model]  M2   │  after 逆序：M3 → M2 → M1
← [after_model]  M1   ┘
```

包裹钩子的嵌套形态：

```
↓ [wrap_model_call] M1 入口（最外层）
    ↓ [wrap_model_call] M2 入口（中间层）
        ↓ [wrap_model_call] M3 入口（最内层）
        ↑ [wrap_model_call] M3 出口（最内层）
    ↑ [wrap_model_call] M2 出口（中间层）
↑ [wrap_model_call] M1 出口（最外层）
```

## 关键细节与参数

- **铁律对多轮模型调用同样成立**：含工具调用的问题有两轮模型调用，两轮的触发顺序完全一致，没有例外。
- **铁律不随钩子类型改变**：循环级钩子（`before_agent` / `after_agent`）与模型级钩子遵守同一条规律，实测中未实现某钩子的中间件被自动跳过、其余顺序不变。
- **包裹钩子最内层最贴近真实模型调用**：可以在调用发生的最后一刻改写请求（临时切换模型、调整参数），这正是模型降级类中间件的实现基础。
- 一个中间件没实现某钩子时框架跳过它继续下一个，不报错。

## 常见陷阱

- **把依赖关系寄望于框架自动处理**：框架只按列表顺序执行，"先脱敏再打日志"必须靠把脱敏中间件排在日志中间件前面来实现。
- **以为 after 也是正序**：实测 `after_*` 严格逆序，按正序假设写的汇总逻辑会拿到与预期不同的中间状态。
- **把内置中间件与自定义中间件的相对位置当成无关紧要**：实测里自定义日志排在调用次数限制中间件之前，日志就先于限流检查打印；调换顺序即调换行为。
