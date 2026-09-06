---
name: extracting-structured-output
description: 让 LangChain Agent 不返回自由文本，而是返回经 Pydantic 校验、下游程序可直接按字段取值的结构化对象。Use when 需要从文本里抽字段（评论分类、订单要素、简历解析、工单分级）、要把模型输出接进统计或数据库、或排查「让模型输出 JSON 结果却是中文键名与字符串数字」「ProviderStrategy 报 400 This response_format type is unavailable now」这类问题时。涵盖 schema 定义、response_format 配置、structured_response 消费、两种策略选型与兼容边界、批量抽取；不含工具调用循环本身（见 building-tool-calling-agent）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、定义 Pydantic schema：ReviewAnalysis 与 OrderInfo
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、用 ToolStrategy 包装 schema 传给 create_agent
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、invoke 一条评论，读 structured_response
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#3、结构化为什么「可信赖」：校验机制的两层保护
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、同一条评论，两种输出方式
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、三种写法对比与 DeepSeek 实测
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、两种策略的底层机制与兼容性矩阵
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、换 OrderInfo schema 抽订单文本
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、批量抽取与结构化数据的可计算性
---

## 能力目标

给 `create_agent` 传一个 `response_format`，让每次调用除消息流外再返回一个经校验的 Python 对象：下游程序直接 `.字段名` 取值、拿到的整数就是 `int`、键名由 schema 锁定，无需任何字符串解析，可直接进统计、报表或自动化流程。

## 前置

- 已能用 `create_agent` 组装 Agent（见 building-tool-calling-agent）。
- schema 用 Pydantic 定义，`pydantic` 随 langchain 一并装好，无需单独安装。
- 模型需支持工具调用——结构化输出的通用策略正是借工具调用协议实现的。

## 实操流程

1. 定义 schema：继承 `BaseModel`，每个字段给类型注解与 `Field(description=...)`。描述文字会被传给模型，直接引导它「这个字段该填什么」，是抽取质量的关键：

   ```python
   # schemas.py
   from pydantic import BaseModel, Field

   class ReviewAnalysis(BaseModel):
       """客户评论分析结果"""
       sentiment: str = Field(description="情感极性：positive / negative / neutral")
       category: str = Field(description="问题类别：logistics / product_quality / refund 等")
       urgency: int = Field(description="紧急程度，1-5 的整数，5 最紧急")
   ```

   ```bash
   python3 schemas.py    # 跑一次 __main__ 块，确认字段列表正确、能实例化
   ```

2. 把 schema 用策略类包一层传给 `response_format`。默认走 `ToolStrategy`——它把 schema 的字段封装成一个工具的参数，让模型以「填参数」的方式产出结构化结果，适用于任何支持工具调用的模型：

   ```python
   # step3_create_agent_structured.py
   from langchain.agents import create_agent
   from langchain.agents.structured_output import ToolStrategy
   from schemas import ReviewAnalysis

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[],
       response_format=ToolStrategy(ReviewAnalysis),
   )
   ```

   纯抽取任务 `tools` 传空列表即可。返回类型仍是 `CompiledStateGraph`，只是在生成最终回答前多走一道按 schema 约束输出的环节。

3. 调用并读结构化结果。开启后 `result` 多出 `structured_response` 这个 key：

   ```python
   result = agent.invoke({"messages": [{"role": "user", "content": review_text}]})
   print("result keys:", list(result.keys()))     # ['messages', 'structured_response']
   sr = result["structured_response"]
   print(type(sr).__name__, sr.sentiment, sr.category, sr.urgency)
   ```

   `sr` 是真正的 Python 对象（类型就是你定义的类），不是字符串也不是字典；`urgency` 拿到的是整数 `5` 而非字符串 `"5"`。

4. 批量处理时一次组装、循环调用，结果可直接计算：

   ```python
   from collections import Counter

   results = [agent.invoke({"messages": [{"role": "user", "content": t}]})["structured_response"]
              for t in reviews]
   print("情感分布:", Counter(r.sentiment for r in results))
   print("平均紧急度:", round(sum(r.urgency for r in results) / len(results), 1))
   ```

5. 换业务只换 schema 类，其余代码不动：

   ```python
   from schemas import OrderInfo
   agent = create_agent(model="deepseek:deepseek-chat", tools=[],
                        response_format=ToolStrategy(OrderInfo))
   ```

## 校验回路

1. **单条抽取**：`result` 里有 `structured_response` key，且它的类型是你定义的 schema 类。
2. **字段取值**：逐个 `.字段名` 取值，确认值与类型都符合声明（整数字段是 `int` 而不是字符串）。
3. **批量复用**：循环处理多条文本全部返回实例，能直接用 `Counter` / `sum` 统计而不做任何字符串解析。

三项都过，说明结构化输出在你的业务上闭环。

## 常见陷阱

- **靠提示词让模型「输出 JSON」当作结构化**：即便提示了 JSON，模型也会自由发挥——实测拿到的是中文键名「情感极性」、值是字符串「高」，类型不安全、键名不可控，下游还得手写解析。真正的结构化必须走 `response_format` + schema 校验。
- **在 DeepSeek 上用 `ProviderStrategy`**：会直接报 `BadRequestError 400: This response_format type is unavailable now`。这不是代码写错，是该提供方没有原生结构化输出端点。选型按兼容性：DeepSeek 与本地 Ollama 只能用 `ToolStrategy`；OpenAI、Anthropic 两种都可用，原生策略在 API 层硬约束、更稳。默认写 `ToolStrategy`，只有确认提供方支持原生端点时才换。
- **直接把 schema 类裸传 `response_format`**：可以，框架会自动选策略，在不支持原生端点的提供方上自动降级到 `ToolStrategy`，结果与显式写完全一致。想让选型意图可读就显式写。
- **字段取值不受控**：没加枚举约束的字段，模型可能填中文而非预期英文；同一段文本多次调用的分类也可能有细微差异。要锁死取值范围就用 `Literal` 类型注解，或在字段描述里明确列出可选项。
- **误以为模型填的值一定合法**：有两层保护——字段描述在源头引导（描述写「1-5 的整数」时，模型面对「10 级紧急」的文本仍会收敛到 5），Pydantic 校验在末端拦截（越界值抛 `ValidationError` 并指明字段）。要强约束就把范围写进字段描述并加校验器，别只靠模型自觉。
