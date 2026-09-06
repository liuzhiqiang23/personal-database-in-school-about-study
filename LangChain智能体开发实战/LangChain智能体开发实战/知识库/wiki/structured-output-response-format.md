---
concept: structured-output-response-format
one_liner: 传 response_format 让智能体在消息流之外多返回一个经校验的 Python 对象，下游程序直接按字段取值而非解析文本
stage_span: [stage-2]
prerequisites: [create-agent-entry, pydantic-schema-design]
related: [structured-output-strategy-compat, retrieval-grader]
applications: [retrieval-grader, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、用 ToolStrategy 包装 schema 传给 create_agent
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、invoke 一条评论，读 structured_response
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、同一条评论，两种输出方式
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、批量抽取与结构化数据的可计算性
---

## 是什么

普通调用返回的是一段自然语言回答：对人友好，对下游程序不友好——程序要取某个字段，还得自己写解析逻辑。结构化输出解决的正是这个问题：给智能体传入 `response_format` 参数，它就会在消息流之外额外返回一个**经过校验的 Python 对象**，下游程序可以直接按字段名取值。

机制上，传了 `response_format` 之后，编译出的图在生成最终回答前多走一道"按数据模型约束输出"的环节；返回的结果字典因此多出一个 `structured_response` 键。这让"人工智能分析结果"变成"可编程的数据"——能直接进报表、能触发自动化流程。

## 怎么用

数据模型不是裸传，而是用策略类包一层：

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from schemas import ReviewAnalysis

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(ReviewAnalysis),   # 关键：开启结构化输出
)
```

调用方式不变，差别在读结果：

```python
result = agent.invoke({"messages": [{"role": "user", "content": reviews[0]}]})

print("result keys:", list(result.keys()))     # ['messages', 'structured_response']
sr = result["structured_response"]
print("类型:", type(sr).__name__)              # ReviewAnalysis
print("  .sentiment =", sr.sentiment)          # negative
print("  .urgency   =", sr.urgency)            # 5（整数，不是字符串）
```

批量处理时循环调用即可，结果直接参与计算：

```
情感分布: {'negative': 5, 'positive': 2}
平均紧急度: 3.9
批量处理成功率: 7/7 (100%)
```

## 关键细节与参数

- **结果只有两个键**：`messages`（熟悉的消息流）与 `structured_response`（结构化结果）。设计上结构化对象不混在消息里，单独放一个键。
- **`structured_response` 是真正的 Python 对象**，类型就是定义的数据模型类，不是字符串也不是字典，可直接按字段取值、编辑器能补全字段名。
- **类型被数据模型强制约束**：声明为整数的字段拿到的是整数 `5` 而非字符串 `"5"`。
- 组装后的返回类型仍是 `CompiledStateGraph`，与不开结构化输出时完全一致。
- 工具列表可以为空：抽取类任务不需要额外工具，模型直接读文本按模型抽取。
- 批量一致性实测：7 条文本全部返回结构化实例，零失败；统计全部用标准库的计数与求和直接算出，无任何字符串解析。

## 常见陷阱

- **靠提示词让模型"输出 JSON"当作结构化**：实测不带 `response_format` 时，即便提示模型输出 JSON，返回的仍是字符串，键名被模型自由发挥成中文、数值被写成"高"这类字符串，类型不安全、键名不可控。把结构化约束交给框架，而不是赌模型每次都按要求格式化。
- **忽略模型输出的随机性**：同一段文本多次调用可能得到细微不同的分类结果（实测同一条评论在两次实验里分别被归入不同类别）。要提高一致性，在字段描述里给出明确的分类指引或用字面量类型锁死可选值。
- **裸传数据模型类而不了解背后选了哪种策略**：直接传类时框架会自动选策略，能否用取决于服务商能力（见 structured-output-strategy-compat）。
