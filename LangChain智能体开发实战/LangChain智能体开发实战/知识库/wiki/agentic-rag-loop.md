---
concept: agentic-rag-loop
one_liner: 把检索器包成工具交给智能体，检索从写死的前置步骤变成模型自主决策的一次工具调用，还会自己改写查询重试
stage_span: [stage-2]
prerequisites: [tool-function-contract, create-agent-entry, embedding-and-vectorstore]
related: [retrieval-grader, tool-calling-loop, document-chunking]
applications: [retrieval-grader, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#一、开篇：让 Agent 自己决定何时检索知识库
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 @tool 把检索器包成 search_docs 工具
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、组装 Agent 并观察自主检索与改写
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#docstring 决定工具调用：问知识库之外的问题，Agent 怎么反应
---

## 是什么

检索增强生成是给模型外接私有知识库的常见做法。传统形态把这条链写死——"先检索、再作答"是固定流程，检索一次、拿到什么用什么。

智能体形态的做法不同：**把检索器包装成一个工具交给智能体**，由模型自己推理"这个问题要不要检索、检索什么、检索结果够不够用"。检索从写死的前置步骤变成了模型自主决策的一次工具调用——这是它与固定检索链最本质的区别。

带来的直接效果是模型会像人一样"这次没查准，换个说法再查"：它把检索当成可以反复调用的工具，自动改写查询重试。

整条链路：加载文档 → 切分 → 向量化 → 存入向量库 → 包成检索器 → 包成工具 → 智能体自主检索 → 评分门控 → 生成答案。

## 怎么用

用工具装饰器把检索器包成工具，docstring 写清这个知识库覆盖什么：

```python
from langchain_core.tools import tool

@tool
def search_docs(query: str) -> str:
    """搜索电商平台知识库，获取关于订单、退款、物流、账号、支付、售后等问题的答案。"""
    docs = retriever.invoke(query)
    return "\n\n".join(f"[来源: {d.metadata['source']}]\n{d.page_content}" for d in docs)
```

组装方式与普通智能体完全一致：

```python
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[search_docs],
)
result = agent.invoke({"messages": [{"role": "user",
    "content": "退款审核通过后，用微信支付的订单多久到账？"}]})
```

## 关键细节与参数

- 包装后的工具类型是 `StructuredTool`，与其他工具没有区别，因此它天然继承工具调用循环的全部性质。
- **自主改写实测**：一个跨主题的问题产生 8 条消息，三条模型消息各自发起了一次检索，查询词依次是「微信支付 退款 审核通过 到账时间」「退款到账时间 微信支付 多久」「退款 微信支付 到账 原路返回」——智能体自己改写了三次查询、检索了三次，直到基于检索内容给出最终回答。
- **docstring 决定检索工具何时被调用**：实测完全无关的问题（问天气、写诗）工具调用次数为 0，智能体直接用模型自身能力回答；边界模糊的问题（问某公司市值）会误触一次检索，检索无果后模型用自身知识兜底。描述越精确，误触越少。
- **改写重试的停止条件是模糊的**：这一版全凭模型自己感觉，没有明确标准判断"这次检索结果够不够好"。实测三次改写仍未精准命中目标文档。给重试装上明确的质量判断标准，正是质量门控要补的一环。
- 换知识库不改框架代码：切分、向量化、入库、包工具、组装这条流水线与领域无关。

## 常见陷阱

- **以为检索未命中会报错**：不会。智能体会退回到用模型自身知识兜底，用户以为答案来自知识库、实际是模型自己编的——这是幻觉风险的主要来源。
- **把检索工具的 docstring 留成通用描述**：迁移到自己的知识库后应改写成准确的领域描述，否则边界问题误触频繁。
- **只加检索工具就当作完成**：没有质量门控时，"知识库里没有"与"模型自己编"无法区分，企业场景下这是不可接受的。
