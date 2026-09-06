---
name: building-agentic-rag
description: 把一批本地文档变成向量知识库，包成检索工具交给 LangChain Agent，让模型自己决定何时检索、检索什么、要不要换关键词重查。Use when 需要给 Agent 外接私有知识库做问答（产品手册、公司制度、技术文档、个人笔记）、要把固定的先检索再作答改造成自主检索、或排查「中文检索返回的全是不相关文档」「导入向量化依赖报 UnicodeDecodeError」这类问题时。涵盖文档切分、向量化与入库、检索器封装成工具、Agent 组装与自主改写观察、embedding 选型、换知识库复用；不含检索结果质量门控（见 grading-retrieved-documents）。
allowed-tools: Bash(python:*), Bash(pip:*), Bash(find:*)
sources:
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、准备 12 篇产品 FAQ 文档
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#2、安装依赖并用 RecursiveCharacterTextSplitter 切分
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#3、HuggingFaceEmbeddings 向量化 + InMemoryVectorStore 入库 + as_retriever
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#embedding 模型选型：换一个多语言模型，中文检索明显变准
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 @tool 把检索器包成 search_docs 工具
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#docstring 决定工具调用：问知识库之外的问题，Agent 怎么反应
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、组装 Agent 并观察自主检索与改写
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#六、换数据即换业务：复用验证
---

## 能力目标

从一个装着领域文档的目录出发，搭出完整链路：切分成片段、向量化、入库、包成检索器、再包成工具交给 Agent。跑通后模型会自己判断某个问题要不要查知识库、用什么关键词查、第一次没查准就换个说法再查，而不是被写死成「每次先检索再作答」。

## 前置

- 已能用 `create_agent` 与 `@tool`（见 building-tool-calling-agent）。
- 知识库文档建议不少于 10 篇。太薄时语义区分度不够，检索几乎看不出效果。
- 向量化用本地句向量模型，不需要额外 API Key；对话模型仍用支持工具调用的型号。

## 实操流程

1. 把领域文档放进一个目录，确认数量与体量：

   ```bash
   mkdir -p docs/
   ls -la docs/*.md
   ```

   再把它们读成带来源标记的文档对象，后面每一步都靠这个 `docs` 变量往下传，`metadata["source"]` 则用于在检索结果里标出内容来自哪一篇：

   ```python
   from pathlib import Path
   from langchain_core.documents import Document

   docs_dir = Path("docs")
   docs = [Document(page_content=p.read_text(encoding="utf-8"),
                    metadata={"source": p.name})
           for p in sorted(docs_dir.glob("*.md"))]
   print("actual_docs:", len(docs))
   ```

2. 装切分与向量化依赖：

   ```bash
   pip install langchain-text-splitters langchain-huggingface sentence-transformers --quiet
   ```

   句向量库体积较大，且首次加载模型还会从网络下载几十 MB 权重，预留时间与网络。

3. 切分文档。整篇太长会让语义被平均掉、检索精度差，切小后每片聚焦一个话题：

   ```python
   # step2_rag_split.py
   from langchain_text_splitters import RecursiveCharacterTextSplitter

   splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
   doc_splits = splitter.split_documents(docs)
   print("actual_docs:", len(docs), "actual_chunks:", len(doc_splits))
   ```

   `chunk_size=500` 对千字左右的文档正好切成一话题一片；`chunk_overlap=50` 让相邻片重叠，防止一句完整信息被切断在边界上。文档更长、话题更密时把片长调大。这个切分器优先按段落切，切不动再按换行、句号、空格逐级回退，落刀点尽量在自然语义边界。

