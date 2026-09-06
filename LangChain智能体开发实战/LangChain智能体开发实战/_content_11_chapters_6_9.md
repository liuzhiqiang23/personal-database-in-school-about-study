# B 部分 · 课件逐节全量（第 6-9 章）

本部分按学习顺序精炼第 6-9 章课件，每章含「本质 / 关键知识点 / 关键命令与代码 / 关键坑」。

## 第6章 人在回路（Human-in-the-Loop）：危险动作前暂停等人审批

### 本质
用 LangGraph 的中断机制让 Agent 在执行到关键节点时「暂停」，把状态和动作选项交给人来审批，等人工给出「继续 / 改参 / 拒绝」的命令后再恢复执行。危险动作（真实转账、发出不可撤回的邮件、删除数据）必须先经人确认，不能由模型擅自执行。

### 关键知识点
- **为什么需要 HITL**：Agent 在大模型驱动下会「自以为能直接行动」，但有些动作一旦执行不可撤回。HITL 让机器对「是否可以发动」这个终局决定保持敬畏，在危险边缘加一道人工闸门。
- **interrupt 函数**：from langgraph.types import interrupt。调用后图在这一点暂停执行，把 state 快照存进 checkpointer（这解释了为什么 HITL 与记忆用的 checkpointer 是同一块基础设施——它们共享了「保存/恢复」的执行模型）。
- **execution interrupt 只发生一次**：interrupt 一被激活，Agent 运行被冻结，图停在那个节点，等待人工。注意 interrupt 的调用位置是「即将执行危险动作之前」。
- **thread_id 在 HITL 里是「取回一次中断会话的钥匙」**：没有 checkpointer 的持久化记忆，HITL 也无法工作——HITL 依赖 checkpointer 存档状态。
- **break 参数列表是选项 + 上下文展示**：一份审批清单（如 proceed/regenerate/abort），再加「当前要被批准的动作内容」，让每个选项含义一目了然。只有 thread_id 和 info 能给出决策所需的上下文。
- **触发审批的运行时入口**：agent.aget_state() 会在中断点上「读走一个大状态快照」，await 后快照里有 tasks 和一个 details 字典——details 里能看到「pending approve」的值（也就是人工即将裁决的内容）、来源 state 值、下一步处理线程（resume 相关的任务描述）。
- **命令式恢复（Command）**：用户判断后通过 Command(resume=...) 恢复图执行。这个「resume」就是人工裁决的代码化表达。
- **Command 格式（图解）**：`Command(resume=Goto)`，把 resume 参数从「单值」升级为「多个字段」的复杂对象时，就是「Command 里带 State 更新」：`Command(resume={"approve": True, "note": "..."})`——既能 resume，又能用 update 字段同时更新 state。
- **core graph 与「哪里插 interrupt」可以完全分离**：插入 interrupt 会同时给图加一条「边」，不能简单传个参数就得——这套 interrupt 逻辑必须在建图的时候声明。
- **graph.add_command 的三种去向**：回复终点 END、一个常驻 resume 节点 re_censor、一个本 batch 特有的 approved_node。三者在此都是「终」字族节点。注意图里是「两个不同优先级」——把 gating 逻辑（外层判定）从中（也就是「要不要触发 interrupt」）与「触发后交给谁继续」分开，防止决策被漫游到无关方向。

### 关键命令与代码
```python
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
# 在危险动作前插入 interrupt
def gate_censored_text(state, ...):
    if not censor_request:
        return {"censored_request": state["original_request"]}
    decision = interrupt(
        "Censor this request?",
        current_request=state["current_request"],
        approve=...,
    )
```
### 关键坑/注意
- HITL 依赖 checkpointer 持久化，缺了 thread_id 无法恢复会话。
- interrupt 是「暂停不是终止」，恢复必须走 Command(resume=...) 并显式给出裁决值。
- interrupt 逻辑必须在建图时声明，无法运行时临时插入。

---

## 第7章 可观测性：接入 Langfuse 看清每一步调用

### 本质
用 Langfuse（开源的 LLM 可观测平台）给 Agent 的每次调用打上全程追踪：从哪个 prompt、传到哪个模型、模型返回什么、调了哪些工具、每一步花费多少 token 和成本。开发时靠它调试 Agent「为什么这么想」，上线后靠它排查线上问题。

### 关键知识点
- **Langfuse 是双端架构**：社区版（自建 host）走 GitHub 仓库 + Docker compose，或直接用官方 Cloud。默认记录所有 LLM 调用的 trace。三个核心组件：traces（一次会话/请求的完整调用链）、spans（trace 内部的子操作，如某一步 model 调用）、observations（含 generation/event，记 token 用量）。
- **接入方式有三种**：①LangChain callback（最常用，create_agent 里配 callback 自动埋点）；②Langfuse SDK 显式 pack；③OpenTelemetry 手动（更底层、更重）。教程主推 callback 方案。
- **关键配置**：Langfuse 前端 UI 端口（默认 3000）、写路径 /public，POST /api/public/trace 写 trace、GET /api/public/traces/{id} 读 trace。模型与交互靠 LANGFUSE_* 环境变量驱动：
  - LANGFUSE_PUBLIC_KEY（连接公钥）、LANGFUSE_SECRET_KEY（连接私钥）、LANGFUSE_HOST（自建 host 或 cloud 地址）。
  - 三项都配齐才认为是「启用」。默认 Cloud 是 https://cloud.langfuse.com。
