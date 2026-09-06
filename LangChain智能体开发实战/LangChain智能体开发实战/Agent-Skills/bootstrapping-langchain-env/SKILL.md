---
name: bootstrapping-langchain-env
description: 在一台干净机器上从零装好 LangChain v1 生态、配好大模型凭证，并跑通第一个 create_agent 工具调用循环示例。Use when 需要初始化 LangChain 开发环境、排查 Python 版本不达标、pip 装完不确定装到哪个版本、模型不发起工具调用这类环境层故障时。涵盖 Python 版本核对、虚拟环境隔离、分层包安装、版本核验、API Key 安全注入、首个示例验收；不含 Agent 的写法与参数体系（见 building-tool-calling-agent）。
allowed-tools: Bash(python:*), Bash(python3:*), Bash(pip:*), Bash(source:*)
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#1、环境基线检测
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、创建并激活虚拟环境
  - experiments/langchain/stage-1-bootstrap/handbook.md#1、安装核心三件套 + DeepSeek 提供方包
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、核验已装版本
  - experiments/langchain/stage-1-bootstrap/handbook.md#3、配置 DeepSeek API Key
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、运行与结果解读
  - experiments/langchain/stage-1-bootstrap/handbook.md#3、模型选型说明
---

## 能力目标

把一台干净机器变成可用的 LangChain v1 开发环境：Python 版本达标、依赖隔离在虚拟环境里、主框架与编排运行时与模型提供方包装齐、凭证注入且不泄漏，最后运行一个最小示例、在终端看到一条完整的工具调用循环消息流。

## 前置

- LangChain v1 是纯 Python 框架，不需要 GPU 与大内存，本机即可跑。
- 需要一个支持工具调用的模型凭证。本流程用 DeepSeek，凭证是 `DEEPSEEK_API_KEY`。
- 术语：提供方集成包指对接某一家模型服务商的适配包（如 `langchain-deepseek`）；工具调用循环指模型在一次任务里自主决定调用外部函数、读结果、再决定下一步。

## 实操流程

1. 核对本机可用的 Python 解释器版本。LangChain v1 要求 Python 3.10 及以上，这是后续所有步骤的前提：

   ```bash
   python3 --version
   ```

   输出 ≥3.10 就直接用 `python3` 建环境，进第 2 步。不达标（macOS 系统自带的 `/usr/bin/python3` 常年停在 3.9.6）则先找一个达标解释器，记下它的绝对路径：

   ```bash
   ls /opt/homebrew/bin/python3.1*      # macOS 上 Homebrew 装的高版本解释器
   /opt/homebrew/bin/python3.13 --version
   ```

   多数 Linux 发行版与新装的 Windows 自带 Python 已 ≥3.10，走前一条即可。

2. 用达标的解释器创建虚拟环境并激活。默认解释器不达标时必须写绝对路径，不能用 `python3`：

   ```bash
   python3 -m venv .venv                          # 默认解释器已达标时
   # /opt/homebrew/bin/python3.13 -m venv .venv   # 默认解释器不达标时改用绝对路径
   source .venv/bin/activate
   python --version
   python -m pip install --quiet --upgrade pip
   ```

   Windows 上激活命令是 `.venv\Scripts\activate`。激活后终端里的 `python` 与 `pip` 都指向 `.venv` 内的解释器。

3. 一条命令装齐分层生态——主框架、编排运行时、模型提供方包：

   ```bash
   pip install -U langchain langgraph langchain-deepseek
   ```

   实测拉齐的核心版本为 langchain 1.3.2、langchain-core 1.4.0、langgraph 1.2.2、langchain-deepseek 1.0.1，并连带装上 langchain-openai 1.2.2 与 openai 2.38.0——DeepSeek 走 OpenAI 兼容协议，其集成包复用 OpenAI 客户端的底层实现，这是预期行为。

4. 显式核验每个包的真实安装版本，不要只看安装日志：

   ```bash
   python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek','langchain-openai','openai']]"
   ```

   统一用 `importlib.metadata.version`，它从安装元数据读版本，对任意已装包都适用。

5. 注入模型凭证，全程不回显明文：

   ```bash
   export DEEPSEEK_API_KEY=$(python -c "import yaml;print(yaml.safe_load(open('/path/to/credentials.yaml'))['api_keys']['deepseek']['key'])")
   echo "DEEPSEEK_API_KEY = ${DEEPSEEK_API_KEY:0:3}***(长度 ${#DEEPSEEK_API_KEY}，已脱敏)"
   ```

   注入与验证分两步：注入步不留痕、验证步只打印前 3 个字符与长度。

6. 写一个最小示例 `create_agent_demo.py` 并运行，验证工具调用循环闭环：

   ```python
   from langchain.agents import create_agent

   def get_weather(city: str) -> str:
       """Get weather for a given city."""
       return f"It's always sunny in {city}!"

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[get_weather],
       system_prompt="You are a helpful assistant",
   )
   result = agent.invoke(
       {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
   )
   for m in result["messages"]:
       print(type(m).__name__, getattr(m, "tool_calls", None) or m.content)
   ```

   ```bash
   python create_agent_demo.py
   ```

   `model` 用 `提供方:模型名` 字符串格式；工具函数的文档字符串是模型判断何时调用它的依据，不能省。

## 校验回路

- 激活后 `python --version` 显示 ≥3.10 的版本，且 `which python` 指向 `.venv`。
- 版本核验命令六个包全部打印出版本号、无 ImportError。
- 凭证验证行显示脱敏前缀与长度，明文不出现在终端与截图里。
- 示例运行输出恰好四条消息，依次是 HumanMessage、带 `tool_calls` 的 AIMessage、ToolMessage、最终 AIMessage；最终回答复用了工具返回的措辞。看到这四条即闭环成立，可以进入 Agent 开发。

## 常见陷阱

- **直接用系统 `python3` 建虚拟环境**：macOS 上大概率是 3.9.6，装包阶段才因版本约束失败。建环境前先核对，必要时写解释器绝对路径。
- **查 langgraph 版本用 `__version__`**：`import langgraph; langgraph.__version__` 会报 `AttributeError: module 'langgraph' has no attribute '__version__'`——langgraph 顶层模块没有定义这个属性。一律改用 `importlib.metadata.version("langgraph")`。
- **满屏 `WARNING: Ignoring invalid distribution -pip ...`**：是先前安装中断在 `site-packages` 留下的 `~` 前缀残留目录导致的噪音，不阻塞安装。介意就清理：
  ```bash
  find ".venv/lib/python3.13/site-packages" -maxdepth 1 -name '~*' -exec rm -rf {} +
  ```
- **选了不支持工具调用的模型**：`deepseek-reasoner` 不支持工具调用与结构化输出，用它跑示例模型不会发出 `tool_calls`、循环走不通。工具调用场景必须用 `deepseek-chat`；换其他厂商模型前先确认该型号支持 function calling。
