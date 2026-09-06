---
concept: document-chunking
one_liner: 检索前必须把文档切成小片段，递归切分器优先在自然语义边界下刀，重叠字符防止关键信息被切断
stage_span: [stage-2]
prerequisites: [langchain-package-stack]
related: [embedding-and-vectorstore, agentic-rag-loop]
applications: [embedding-and-vectorstore, agentic-rag-loop]
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#2、安装依赖并用 RecursiveCharacterTextSplitter 切分
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、准备 12 篇产品 FAQ 文档
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#2、保持不变的部分（结构骨架）
---

## 是什么

检索的粒度决定检索的精度。整篇文档太长，向量化后语义被"平均"掉，检索精度差；切成小片段后，每个片段聚焦一个话题，检索能精准定位到"讲某个具体问题的那一段"而非"整篇文档"。

递归字符切分器是常用的切分器。"递归"指的是它的切分策略：优先按段落切，切不动再按换行、句号、空格逐级回退，尽量在**自然语义边界**处下刀，而不是机械地定长一刀切断。这也是它比朴素定长切分更适合中文文档的原因。

## 怎么用

```bash
pip install langchain-text-splitters
```

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
doc_splits = splitter.split_documents(docs)
print("actual_docs:", len(docs), "actual_chunks:", len(doc_splits))
```

实测：12 篇千字左右的文档切出 19 个片段，前几个片段长度分别为 391、425、456 字符。

## 关键细节与参数

- **`chunk_size`（每片目标上限）**：实测取 500。千字左右的文档切成 500 字符的片段后，多数被切成 1 至 2 片，正好对应"一个问答话题一片"的粒度。文档越长、话题越密集，这个值可适当调大。
- **`chunk_overlap`（相邻片段的重叠字符数）**：实测取 50。作用是防止一个完整句子或关键信息恰好被切断在两片边界上——重叠保证边界处语义不丢。
- 切分结果保留来源元信息，检索返回时可以直接读出片段来自哪个文件。
- **知识库规模下限**：文档太薄（少于 10 篇）时检索几乎无意义——总量小、语义区分度不够，检索器体现不出"按意思找"的价值。实测用 12 篇作为让检索效果可观察的起点。

## 常见陷阱

- **不切分直接整篇入库**：语义被平均，检索永远返回"整篇最像的那一篇"，精度无法接受。
- **重叠设为 0**：边界处的完整语义被切断，跨边界的关键信息检索不到。
- **把参数当成通用最优值**：这两个值需按语料调整，换一批文档后应重新验证检索效果。
