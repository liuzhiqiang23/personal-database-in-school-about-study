---
concept: langchain-package-stack
one_liner: LangChain 是分层发布的多包生态（主框架、编排运行时、提供方集成包），按需安装、版本各自迭代，核验版本统一用 importlib.metadata
stage_span: [stage-1, stage-2]
prerequisites: [python-env-and-venv-setup]
related: [deepseek-provider-integration, create-agent-entry, local-environment-traps]
applications: [create-agent-entry, deepagents-harness, embedding-and-vectorstore]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#一、LangChain 是什么:项目定位与本节目标
  - experiments/langchain/stage-1-bootstrap/handbook.md#三、安装 LangChain 生态与凭证配置
  - experiments/langchain/stage-1-bootstrap/handbook.md#1、安装核心三件套 + DeepSeek 提供方包
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、核验已装版本
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、确认运行环境
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、确认 middleware 模块就位
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、安装 deepagents 并确认版本
---

## 是什么

LangChain 是面向智能体工程的开源框架，目标是让模型不只"回答一句话"，而是能在一个循环中自主调用外部工具、读取结果、再决定下一步。它的实现不是一个单体包，而是一组分层发布的独立 PyPI 包，分工清晰：**主框架 `langchain` 提供 `create_agent` 等上层 API，`langgraph` 提供底层图执行运行时**——前者负责声明式组装，后者负责状态与循环调度；`langchain-core` 提供消息类型等基础设施；各家模型的适配包（如 `langchain-deepseek`）单独发布。分层的好处是按需安装、各自独立迭代。

这个分层结构会在后续所有能力上反复显形：`create_agent` 返回的是 `langgraph.graph.state.CompiledStateGraph`；记忆用的 `InMemorySaver` 来自 `langgraph.checkpoint.memory`；中间件全部集中在 `langchain.agents.middleware`；检索增强的向量库来自 `langchain_core.vectorstores`。搞清哪个能力属于哪个包，是排查导入错误的前提。

## 怎么用

安装主框架、运行时与一个提供方集成包，一条命令即可拉齐整条依赖树：

```bash
pip install -U langchain langgraph langchain-deepseek
```

安装日志一闪而过，稳妥做法是显式读取每个包的真实安装版本：

```bash
python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek','langchain-openai','openai']]"
```

按需扩展的包在用到时再装，各自独立：

```bash
pip install langgraph-checkpoint-sqlite        # 跨进程持久化记忆
pip install langchain-text-splitters langchain-huggingface sentence-transformers   # 文档切分与向量化
pip install langfuse                            # 可观测上报
pip install deepagents                          # 长程智能体脚手架
```

## 关键细节与参数

- 实测版本基线：`langchain 1.3.2`、`langchain-core 1.4.0`、`langgraph 1.2.2`、`langchain-deepseek 1.0.1`、`langchain-openai 1.2.2`、`openai 2.38.0`，Python 3.13.13。这套基线贯穿全部实操场景。
- 装 `langchain-deepseek` 会连带拉入 `langchain-openai` 与 `openai`——因为 DeepSeek 走 OpenAI 兼容协议，其集成包复用了 OpenAI 客户端的底层实现。
- 中间件能力全部集中在 `langchain.agents.middleware` 一个模块，基类的真实路径是 `langchain.agents.middleware.types.AgentMiddleware`。
- `deepagents` 是独立 PyPI 包，安装时会自动带上 `anthropic`、`langchain-anthropic`、`langchain-google-genai` 等依赖；实测版本 0.6.7，处于 pre-1.0 阶段，接口尚未冻结。
- 这是一个高频迭代的项目，安装时应以实测版本为准，而不是凭印象锁定版本号。

## 常见陷阱

- **用 `__version__` 查版本**：`import langgraph; print(langgraph.__version__)` 会报 `AttributeError: module 'langgraph' has no attribute '__version__'`——langgraph 顶层模块并未定义该属性（`langchain` 与 `langchain_core` 有）。通用可靠的做法是 `importlib.metadata.version("langgraph")`，它从安装元数据读版本，对任意已装包都适用。
- **假设某能力在主框架里**：记忆（checkpointer）、人在回路的 `interrupt` / `Command` 都属于 `langgraph` 而非 `langchain`，找不到时先确认包归属再怀疑版本。
- **pre-1.0 包按记忆写参数**：`deepagents` 的工具名与参数名在 pre-1.0 阶段可能调整，落地前应对照当时的官方 reference 复核，重心放在不易过期的设计理念上。