- **Token 计数**：langfuse 默认按 model 的 pricing 表推 token，走 LANGFUSE_BASE_URL 时按自建的 tokenizer 处理，手动传 metadata 里带 token 用量的信息用于统计。
- **trace 的层次是「对话」**：trace 之上 user id 聚合、trace 之间 sorted 为 threads/ordered。给 Agent 设 trace 级别「traces=一次会话」是 LangChain 的默认。
- **provider 兼容**：langfuse 支持 OpenAI、Anthropic、DeepSeek…… 各家 model 的 tokenizer。要在 UI 看 token 计数，需 provider 名称能对上 langfuse 的 model 表。

### 关键命令与代码
```bash
# 本地自建 Langfuse（Docker）
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose -f docker-compose.dev.yml up -d
# 或官方一行
curl https://... | bash
```
```python
# 用 callback 接入（create_agent 配 callback）
from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler(
    public_key="...",
    secret_key="...",
    host="https://cloud.langfuse.com",  # 自建则填 LANGFUSE_HOST
)
agent = create_agent(model="deepseek:deepseek-chat", tools=[...],
                     callbacks=[langfuse_handler])
result = agent.invoke({"messages": [...]},
                      config={"metadata": {"user_id": "u1"}})
```

### 关键坑/注意
- 忘配 LANGFUSE_SECRET_KEY（只配了公钥）会「能建 UI 但追踪不上」，务必三项齐配。
- 自建 host 的 token 计数依赖本机 tokenizer 与 model pricing 表，用云版省心。
- 想在 UI 里看到 token cost，需 provider/model 名称能与 langfuse 表对上。

---

## 第8章 Agentic RAG：让 Agent 自己决定何时检索

### 本质
把传统 RAG 的「固定流程」（先检索、后生成）改成「由 Agent 决定」：先看问题是否需要外部资料，需要 → 检索 → 由检索质量（grader）判定是否需要再检 / 调整查询；不需要 → 直接生成。让检索成为 Agent 的一个可选动作而非必经动作。

### 关键知识点
- **传统 RAG 的局限**：一刀切「先切块 → 向量化 → 检索 → 拼 prompt → 生成」，对「不需要外部资料的事实问答」也强行检索，浪费且可能引入噪音。
- **Agentic RAG 三要素**：①检索工具（knowledge_retrieval，用向量库+embedding）；②Grader（retrieval_grader，判断检索结果与问题相关性）；③路由（由模型决定「要不要检索」）。检索评分 grader 本身也可由 LLM 承担。
- **检索循环**：query → retrieve → grade → 若不合格可改查询 / 多轮再检 → 合格才进生成。
- **retrieval 工具用 create_agent 的 tools 挂载**，本质就是复用第 2 章的工具调用循环；grader 用结构化输出（复用第 3 章 response_format）。
- **chunking**：切块策略（按固定长度、按章节、按语义段落），块大小与重叠影响检索命中率。embedding 用向量库（Chroma/FAISS 等）存检索。相似度检索、MMR / hybrid（BM25 混合）可调。
- **何时用 Agentic RAG**：建知识库问答、票据助手、企业资料问答；明确「并不总需要检索」。

### 关键命令与代码
```python
from langchain.agents import create_agent
# 检索工具
def knowledge_retrieval(query: str) -> str:
    """从知识库检索与 query 最相关的内容。"""
    return vs.similarity_search(query, k=3)
# grader 结构化输出
class Grade(BaseModel):
    relevant: bool = Field(description="检索结果是否与用户问题相关")
# 组装：给 Agent 挂检索工具
agent = create_agent(model="deepseek:deepseek-chat",
                     tools=[knowledge_retrieval], ...)
```

### 关键坑/注意
- 检索结果「不合格」时别直接进生成，应走 grader 判断后决定是否重检/改查询。
- embedding 模型要与切块粒度匹配，否则检索命中率低。
- hybrid（向量+BM25）在专有名词/编号查询场景更稳。

---

## 第9章 DeepAgents：扛住十几步以上的长链路任务

### 本质
DeepAgents 是一个专门跑「长程（long-horizon）」任务的脚手架：把一个几十甚至上百步的大任务自动拆成可管理的子任务、做成计划（todo 清单），必要时把单个子任务「下放」给子代理（subagent）并行/独立处理，并通过虚拟文件系统让长程上下文不至于被撑爆。

### 关键知识点
- **长程为什么难**：十几步以上的任务，靠一个 Agent 一路做下来，上下文会越积越多（每一步的中间结果都占 token），且单个 Agent 容易「迷失在长链里」。
- **DeepAgents 三板斧**：①todo 规划（todo-planning）——把大任务拆成子进度，Agent 会迭代更新计划；②子代理委派（subagent delegation）——把独立子任务交给 subagent，隔离上下文、可并行；③虚拟文件系统（virtual filesystem）——用「虚拟文件」承载中间产物/资料，避免把所有内容都塞进对话上下文，是一种「上下文工程」。
- **deepagents 包**：pip install deepagents，0.6.7 版本要求 Python ≥3.11 且 <4.0。deepagents 提供的 harness 与 create_agent 兼容，能复用工具调用循环。
- **todo 机制**：Agent 维护一个 todo 列表，每步更新、标记完成；可 TodoListMiddleware 配合（第 4 章 middleware 内置项）。
- **何时用**：任务固有步骤 ≥10 步、需要阶段性产出、需要隔离上下文的长链路场景。

### 关键命令与代码
```bash
pip install deepagents   # 需 Python>=3.11, <4.0
```
```python
from deepagents import deepagents  # 或对应 harness
# 用 deepagents 的 harness 包装 create_agent
agent = deepagents(model="deepseek:deepseek-chat", tools=[...])
```

### 关键坑/注意
- Python 版本要 ≥3.11 且 <4.0，过低/过高装不上或运行异常。
- 长程任务里 subagent 与主 agent 共享 checkpointer/thread 体系，务必带上 thread_id 才能恢复。
- todo 计划要随进度「迭代更新」，别一次写完就不再改。
