---
concept: system-prompt-boundary
one_liner: 系统提示词控制模型「怎么说」，不控制「做什么」——调哪个工具由工具描述与用户问题共同决定
stage_span: [stage-2]
prerequisites: [create-agent-entry, tool-function-contract]
related: [tool-calling-loop, subagent-delegation]
applications: [human-in-the-loop-interrupt, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、system_prompt：控制「怎么说」而非「做什么」
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、定义 mock 危险工具 refund_order（在工具内调 interrupt）
---

## 是什么

`system_prompt` 是组装智能体时传入的系统提示词，定义它的角色与说话风格。它有一条明确的职责边界：**控制模型"怎么说"，不控制"做什么"**。决定调哪个工具的逻辑，由工具的 docstring 加用户问题共同决定，系统提示词不参与这一层。

工具调用循环是稳定的核心，系统提示词是可调的外衣。理解这条边界，才知道行为不符预期时该改哪里——回答风格不对改提示词，工具选错改 docstring。

## 怎么用

保持工具和问题不变、只换系统提示词，对照观察：

```python
# Prompt A: 标准订单助手（默认）
system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。"

# Prompt B: 极简风格
system_prompt="只报关键状态，不加解释。"
```

实测结果：

```
Prompt A 最终回答: 订单 A1001 当前的状态是已发货，预计明天到达。
                 需要我帮你查询一下该订单的物流轨迹吗？
Prompt B 最终回答: 订单 A1001：已发货。

对比总结:
- 两个 agent 调用了相同的工具（tool_calls 不变）
- 但 system_prompt 改变了最终回答的风格和长度
- 工具调用循环本身（agent loop）不受 system_prompt 影响
```

## 关键细节与参数

- 两个智能体调用的工具完全一致，差异只出现在最终回答的风格与长度上。
- 生产中的实用价值：同一套工具，配"热情的客服"让回答有温度，配"简洁报告状态"提高内部工具效率，配"同时用中文和英文回答"直接控制输出格式。
- **边界有一处例外值得注意**：提示词虽不决定"调哪个工具"，但能影响"要不要先做别的"。实测中模型有时会自作主张先查一遍订单再考虑执行危险动作，导致关键工具迟迟不被调用；把提示词写清"用户要求退款时必须立即调用退款工具，不需要先查询"，配合明确措辞的用户消息，才能稳定触发预期路径。
- 在长程脚手架里，子智能体的 `system_prompt` 承担更重的职责：它直接决定子智能体的信息提炼能力，而提炼能力决定了上下文压缩效果。

## 常见陷阱

- **靠改系统提示词来纠正选错工具**：选错工具应改工具的 docstring，改提示词通常无效。
- **靠提示词让模型输出 JSON 当作结构化输出**：实测即便提示"请输出 JSON"，模型仍可能用中文键名、把数值写成字符串，结果类型不安全、键名不可控（见 structured-output-response-format）。
- **提示词里省略关键执行顺序**：涉及危险动作、审批等强顺序要求的场景，提示词必须写明"立即调用哪个工具"，否则模型的自主探索会绕开预期路径。
