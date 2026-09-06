---
name: grading-retrieved-documents
description: 给知识库问答加一道评分门控：每次检索后逐篇判断文档与问题是否相关，相关就作答、全不相关就改写查询重试，重试到上限仍无命中就明说知识库里没有。Use when 需要防止 Agent 拿知识库里根本没有的内容编答案、要给检索改写循环设一个明确的停止条件、或排查「with_structured_output 在国产模型上报 400 This response_format type is unavailable now」时。涵盖评分模型定义、结构化判断的兼容写法、停止与改写的判定规则、重试上限与兜底、有无门控的效果对比；不含知识库与检索器的搭建（见 building-agentic-rag）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 GradeDocuments + with_structured_output 创建 Grader
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#Grader 的完整决策 trace：相关就停、全不相关就循环改写
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#简化版 vs 进阶版：Grader 到底带来了什么
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、用 create_deep_agent 一行搭出长程 Agent
---

## 能力目标

在检索与作答之间插入一个评分器，把「这次检索够不够用」从模型的模糊感觉变成一个可判定的二元字段：命中就停止改写、用相关文档作答；全不命中就自动改写查询重检索；到达重试上限仍不命中，明确声明知识库无此内容而不是拿模型自身知识编一个看似合理的答案。

## 前置

- 已有可用的检索器与检索工具（见 building-agentic-rag）。
- 评分结果用结构化输出约束（见 extracting-structured-output）——判断必须落成一个固定字段，而不是一段自由文本。

## 实操流程

1. 定义评分用的数据模型，只放一个二元字段，字段描述写清取值：

   ```python
   # step6_rag_grader.py
   from pydantic import BaseModel, Field

   class GradeDocuments(BaseModel):
       """对检索到的文档与问题相关性的二元评分"""
       binary_score: str = Field(description="文档是否与问题相关，回答 'yes' 或 'no'")
   ```

2. 把模型包成评分器。**国产模型必须显式指定走工具调用方式**，否则默认走提供方原生结构化输出端点、直接报 400：

   ```python
   from langchain_deepseek import ChatDeepSeek

   llm = ChatDeepSeek(model="deepseek-chat")
   grader = llm.with_structured_output(GradeDocuments, method='function_calling')
   ```

3. 对每次检索回来的每一篇文档逐个评分，按「至少一篇命中」决定停还是改写：

   ```python
   def grade_batch(question, docs):
       grades = []
       for d in docs:
           r = grader.invoke(
               f"问题：{question}\n\n文档内容：{d.page_content}\n\n这篇文档与问题相关吗？")
           grades.append(r.binary_score)
       return grades

   grades = grade_batch(question, retriever.invoke(question))
   print("grades:", grades)          # 形如 ['no', 'yes', 'no']
   decision = "STOP" if "yes" in grades else "REWRITE"
   ```

   ```bash
   python step6_rag_grader.py
   ```

   停止条件取「至少一篇命中」而不是「全部命中」：返回的三篇里只要有一篇真正相关就足够支撑作答，苛求全命中会让循环停不下来。这是召回与精度之间的工程平衡。

4. 全不命中时改写查询重检索，并**给循环设上限**：

   ```python
   # ext7_1_grader_decision_trace.py
   def rewrite(question, last_query):
       return llm.invoke(
           f"原始问题：{question}\n上一次检索用的查询：{last_query}\n"
           "这次检索没找到相关内容，请换一组关键词重写查询，只输出新查询本身。"
       ).content.strip()

   MAX_RETRY = 3
   query = question
   for round_i in range(MAX_RETRY):
       docs = retriever.invoke(query)
       grades = grade_batch(question, docs)
       print(f"第 {round_i+1} 轮 grades={grades}")
       if "yes" in grades:
           break
       query = rewrite(question, query)      # 让模型换一组关键词
   else:
       print("知识库无相关内容")              # 到上限仍不命中，走兜底
   ```

   实测行为：知识库里有答案的问题第一轮就命中并停止；知识库外的问题（如问一段编程算法）三轮全部不命中、每轮都换一组关键词，到上限后停止。改写效果的预期形态可对照这组实测：原问题「如何在 Python 中实现快速排序算法？」被改写成「Python 快速排序代码实现示例」。没有这个上限，知识库里本就没有的问题会让 Agent 无限改写、无限检索、白烧 token。

5. 到达上限后走兜底策略：先明确告诉用户知识库里没有这项内容，再决定要不要补充通用知识。这一步是门控价值的落点——在合规、法律、公司制度这类问答里，说不知道比编一个看似合理的答案重要得多。

## 校验回路

分别问两类问题各一次，对照结果：

1. **知识库里有答案的问题**：应有文档得到命中评分、决策为停止改写，答案基于被判相关的那篇文档。
2. **知识库里没有答案的问题**：每轮评分应全为不相关、触发改写，到达上限后 Agent 明确声明知识库无此内容，而不是直接给出一段模型自己编的答案。

第二条是门控是否真正生效的关键标志。对照着不带门控的版本跑同一个知识库外问题，能直接看出差别：不带门控的会绕过知识库用自身知识作答，用户却以为答案来自知识库。

## 常见陷阱

- **不加参数直接调用结构化输出**：在 DeepSeek、Qwen 这类没有原生结构化输出端点的模型上会报 `This response_format type is unavailable now`（400）。统一显式指定走工具调用方式解决。
- **停止条件写成「全部命中」**：检索返回的多篇里通常只有一两篇真相关，要求全命中会让循环永远不停、直到耗尽重试。
- **改写循环不设上限**：知识库里没有的问题会让它一直改写下去，token 消耗不可控。上限必须显式设。
- **命中后仍把全部检索结果塞给模型**：门控的另一半价值是只把被判相关的文档喂进作答上下文，输出更干净、也更省 token。
- **把评分器的判断当绝对真值**：它是模型的二元判断，边界情形会有误判。它的作用是把不可控的兜底变得可控，不是保证百分百准确。