4. 向量化入库并包成检索器：

   ```python
   # step3_rag_vectorstore.py
   from langchain_huggingface import HuggingFaceEmbeddings
   from langchain_core.vectorstores import InMemoryVectorStore

   embeddings = HuggingFaceEmbeddings(
       model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
   vectorstore = InMemoryVectorStore.from_documents(doc_splits, embeddings)
   retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

   for d in retriever.invoke("退款需要多久到账？"):
       print(d.metadata["source"])
   ```

   `k=3` 表示每次返回最相关的三片。**中文知识库直接选多语言或中文专用模型**（如上面这个多语言模型、或中文专用的句向量模型）；英文优化的轻量模型处理中文时相似度排序会明显偏，实测同一批中文查询它有两个返回了不相关文档、多语言模型三个全对。换模型只改 `model_name` 一行再重建向量库，检索器、工具、Agent 全不用动。

5. 用 `@tool` 把检索器包成工具，文档字符串按你的知识库领域写准——它是模型判断何时检索的直接依据：

   ```python
   # step4_rag_tool.py
   from langchain_core.tools import tool

   @tool
   def search_docs(query: str) -> str:
       """搜索电商平台知识库，获取关于订单、退款、物流、账号、支付、售后等问题的答案。"""
       docs = retriever.invoke(query)
       return "\n\n".join(f"[来源: {d.metadata['source']}]\n{d.page_content}" for d in docs)
   ```

6. 组装 Agent 并观察自主检索：

   ```python
   # step5_rag_agent_simple.py
   from langchain.agents import create_agent

   agent = create_agent(model="deepseek:deepseek-chat", tools=[search_docs])
   result = agent.invoke({"messages": [{"role": "user",
       "content": "退款审核通过后，用微信支付的订单多久到账？"}]})
   for i, m in enumerate(result["messages"]):
       print(i, type(m).__name__, getattr(m, "tool_calls", None))
   ```

   ```bash
   python step5_rag_agent_simple.py
   ```

   预期消息流明显长于单工具问答：模型可能连续发起多次检索，每次的查询串都不一样（换一组关键词重查），直到它认为拿到了够用的内容再作答。这就是自主检索区别于写死流程的地方。

7. 换业务只改文档目录一行，切分、向量化、入库、工具封装、Agent 组装全不变：

   ```python
   # step7_rag_reuse.py
   docs_dir = Path("new_docs")     # 换成你的文档目录
   ```

## 校验回路

1. **检索验证**：先单独跑 `retriever.invoke("你的领域问题")`，确认返回片段确实来自相关文档。全是不相关的，多半是向量化模型与语言不匹配，回第 4 步换多语言模型。
2. **自主检索验证**：组装后提一个必须查知识库才答得出的问题，检查消息流里出现检索工具的调用与对应的工具结果。
3. **换知识库验证**：换一个目录重跑，确认只改一行、新领域问题被正确作答。

## 常见陷阱

- **中文知识库用英文优化的向量化模型**：检索排序会偏，返回的「最相关三篇」里混进明显不相干的文档。向量化模型选型是这条链路最重要的工程决策，直接决定能不能找对内容。
- **在 macOS 外接磁盘上导入向量化依赖报 `UnicodeDecodeError`**：外接磁盘会生成大量 `._` 开头的资源分叉文件，依赖库扫描目录时按 UTF-8 解码它们就会报错。清理即可恢复：
  ```bash
  find .venv/lib/python3.13/site-packages/transformers -name "._*" -type f -delete
  find docs/ -name "._*" -type f -delete
  ```
- **工具文档字符串写得笼统**：它决定工具在边界问题上被不被调用。完全无关的问题（天气、写诗）模型会直接不调工具、用自身知识回答；措辞含糊时沾点边的问题会误触检索。按你的知识库领域写准描述，误触会明显减少。
- **默认检索一定能找对、找不到就没事**：检索未命中不会让 Agent 崩溃，它会退回用模型自身知识兜底——而这个兜底不可控，用户会以为答案来自知识库。要把知识边界守住，加质量门控（见 grading-retrieved-documents）。
- **把内存向量库当生产方案**：它把向量存在进程内存里，进程一退就没了，每次启动都要重新向量化全部文档。上生产要换持久化向量库。
