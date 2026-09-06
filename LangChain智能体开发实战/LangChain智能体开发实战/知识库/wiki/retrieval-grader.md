---
concept: retrieval-grader
one_liner: 评分器给每篇检索结果打二元相关性分，命中即停止改写、全不相关则改写重试并设上限，守住知识边界不乱答
stage_span: [stage-2]
prerequisites: [agentic-rag-loop, pydantic-schema-design, structured-output-strategy-compat]
related: [embedding-and-vectorstore, structured-output-response-format]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#五、Grader 质量门控：GradeDocuments + binary_score + 改写循环
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 GradeDocuments + with_structured_output 创建 Grader
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#Grader 的完整决策 trace：相关就停、全不相关就循环改写
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#简化版 vs 进阶版：Grader 到底带来了什么
---

## 是什么

检索有两个已知缺陷：返回结果可能混入不相关片段；智能体的改写重试缺一个明确的停止标准。两者的共同答案是**评分器**——每次检索后让它逐篇判断"这篇文档和问题相关吗"，相关就停止改写、用它作答，不相关就改写查询重试。

评分结果必须是明确的二元判断，因此用结构化输出把模型的判断约束成一个字段。这是质量门控的核心，也是把"不知道就说不知道"变成可实现工程的关键。

## 怎么用

定义只含一个二元字段的数据模型，并把模型的判断约束到它上面：

```python
from pydantic import BaseModel, Field

class GradeDocuments(BaseModel):
    """对检索到的文档与问题相关性的二元评分"""
    binary_score: str = Field(description="文档是否与问题相关，回答 'yes' 或 'no'")

# 关键：该服务商需指定 method='function_calling'
grader = llm.with_structured_output(GradeDocuments, method='function_calling')
```

对每次检索到的每篇文档评分：只要有一篇得 `yes`，判定本轮找到了相关内容、停止改写；三篇全 `no` 则改写查询重试。

## 关键细节与参数

- **停止条件是"至少一篇 yes"而非"全部 yes"**：检索返回的 3 篇里只要有一篇真正相关就足够支撑作答，不必苛求三篇全相关。这是召回与精度之间的工程平衡。
- 实测评分序列：一个退款审核问题得到 `['no', 'yes', 'no']`、一个会员权益问题得到 `['yes', 'no', 'no']`，两个都在第一轮命中并停止改写。二元字段在工具调用模式下稳定输出 `yes` / `no`，没有出现自由文本或格式漂移。
- **改写循环必须有上限**：知识库里本就没有的问题会让智能体无限改写、无限检索、白白消耗 token。实测一个知识库外的编程问题连续三轮全 `no`、改写两次后达到最大重试次数停止。
- **达到上限仍全 `no` 时应走兜底策略**：明确告诉用户"知识库无此内容"。
- **门控带来的真实差异**（同一问题两版对照）：
  - 知识库内的问题：两版答案质量相当，带门控的一版只用了经筛选的相关文档、输出更干净。
  - 知识库外的问题：不带门控的一版直接用模型自身知识绕过知识库答了一段代码——用户以为答案来自知识库、实际是模型编的；带门控的一版先明确声明"知识库无相关内容"再补充通用知识，知识边界清清楚楚。
- 在合规、法律、公司制度这类知识库问答里，"不知道就说不知道"比"编一个看似合理的答案"重要得多。
- 门控还能兜住向量检索的排序偏差：即便向量模型排序不准，评分器仍能把不相关结果过滤掉。

## 常见陷阱

- **漏掉结构化输出的策略参数**：默认走服务商原生结构化输出模式，不支持的服务商会直接报 400 错误 `This response_format type is unavailable now`，显式指定工具调用方式即可（见 structured-output-strategy-compat）。
- **不设改写上限**：知识库外的问题会导致无限检索循环。
- **把评分器当成检索质量的替代品**：它是兜底而非源头，向量模型选型仍决定"能不能找到"，评分器只决定"找到的能不能用"。
- **只验证知识库内的问题**：门控是否生效的关键标志，是知识库外的问题能否得到"知识库无此内容"而非编造答案。
