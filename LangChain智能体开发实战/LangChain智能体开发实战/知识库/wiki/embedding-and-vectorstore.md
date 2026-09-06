---
concept: embedding-and-vectorstore
one_liner: 向量化把片段变成可按语义比对的向量存进向量库，再包成检索器；向量模型的语言匹配度直接决定检索准不准
stage_span: [stage-2]
prerequisites: [document-chunking]
related: [agentic-rag-loop, retrieval-grader, local-environment-traps]
applications: [agentic-rag-loop, retrieval-grader]
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#3、HuggingFaceEmbeddings 向量化 + InMemoryVectorStore 入库 + as_retriever
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#embedding 模型选型：换一个多语言模型，中文检索明显变准
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、可替换的部分（换成你的业务）
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#4、迁移前置假设清单
---

## 是什么

切好的片段还是纯文本，检索器没法直接按语义比对。向量化（embedding）把每个片段转成一串浮点数，让语义相近的文本在向量空间里距离也近；检索时把用户问题也转成向量，找出距离最近的几个片段，就实现了"按意思找而非按关键词找"。

向量存进向量库，再用 `as_retriever` 把向量库包装成统一的**检索器**接口，对外暴露返回条数等检索参数。这层统一接口是后续能"换模型不换架构"的原因。

## 怎么用

```bash
pip install langchain-huggingface sentence-transformers
```

```python
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = InMemoryVectorStore.from_documents(doc_splits, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

docs = retriever.invoke("退款需要多久到账？")
for i, d in enumerate(docs):
    print(f"  [{i}] source={d.metadata['source']}")
```

中文知识库换多语言向量模型，只改一行加重建向量库：

```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
```

## 关键细节与参数

- 实测基线模型把任意文本编码成 **384 维**向量，体积小、本地可跑、无需接口密钥——选本地向量模型而非云端向量接口，是为了让整条链路在没有额外密钥时也能跑通。
- `search_kwargs={"k": 3}` 表示每次检索返回最相关的 3 个片段。
- **向量模型的语言匹配度是最重要的工程决策之一**：实测三个中文查询下，英文优化模型有两个返回了不相关文档（问"退款审核多久"返回评价修改文档、问"商品库存不足"返回余额退款文档），换成多语言模型后三个查询全部命中最相关文档。中文知识库应优先选多语言或中文专用模型。
- **换向量模型零架构成本**：向量库的向量接口是统一的，换模型只改模型名一行加重建向量库，检索器、工具、智能体全不用动。
- **检索排序天然会出偏差**：实测用"退款需要多久到账"检索，返回的最相关 3 篇里混进了讲评价修改的不相关文档。这不是 bug，而是向量检索的固有特性，也正是引入质量门控的直接动机。
- **内存向量库是教学与原型选择，不是生产方案**：向量存在进程内存里，进程一退就没了，每次启动都要重新向量化全部文档。推到生产需换成持久化向量库，并考虑异步检索、批量评分等工程优化。

## 常见陷阱

- **中文知识库用英文优化的向量模型**：这是检索"找不对内容"最常见的根因，且表现为静默的排序偏差而非报错。迁移后若检索返回全是不相关文档，先怀疑向量模型的语言匹配度。
- **以为检索一定能找对内容**：向量检索是按语义近似找，选错模型就会找偏；对不准的检索结果，还需要一道质量门控兜底（见 retrieval-grader）。
- **在生产里沿用内存向量库**：重启即失忆，且大知识库每次启动重新向量化的开销不可接受。
- **在外置磁盘上加载本地向量模型**：可能撞上资源分叉文件导致的解码错误，处理方式见 local-environment-traps。
