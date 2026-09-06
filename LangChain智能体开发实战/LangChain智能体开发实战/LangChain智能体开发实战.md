# LangChain智能体开发实战


---

## LangChain v1 从零到一跑通实操手册

本手册记录 LangChain v1 在一台 Mac mini（M4 芯片、macOS 26.4.1、arm64 架构）上从零到一跑通的完整过程：检测并解决 Python 版本不达标、建立隔离的虚拟环境、安装 LangChain 分层生态、配置大模型凭证，最终运行官方 `create_agent` 最小示例,亲眼看到一次完整的「工具调用循环」闭环。

全流程基于真实执行,所有命令、版本号、终端输出均来自实测,可按本手册逐步复现。

---

### 一、LangChain 是什么:项目定位与本节目标

LangChain 是一个面向智能体工程（agent engineering）的开源框架,用于构建基于大语言模型的可靠应用。它的目标是让模型不只是「回答一句话」,而是能够在一个循环中自主调用外部工具、读取结果、再决定下一步,直到完成一个完整任务。

LangChain 的官方文档站点与代码仓库分别是:

- 官方文档:https://docs.langchain.com
- GitHub 仓库:https://github.com/langchain-ai/langchain

打开官方文档首页,可以看到 LangChain 把自己定位为「the platform for agent engineering」(智能体工程平台),并列出了围绕智能体生命周期的几个核心能力板块,例如可观测性(Observability)、提示词工程(Prompt Engineering)、部署(Deployment)等。其中 LangSmith 是配套的运行追踪与评估平台,本阶段不展开。

![LangChain 官方文档首页](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step1-official-docs.png)

代码仓库主页可以进一步确认这个项目的活跃度与版本基线。仓库右侧的 Releases 区域显示当前发布版本为 `langchain-core 1.4.0`,About 区域用一组标签概括了它的关键词:`python`、`agents`、`llm`、`langchain` 等。这是一个持续高频迭代的项目,因此安装时务必以「实测版本」为准,而不是凭印象。

![LangChain GitHub 仓库主页](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step1-official-github.png)

> 关于英文术语:本手册中,Agent(智能体)指能够自主调用工具完成任务的程序实体;tool calling(工具调用)指模型在推理过程中决定调用某个外部函数并使用其返回结果的机制;provider(提供方/集成包)指对接某一家大模型服务商的适配包。这些概念会在后文实操中逐一对应到具体代码。

本阶段的目标是跑通最小闭环,具体包含四件事:

- 装好 LangChain 主框架、编排运行时,以及一个大模型提供方集成包
- 配置好可用的大模型 API Key
- 运行官方 `create_agent` 最小示例
- 在终端中看到一条完整的工具调用循环消息流

实测使用的核心版本为 langchain 1.3.2、langchain-core 1.4.0、langgraph 1.2.2。下面从环境准备开始。

---

### 二、环境准备:从 Python 版本到虚拟环境

LangChain v1 对 Python 版本有硬性要求。官方 install 文档([install 文档](https://docs.langchain.com/oss/python/langchain/install))明确写明 `Requires Python 3.10+`(要求 Python 3.10 及以上)。这一条是后续所有步骤的前提,因此第一步不是装包,而是核对本机环境是否达标。

#### 1、环境基线检测

LangChain 是纯 Python 框架,不依赖 GPU,也没有大内存要求,普通笔记本或台式机本机即可运行。需要确认的只有两点:操作系统/架构,以及本机可用的 Python 解释器版本。

```bash
echo "OS: $(sw_vers -productName) $(sw_vers -productVersion) ($(uname -m))"
echo "系统 python3 = $(python3 --version)"
echo "brew python3.13 = $(/opt/homebrew/bin/python3.13 --version)"
echo "uv = $(uv --version)"
```

![环境基线检测](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step1-env-baseline.png)

终端输出如下:

```
OS: macOS 26.4.1 (arm64)
系统 python3 = Python 3.9.6 [需 3.10+ 不达标]
brew python3.13 = Python 3.13.13 [达标]
uv = uv 0.11.1 (Homebrew 2026-03-24 aarch64-apple-darwin)
```

这里出现了第一个真实拦路点:macOS 系统自带的 `/usr/bin/python3` 是 **3.9.6**,低于 LangChain v1 要求的 3.10+。如果直接用系统解释器去建虚拟环境再装包,会因为版本约束而失败。所幸本机另外通过 Homebrew 安装了 `python3.13`(版本 3.13.13),满足要求,后续就用它来建环境。

> 这是一个 macOS 上很容易踩中的坑:系统自带的 Python 往往偏旧。多数 Linux 发行版与新安装的 Windows,其 Python 通常已是 3.10 及以上,可以直接使用;但在 macOS 上要先确认,必要时显式指定一个更高版本的解释器。本机除了 python3.13,还装有 python3.12、python3.11,任选一个 ≥3.10 的版本即可。

#### 2、创建并激活虚拟环境

虚拟环境(virtual environment)的作用是把本项目的依赖与系统全局环境隔离开,避免包版本互相污染。这里在项目根目录创建一个名为 `.venv` 的虚拟环境。关键在于:必须用满足版本要求的 `python3.13` 来创建,而不能用默认的 `python3`(那是不达标的 3.9)。

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --quiet --upgrade pip
```

四条命令依次完成:用 python3.13 创建 `.venv`、激活该环境、确认激活后的 Python 版本、把环境内的 pip 升级到最新。

![创建并激活虚拟环境](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step2-venv-create.png)

激活后 `python --version` 显示 `Python 3.13.13`,pip 升级到了 `26.1.1`。从这一刻起,当前终端里的 `python` 与 `pip` 都指向 `.venv` 内的 3.13 解释器,环境就位。

> 跨平台对照:若所在系统的 Python 已经 ≥3.10,可以直接 `python3 -m venv .venv`;Windows 上的激活命令为 `.venv\Scripts\activate`。本机因为系统 Python 偏旧,才改用 Homebrew 中 `python3.13` 的绝对路径来建环境。

观察上面的截图会发现,pip 升级过程中夹带了多条 `WARNING: Ignoring invalid distribution -pip ...` 警告。这是一个无害但容易让人困惑的现象:本次实验的工作空间位于外置 SSD 上,先前某次安装中断后,在 `site-packages` 目录里留下了以 `~`(pip 显示为 `-`)为前缀的临时残留目录。pip 每次都会报告「忽略无效分发」并跳过它们,然后照常完成工作。它**不阻塞**安装,所有包都能正确装上、Demo 也能正常跑通,仅仅是输出噪音。如果介意,可在重装前清理:

```bash
find ".venv/lib/python3.13/site-packages" -maxdepth 1 -name '~*' -exec rm -rf {} +
```

---

### 三、安装 LangChain 生态与凭证配置

LangChain 采用分层包结构:主框架、编排运行时、各家模型的提供方集成包是分开发布的独立 PyPI 包。这样做的好处是按需安装、各自独立迭代。本节先把需要的包装齐,再核验版本,最后配置大模型凭证。

#### 1、安装核心三件套 + DeepSeek 提供方包

本次需要安装三个包:

- **langchain**(主框架)— https://docs.langchain.com/oss/python/langchain/
- **langgraph**(编排运行时,负责智能体的状态与循环调度)— https://docs.langchain.com/oss/python/langgraph/
- **langchain-deepseek**(DeepSeek 提供方集成包)— https://docs.langchain.com/oss/python/integrations/chat/deepseek

对一个框架/库类项目而言,「部署」本质上就是把这些包装进虚拟环境。一条命令即可:

```bash
pip install -U langchain langgraph langchain-deepseek
```

![安装 langchain + langgraph + langchain-deepseek](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step2-pip-install.png)

截图是安装过程的尾部(依旧能看到外置 SSD 残留带来的 `Ignoring invalid distribution` 警告,同样非阻塞),末尾的 `Successfully installed ...` 一次性拉齐了整个依赖树。实测装上的核心包版本为:

```
langchain-1.3.2  langchain-core-1.4.0  langgraph-1.2.2
langchain-deepseek-1.0.1  langchain-openai-1.2.2  openai-2.38.0
```

这里有一个值得注意的细节:安装 `langchain-deepseek` 会连带拉入 `langchain-openai` 和 `openai` 两个包。原因是 DeepSeek 的接口走的是 OpenAI 兼容协议,其集成包复用了 OpenAI 客户端的底层实现。一条命令就拉齐了整条分层生态,无需逐包手动解析依赖。

#### 2、核验已装版本

安装日志一闪而过,稳妥的做法是显式读取每个包的真实安装版本,确认全部可导入、版本无误。查询包版本推荐统一使用标准库 `importlib.metadata` 的 `version` 函数:

```bash
python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek','langchain-openai','openai']]"
```

![核验六个包的安装版本](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step3-verify-versions.png)

输出与安装日志完全一致:

```
langchain            = 1.3.2
langchain-core       = 1.4.0
langgraph            = 1.2.2
langchain-deepseek   = 1.0.1
langchain-openai     = 1.2.2
openai               = 2.38.0
```

六个包全部可导入、版本无误,部署核验通过。

> 这里要专门提一个坑。查版本时一种常见写法是 `import langgraph; print(langgraph.__version__)`,但对 langgraph 执行会报错:`AttributeError: module 'langgraph' has no attribute '__version__'`。原因是 langgraph 顶层模块并未定义 `__version__` 属性(langchain 与 langchain_core 有,langgraph 没有)。可靠且通用的做法是改用 `importlib.metadata.version("langgraph")`——它从包的安装元数据里读版本,不依赖包是否自己暴露版本属性,对任意已安装包都适用。

#### 3、配置 DeepSeek API Key

DeepSeek 提供方通过环境变量 `DEEPSEEK_API_KEY` 读取凭证(见 [ChatDeepSeek 集成文档](https://docs.langchain.com/oss/python/integrations/chat/deepseek))。配置凭证时有一条安全原则:全程不在终端回显明文,也不让 Key 出现在任何截图里。

```bash
# 从凭证文件注入环境变量(不回显明文,此步不截图)
export DEEPSEEK_API_KEY=$(python -c "import yaml;print(yaml.safe_load(open('/path/to/credentials.yaml'))['api_keys']['deepseek']['key'])")
# 验证已注入(只显示脱敏前缀与长度)
echo "DEEPSEEK_API_KEY = ${DEEPSEEK_API_KEY:0:3}***(长度 ${#DEEPSEEK_API_KEY},已脱敏)"
```

注入与验证分成两步:注入那一步不截图,验证步只打印 Key 的前 3 个字符加长度,从源头杜绝 Key 泄漏。

![配置 DeepSeek API Key(脱敏)](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step4-config-key.png)

终端显示 `DEEPSEEK_API_KEY = sk-***(长度 35,已脱敏)`,凭证注入成功且无明文泄漏。同一步顺带确认了 Demo 脚本 `create_agent_demo.py`(1234 字节)已经就位。

> 截图中那条 `awk: syntax error` 是用来格式化文件字节数的 awk 命令本身的小语法问题,与凭证配置无关,文件清单仍正确列出了脚本及其大小,不影响后续运行。配置环境变量这一步本身只需关注「Key 是否注入成功、是否脱敏」即可。

---

### 四、跑通第一个 Agent:create_agent 工具调用循环

前面三章把地基打好了:Python 版本达标、虚拟环境隔离、生态包装齐、凭证就位。本章是收口——运行官方 `create_agent` 最小示例,验证 LangChain v1 的核心范式:**模型在一个循环里调用工具,直到任务完成**。

#### 1、Demo 脚本结构

示例直接取自官方 quickstart([create_agent quickstart](https://docs.langchain.com/oss/python/langchain/quickstart)),结构非常精简:定义一个工具函数,用 `create_agent` 组装智能体,再用 `invoke` 提问。

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
```

逐段理解这段代码:

- `get_weather` 是一个普通 Python 函数,但它的**文档字符串(docstring)`"""Get weather for a given city."""` 至关重要**——模型正是通过这段描述来判断「什么时候该调用这个工具」。这里返回值固定写死为「永远晴天」,纯粹为了让结果一眼可辨,真实场景会替换为天气 API 调用。
- `create_agent` 接收三个参数:`model` 指定模型,`tools` 传入可用工具列表,`system_prompt` 给出系统角色设定。
- `model="deepseek:deepseek-chat"` 采用 `提供方:模型名` 的字符串格式。官方 quickstart 按提供方分了多个标签页给出不同型号串(OpenAI、Anthropic 等各异),这里换成了国内可用的 DeepSeek,其余结构与官方示例完全一致。
- `agent.invoke(...)` 以一条用户消息发起调用,返回包含完整消息流的结果。

实际运行的脚本在此基础上额外遍历了返回的消息流,把工具调用循环的每一个环节显式打印出来,便于观察。

#### 2、运行与结果解读

```bash
python create_agent_demo.py
```

![运行 create_agent 最小示例:工具调用循环闭环](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/stage-1--shot--step4-demo-run.png)

终端输出如下:

```
=== 消息流(工具调用循环)===
[HumanMessage] "What's the weather in San Francisco?"
[AIMessage] tool_calls -> [('get_weather', {'city': 'San Francisco'})]
[ToolMessage] "It's always sunny in San Francisco!"
[AIMessage] 'The weather in San Francisco is always sunny! ☀️'

=== 最终回答 ===
The weather in San Francisco is always sunny! ☀️
```

这条消息流就是 LangChain v1 核心闭环的最小实证。它恰好由四条消息组成,完整地走了一遍工具调用循环:

1. **HumanMessage(用户消息)**:用户问「旧金山天气如何」。
2. **AIMessage 带 tool_calls(模型决定调工具)**:模型没有直接回答,而是判断需要查天气,于是发出一次工具调用 `get_weather(city="San Francisco")`。此时这条 AI 消息的文本内容为空,关键信息在 `tool_calls` 字段里。
3. **ToolMessage(工具返回结果)**:`get_weather` 函数被执行,返回 `It's always sunny in San Francisco!`,作为工具消息回填给模型。
4. **AIMessage 最终回答(模型据此作答)**:模型拿到工具结果后,生成最终自然语言回答 `The weather in San Francisco is always sunny! ☀️`。

注意最终回答直接复用了工具返回的「always sunny」措辞,这说明工具结果被正确地喂回了模型、并参与了最终生成——这正是「循环」二字的含义。官方对 Agent 的定义是「a model calling tools in a loop until a given task is complete」(模型在循环中调用工具,直到任务完成),这四条消息就是该定义的最小可见证据。本次 DeepSeek 真实联网完成调用,耗时约 5.6 秒。

#### 3、模型选型说明

这个 Demo 选用 `deepseek-chat` 而非 `deepseek-reasoner`,是一个必须讲清楚的决策点。

ChatDeepSeek 官方文档明确:`deepseek-reasoner` **不支持**工具调用(tool calling)与结构化输出,而 `deepseek-chat` **支持**。本 Demo 的本质就是工具调用循环,因此必须使用 `deepseek-chat`。如果误用 `deepseek-reasoner`,模型不会发出 `tool_calls`,上面那条循环就走不通。

下面把两者在本场景下的差异对照如下:

| 维度 | deepseek-chat | deepseek-reasoner |
| --- | --- | --- |
| 工具调用(tool calling) | 支持 | 不支持 |
| 结构化输出 | 支持 | 不支持 |
| 是否适用本 Demo | 适用(必选) | 不适用 |

使用前提是:已安装 `langchain-deepseek` 包,并已设置 `DEEPSEEK_API_KEY` 环境变量——这两点在第三章均已完成。

---

### 五、本节小结与后续方向

本手册完整走通了 LangChain v1 的从零到一最小闭环:核对并绕过 macOS 系统 Python 3.9 不达标的拦路点(改用 python3.13 建 `.venv`)、一条命令装齐分层生态(langchain 1.3.2 + langgraph 1.2.2 + langchain-deepseek 1.0.1)、安全地配置 DeepSeek 凭证、照官方 quickstart 跑通 `create_agent` + 工具 + `invoke`,并通过一条四步消息流实证了「模型在循环中调用工具」这一核心范式。

过程中沉淀了四个真实可复用的经验点:

- macOS 系统 Python 常偏旧,建虚拟环境前务必核对版本,必要时显式指定高版本解释器。
- 外置 SSD 上的 `Ignoring invalid distribution` 警告是中断残留导致的无害噪音,可忽略或一行清理。
- 查 langgraph 版本不能用 `__version__`,统一用 `importlib.metadata.version`。
- 工具调用循环 Demo 必须用支持 tool calling 的 `deepseek-chat`,而非 `deepseek-reasoner`。

本阶段仅演示了非流式的 `invoke` 调用。围绕 `create_agent` 还有大量内容尚未展开:流式输出 `stream`、基于 `checkpointer + thread_id` 的多轮记忆、Middleware(中间件)系统、结构化输出 `response_format`,以及更底层的 LangGraph `StateGraph` 编排、可观测平台 LangSmith 等。环境已就绪——虚拟环境 `.venv`(Python 3.13.13)与六个核心包均已装好,后续可直接 `source .venv/bin/activate` 接力,从 `create_agent` 的完整参数体系与三种调用方式继续深入。


---

## LangChain create_agent 智能体核心从零到一跑通实操手册

### 一、开篇：用一个订单助手理解 Agent 的「工具调用循环」

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)，官方文档站为 [docs.langchain.com](https://docs.langchain.com/)。在 LangChain v1 中，搭建一个能自主调用工具的智能体（Agent，智能体）的官方入口是 `create_agent`，对应文档页 [docs.langchain.com/oss/python/langchain/agents](https://docs.langchain.com/oss/python/langchain/agents)。

本案例围绕一个具体场景展开：一个订单运营助手。它需要能查订单状态、查物流轨迹、算运费、查库存。这些能力在传统程序里通常写成几个函数，再由开发者用 `if/else` 判断用户意图、决定调用哪个函数。Agent 的不同之处在于：**调用哪个函数、何时调、调几次，由模型自己推理决定**，开发者不再手写分发逻辑。

打个日常的比方：传统程序像一份写死的操作手册，每个分支都得开发者提前规定好；Agent 更像一个收到任务的助理——你只把工具（查订单的系统、查物流的系统、算运费的工具）交给他，再把任务告诉他，至于先查哪个系统、要不要顺手再查另一个，由他自己判断。本案例要做的，就是把这个「助理」搭起来，并把他每一步的判断过程摊开给读者看。

模型自主决策的过程，遵循一个固定的循环，业界称之为 agent loop（智能体循环），本案例统一称「工具调用循环」。它由四步构成：

1. **推理**：模型读到用户问题，判断需要调用哪个工具、传什么参数；
2. **调工具**：框架按模型的决定执行对应函数；
3. **结果喂回**：工具的返回值被重新交给模型；
4. **继续推理直到完成**：模型基于工具结果，要么再调下一个工具，要么生成最终回答。

这套循环正是本案例要让读者亲眼看清的核心。下文按「确认环境 → 定义工具 → 组装 Agent → 运行并观察循环 → 多工具协作 → 换工具复用」的顺序逐步推进，每一步都有真实终端输出佐证。

本案例涉及的关键技术对象有三个：

- **工具函数（tool）**：带类型注解和文档字符串（docstring）的普通 Python 函数，是 Agent 的「能力单元」；
- **`create_agent`**：把「模型 + 工具 + 系统提示词」组装成可执行 Agent 的工厂函数；
- **消息流（messages）**：一次调用返回的消息链，记录了工具调用循环每一步的痕迹，是观察原理的窗口。

---

### 二、准备工作：环境确认与工具定义

#### 1、确认运行环境

本案例沿用既有的 Python 虚拟环境（venv）。运行实操前，先确认环境里的 LangChain 相关包版本就位。激活 venv 后，用 `importlib.metadata.version` 逐个打印关键包版本：

```bash
source .venv/bin/activate
python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek']]"
python --version
```

终端输出确认了版本基线：

![终端输出 langchain=1.3.2 / langchain-core=1.4.0 / langgraph=1.2.2 / Python 3.13.13](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step1-venv-verify.png)

```
langchain            = 1.3.2
langchain-core       = 1.4.0
langgraph            = 1.2.2
langchain-deepseek   = 1.0.1
Python: Python 3.13.13
```

这里有几个版本对应关系值得留意。`create_agent` 是 LangChain v1（即 `langchain` 1.x）引入的官方 API，运行依赖 `langgraph`（底层图执行引擎）和 `langchain-core`（消息类型等基础设施）。`langchain-deepseek` 提供 DeepSeek 模型的接入能力，后文用 `"deepseek:deepseek-chat"` 这种 `provider:model` 写法时正是靠它解析。Python 版本为 3.13.13，满足 LangChain v1 要求的 3.10 及以上。

若读者从零起步、本机尚无此环境，完整路径为：用 `python -m venv .venv` 创建虚拟环境，`source .venv/bin/activate` 激活，再 `pip install langchain langchain-deepseek` 安装核心依赖，最后用上面的版本打印命令验证安装成功。此外需要一个 DeepSeek API Key——在 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取后，通过环境变量注入：`export DEEPSEEK_API_KEY=你的key`。注意模型必须选 `deepseek-chat`（支持工具调用），而非 `deepseek-reasoner`（不支持工具调用）。

#### 2、定义业务工具集

环境就位后，第一件实质工作是定义工具。新建 `tools.py`，写入三个订单运营工具函数。每个函数都遵循同一个规范：**带类型注解、带 docstring、返回字符串**。下面是核心三个工具（外加一个 `query_inventory` 预留给后文的复用实验）：

```python
# tools.py
def query_order(order_id: str) -> str:
    """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
    mock = {"A1001": "已发货 · 预计明天到达"}
    return mock.get(order_id, "未找到该订单")

def track_shipping(order_id: str) -> str:
    """查询指定订单的最新物流轨迹。order_id 是订单编号。"""
    return "2026-05-30 08:00 上海转运中心 → 正在派送中"

def calc_shipping_fee(origin: str, destination: str, weight_kg: float) -> str:
    """计算运费。origin 出发城市，destination 目的城市，weight_kg 包裹重量（公斤）。"""
    fee = round(10 + weight_kg * 3, 1)  # mock：基础费 10 元 + 每公斤 3 元
    return f"从{origin}到{destination}，重量 {weight_kg} kg，预估运费 {fee} 元"

def query_inventory(product_id: str) -> str:
    """查询指定商品的库存数量。product_id 是商品编号，如 P001。"""
    return "库存充足 · 当前 358 件"
```

文件写好后，打印确认四个函数都带 docstring 和类型注解：

```bash
cat tools.py
```

![tools.py 完整内容，4 个函数均含 docstring 和类型注解：query_order / track_shipping / calc_shipping_fee / query_inventory](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step2-tools-py.png)

工具返回的都是 mock（模拟）数据，这是本案例有意的选择。工具调用循环的教学核心是「模型如何自主决定调用」，工具内部查的是真数据库还是返回固定字符串，对循环机制没有影响。用 mock 返回，读者就能把注意力集中在循环本身。

这里最关键的一点是 docstring。它看起来像普通的函数说明，但在 `create_agent` 体系里，**docstring 就是这个工具向模型暴露的「能力描述」**。框架会把所有工具的 docstring 拼成一份能力清单交给模型，模型据此判断「用户这个问题该调哪个工具」。换句话说，docstring 不是写给人看的注释，而是直接参与模型推理的元数据。

#### 3、docstring 为什么不是可选项

很多 Python 教程把 docstring 描述成「良好习惯但非必须」。在 `create_agent` 体系里，这个判断不成立——docstring 是框架的**硬约束**。为了证实这一点，可以做一个对照实验：分别用「有 docstring」和「无 docstring」的工具去组装 Agent，观察差异。

```bash
python ext3_no_docstring_breaks.py
```

有 docstring 的工具正常被调用：

```
实验 A: query_order_with_doc（有 docstring）
被调用的工具: ['query_order_with_doc']
query_order_with_doc 被调用: True
```

而去掉 docstring 的工具，问题不在「模型不会调」，而是 **Agent 根本组装不起来**：

```
实验 B: query_order_no_doc（无 docstring）
Traceback (most recent call last):
  ...
  langchain_core/tools/structured.py
ValueError: Function must have a docstring if description not provided.
```

![有 docstring 工具正常调用，无 docstring 触发 ValueError，create_agent 在组装阶段拒绝注册](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--extension-3-no-docstring.png)

这个报错有两个细节值得讲清楚。其一，错误发生在 **`create_agent()` 组装阶段，而不是 `agent.invoke()` 运行阶段**。也就是说，工具漏写 docstring 的话，程序根本启动不了，问题在编码阶段就暴露，而非等到线上运行才出错——这是「快速失败」（fast fail）的设计。其二，错误信息 `Function must have a docstring if description not provided.` 点明了两条出路：要么给函数写 docstring（最简洁），要么在创建工具时显式传入 `description` 参数。两种方式本质相同，都是为了给模型提供工具描述。

这条经验在真实工程里直接影响 Agent 行为：docstring 写「查询订单状态」还是写「订单查询工具」，会让模型在边界场景下做出不同的调用判断。docstring 的措辞，就是 Agent 选工具的判断依据。

---

### 三、组装 Agent：create_agent 一行成图

#### 1、create_agent 组装与返回对象

工具定义好后，组装 Agent 只需一次 `create_agent` 调用。注意 import 路径——LangChain v1 的官方入口是 `from langchain.agents import create_agent`：

```python
# agent_core.py
from langchain.agents import create_agent
from tools import query_order, track_shipping, calc_shipping_fee

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
)
print("agent 类型:", type(agent))
```

三个参数各有职责：`model` 用 `provider:model` 格式指定底层模型，这里是 DeepSeek 的 `deepseek-chat`；`tools` 是工具函数列表；`system_prompt` 是系统提示词，定义 Agent 的角色和说话风格。运行后打印返回对象的类型：

```bash
python step3_check_agent.py
```

![终端输出：create_agent 返回 CompiledStateGraph（langgraph.graph.state），组装成功](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step3-create-agent.png)

```
agent 类型: <class 'langgraph.graph.state.CompiledStateGraph'>
agent 类名: CompiledStateGraph
agent 模块: langgraph.graph.state
create_agent 成功 - agent 对象就绪
```

返回对象的类型是 `CompiledStateGraph`，来自 `langgraph.graph.state`。这个返回值揭示了 `create_agent` 的本质：它不是简单地「把工具绑到模型上」，而是把「模型 + 工具 + 系统提示词」这份声明式配置**编译成一张可执行的 LangGraph 图**。正因为返回的是编译好的图对象，它天然就拥有 `invoke`（一次性执行）和 `stream`（流式执行）两种调用能力——这两个方法是后文运行 Agent 的入口。

#### 2、system_prompt：控制「怎么说」而非「做什么」

上一步传入的 `system_prompt` 到底改变了什么？用一个对照实验回答：保持工具和问题不变，只换 `system_prompt`，观察 Agent 行为差异。

```bash
python ext4_system_prompt.py
```

```
Prompt A: 标准订单助手（默认）
最终回答: 订单 **A1001** 当前的状态是 **已发货**，预计 **明天到达**。
         需要我帮你查询一下该订单的物流轨迹吗？

Prompt B: 极简风格（只报关键状态，不加解释）
最终回答: 订单 A1001：已发货。

对比总结:
- 两个 agent 调用了相同的工具（tool_calls 不变）
- 但 system_prompt 改变了最终回答的风格和长度
- 工具调用循环本身（agent loop）不受 system_prompt 影响
```

![system_prompt 对比：Prompt A 详细并追问，Prompt B 极简一句话，两者工具调用行为一致](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--extension-4-system-prompt.png)

对比结果清晰：两个 Agent 都调用了 `query_order`，工具调用行为完全一致，但最终回答的风格天差地别。这印证了一条边界：**`system_prompt` 控制模型「怎么说」，不控制「做什么」**。决定调哪个工具的逻辑，由工具的 docstring 加用户问题共同决定，`system_prompt` 不参与这一层。

这个边界在生产中很实用：同一套工具，配「你是热情的客服」可以让回答有温度，配「简洁报告状态，不加解释」可以提高内部工具的效率，配「请同时用中文和英文回答」可以直接控制输出格式。工具调用循环是稳定的核心，`system_prompt` 是可调的外衣。

---

### 四、运行 Agent：看清单工具调用循环

#### 1、invoke 单工具问题

Agent 组装就绪，用 `agent.invoke` 发出第一个问题。`invoke` 接收一个含 `messages` 列表的字典，列表里放一条 `HumanMessage`（用户消息）：

```python
# step4_single_tool.py
from langchain_core.messages import HumanMessage

result = agent.invoke({"messages": [HumanMessage(content="订单 A1001 是什么状态？")]})

for i, msg in enumerate(result["messages"]):
    print(f"  [{i}] {type(msg).__name__} → ...")
```

运行并观察完整消息流：

```bash
python step4_single_tool.py
```

![Step 4 消息流：[0]HumanMessage→[1]AIMessage(tool_calls:query_order)→[2]ToolMessage(已发货)→[3]AIMessage(最终回答)，共 4 条消息](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step4-single-tool-loop.png)

```
消息流（工具调用循环）:
  [0] HumanMessage → 订单 A1001 是什么状态？
  [1] AIMessage → tool_calls: [('query_order', {'order_id': 'A1001'})]
  [2] ToolMessage → content: 已发货 · 预计明天到达
  [3] AIMessage（最终回答）→ 订单 **A1001** 当前的状态是 **🟢 已发货**，预计 **明天到达**。
消息总条数: 4
```

这 4 条消息，正是开篇所讲工具调用循环的完整一轮，一一对应：

- **`[0]` HumanMessage**：用户的原始问题，循环的输入；
- **`[1]` AIMessage（带 tool_calls）**：模型推理后的决策——它没有直接回答，而是决定调用 `query_order`，参数 `{'order_id': 'A1001'}`。这一步对应循环的「推理 + 调工具」；
- **`[2]` ToolMessage**：工具执行的返回值「已发货 · 预计明天到达」，原样喂回模型，对应循环的「结果喂回」；
- **`[3]` AIMessage（最终回答）**：模型拿到工具结果后，生成自然语言回答，对应循环的「完成」。

有两个工程细节值得记下来。其一，`AIMessage.tool_calls` 是一个由字典组成的列表，每个字典含 `name`（工具名）、`args`（参数）、`id`（调用编号）三个字段——这是 DeepSeek 实际返回的结构，可在终端输出中确认。其二，最终回答里复用了工具返回的「已发货」措辞，说明工具结果真实参与了生成，不是模型凭空编造。

#### 2、逐条拆解消息流

上一步看到了 4 条消息的整体结构，但每条消息的内部字段还能再拆细一层。遍历 `result["messages"]`，逐条打印 `type` / `content` / `tool_calls` / `tool_call_id`：

```bash
python ext1_print_message_stream.py
```

```
── 消息 [1] ────────────────────────────
  type    : AIMessage
  content : 好的，我来查询一下订单 A1001 的当前状态。
  tool_calls:
    - name  : query_order
      args  : {'order_id': 'A1001'}
      id    : call_00_L7m10XIu...

── 消息 [2] ────────────────────────────
  type    : ToolMessage
  content : 已发货 · 预计明天到达
  tool_call_id: call_00_L7m10XIu...
```

![消息流逐条解析，含 type/content/tool_calls/tool_call_id 完整字段，4 条消息结构清晰可见](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--extension-1-print-message-stream.png)

拆到字段层，又能看清两个机制：

1. **AIMessage 可以同时有 `content` 和 `tool_calls`**：消息 `[1]` 里，模型一边说「好的，我来查询一下……」（`content` 不为空），一边发出工具调用请求（`tool_calls` 不为空）。也就是说，模型能「边说话边行动」，两者并不互斥。
2. **ToolMessage 的 `tool_call_id` 等于 AIMessage 里 `tool_calls[].id`**：消息 `[2]` 的 `tool_call_id` 与消息 `[1]` 的调用 `id` 完全一致。这是结果路由机制——当一个回合里同时发出多个工具调用时，靠这个 id 保证每条工具返回结果对应回正确的请求。下一节的多工具场景会用到它。

四种消息类型各司其职：HumanMessage 是输入，AIMessage 承载决策与最终回答，ToolMessage 承载工具结果。消息类型，就是「读懂 Agent 在哪一步做了什么」的索引。

---

### 五、多工具协作与流式观察

#### 1、一个问题触发多个工具

单工具循环跑通后，进一步验证 Agent 的自主协作能力：构造一个需要调用两个工具才能回答的问题，看 Agent 会不会自己把它们串起来。

这里有一个实操中真实遇到的坑值得先讲。最初的问法是「订单 A1001 从北京寄到上海运费多少」，结果模型只调了 `query_order`，然后反过来追问「请问商品有多重」——因为 `calc_shipping_fee` 需要 `weight_kg` 参数，而问题里没给重量，**模型遵循「不猜参数」原则，宁可追问也不编一个默认值**。这是 Agent 「信息驱动」本质的体现：参数不全时模型会追问，而非瞎猜。修正办法是把参数补全，让两件任务明确并列。修正后的问法是：

```
帮我查一下订单 A1001 的最新物流状态，同时帮我算一下 1.5kg 商品从北京寄到上海的运费。
```

```bash
python step5_multi_tool.py
```

![Step 5 消息流：[1]AIMessage 并行发起 track_shipping + calc_shipping_fee 两个 tool_calls，[2][3]两条 ToolMessage，工具调用总次数 2](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step5-multi-tool.png)

```
消息流（工具调用循环）:
  [0] HumanMessage → 帮我查一下订单 A1001 的最新物流状态，同时帮我算一下 1.5kg 商品从北京寄到上海的运费。
  [1] AIMessage → tool_call #1: track_shipping({'order_id': 'A1001'})
  [1] AIMessage → tool_call #2: calc_shipping_fee({'origin': '北京', 'destination': '上海', 'weight_kg': 1.5})
  [2] ToolMessage → content: 2026-05-30 08:00 上海转运中心 → 正在派送中
  [3] ToolMessage → content: 从北京到上海，重量 1.5 kg，预估运费 14.5 元
  [4] AIMessage（最终回答）→ 好的，查询结果如下：...
消息总条数: 5
工具调用总次数: 2
被调用的工具: ['track_shipping', 'calc_shipping_fee']
```

注意消息总数是 **5 条而不是 6 条**，这是本步最值得关注的细节。两次工具调用 `track_shipping` 和 `calc_shipping_fee` 都挂在**同一条 AIMessage（index=1）**里并行发起，而不是顺序调用。这说明 `deepseek-chat` 支持并行工具调用（parallel function calling）：模型识别到「查物流」和「算运费」是两件互不依赖的独立任务，于是在一个回合里同时发出两个请求，而非先查完物流再算运费。两条 ToolMessage 各自靠 `tool_call_id` 路由回对应的请求——这正是上一节那个机制的实战价值。

从应用视角看，这是 Agent 处理复合任务的高效之处：面对「同时做两件独立的事」，它能并行处理，而不必把任务拆成两轮串行执行。

#### 2、invoke vs stream：让循环肉眼可见

到目前为止都用 `invoke` 调用，它一次性返回完整的消息列表。`create_agent` 编译出的图对象还支持另一种调用方式 `stream`，它会流式地吐出循环的每一步。同一个问题用两种方式各跑一遍做对比：

```bash
python ext2_stream_vs_invoke.py
```

```
方式 A: invoke
返回类型: <class 'dict'>
消息条数: 4

方式 B: stream
─ 流式 chunk #1 ─
  节点: model
    [AIMessage] → tool_calls: ['query_order']
─ 流式 chunk #2 ─
  节点: tools
    [ToolMessage] → 已发货 · 预计明天到达
─ 流式 chunk #3 ─
  节点: model
    [AIMessage] → 订单 **A1001** 当前状态为：**已发货**，预计 **明天到达**。
流式 chunk 总数: 3
```

![invoke vs stream 对比：stream 展示 3 个流式 chunk（model→tools→model），节点名为 model 而非 agent](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--extension-2-stream-vs-invoke.png)

两种方式的对比可以这样理解：

- **`invoke` 返回 dict，`stream` 返回生成器**：`invoke` 的 `result["messages"]` 是跑完整个循环后的完整消息列表；`stream` 每个 chunk 只含当前步骤的增量消息。
- **stream 的 chunk 数等于循环步数**：3 个 chunk 对应 model（决策加调工具）→ tools（执行）→ model（最终回答），与 invoke 的 4 条消息一一对应，只是颗粒度不同。
- **节点名是 `model` 不是 `agent`**：解析 stream 事件时，节点名是 `model` 和 `tools`。这一点在 LangChain v1 中是确定的——若读者参考的是旧版资料，需注意旧版节点名可能不同，迁移时按 `model` 为准。

适用场景上，`invoke` 适合直接拿最终答案的单轮问答；`stream` 适合需要实时反馈的场景——长任务的进度可视化、或像本案例这样让循环「一步步走」给人看。生产环境中，`stream` 通常带来更好的用户体验：实时响应，而非等待数秒后突然出结果。

---

### 六、换工具即换业务：复用验证

#### 1、新增 query_inventory 工具再跑

前面所有实操都围绕「查订单、物流、运费」三个工具。本案例最后验证一个关键命题：**给 Agent 增加新能力，需要改多少代码？** 把第二章预留的 `query_inventory` 工具加进工具列表，问一个全新的库存问题，看 Agent 会不会自主调用它。

改动只有一处——`tools` 列表里多加一个函数：

```python
from tools import query_order, track_shipping, calc_shipping_fee, query_inventory

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee, query_inventory],  # 多了 query_inventory
    system_prompt="你是一个订单运营助手……",
)
```

```bash
python step6_reuse_new_tool.py
```

![Step 6 消息流：新增 query_inventory 后，agent 自主调用该工具返回库存信息，工具总数 4，换工具即换业务验证通过](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-1--shot--step6-reuse-new-tool.png)

```
工具数量: 4（原 3 个 + 新增 query_inventory）
消息流（工具调用循环）:
  [0] HumanMessage → 商品 P001 的库存还有多少？
  [1] AIMessage → tool_call: query_inventory({'product_id': 'P001'})
  [2] ToolMessage → content: 库存充足 · 当前 358 件
  [3] AIMessage（最终回答）→ 商品 **P001** 当前的库存情况如下：当前库存数量 358 件，库存状态充足
消息总条数: 4
被调用的工具: ['query_inventory']
```

结果印证了命题：**只把新工具函数加进 `tools=[]` 列表，不改任何其他代码**，`create_agent` 就会自动把新工具的 docstring 注册进模型的可调用范围，模型立刻能在合适的问题上调用它。没有手写分发逻辑、没有改提示词、没有改循环代码。

这就是 `create_agent` 体系「工具即能力、换工具即换业务」的核心价值。Agent 的能力边界由工具列表定义，扩展能力等于扩展列表。理解了这一点，就能把本案例的订单助手迁移到任何其他业务场景——这正是下一章要展开的。

---

### 七、自学迁移指南：把订单助手换成你的业务

本案例用订单运营场景跑通了工具调用循环，但这套结构与「订单」这个领域无关。要把它迁移到自己的业务，关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的业务）

唯一需要改写的是**工具函数**。把 `tools.py` 里的四个函数换成你自己业务的函数即可，规范保持不变：

- **函数体**：换成你的真实逻辑。本案例返回 mock 字符串，真实业务里这里可以查数据库、调 REST API、读文件——只要最终返回字符串。
- **函数签名**：参数改成你业务需要的，但务必保留**类型注解**（如 `order_id: str`）。
- **docstring**：换成准确描述这个工具能力的说明。这一项直接决定模型何时调用它，措辞要让模型一看就懂「什么场景该用它」。

举例：把订单工具组换成「查天气 + 查汇率」，或换成调用公司内部真实 API 的工具，工具调用循环照常运转——因为循环机制与具体领域无关，只要函数签名和 docstring 规范。下面是「订单工具 → 你的业务工具」的最小改写骨架，对照着改即可：

```python
# 改之前（本案例的订单工具）
def query_order(order_id: str) -> str:
    """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
    mock = {"A1001": "已发货 · 预计明天到达"}
    return mock.get(order_id, "未找到该订单")

# 改之后（换成你的业务工具，以「查天气」为例）
def query_weather(city: str) -> str:
    """查询指定城市的实时天气。city 是城市名，如 北京。"""
    resp = requests.get(f"https://your-weather-api/...?city={city}")  # 换成真实 API
    return resp.json()["summary"]                                     # 返回字符串
```

可以看到，函数名、参数、docstring、函数体四处都换成了业务相关内容，但「带类型注解 + 带 docstring + 返回字符串」这三条规范一字未变——把改写后的函数放进 `tools=[]` 列表，Agent 就拥有了新能力。

#### 2、保持不变的部分（结构骨架）

下面这些不需要改动，它们是迁移后依然成立的骨架：

- **`create_agent` 的调用方式**：`model` / `tools` / `system_prompt` 三个参数结构不变；
- **`invoke` / `stream` 的调用入口**：传 `{"messages": [HumanMessage(...)]}`、读 `result["messages"]` 的方式不变；
- **消息流结构**：HumanMessage → AIMessage(tool_calls) → ToolMessage → AIMessage 这条循环链不变，调试时依然靠它看 Agent 每一步做了什么；
- **`system_prompt` 的职责边界**：依然只管「怎么说」，不管「调什么工具」。

#### 3、迁移后如何验证跑通

换完工具后，按本案例的验收方式自检，确认迁移成功：

1. **单工具验证**：构造一个只需调用一个新工具的问题，`invoke` 后检查消息流里是否出现对应的 `tool_calls` 和 `ToolMessage`；
2. **多工具串联验证**：构造一个需要连续或并行调用两个工具才能回答的问题（参数务必给全，否则模型会追问而非猜），确认 `工具调用总次数 ≥ 2`；
3. **换工具复用验证**：再加一个新工具进 `tools` 列表，问一个新问题，确认无需改其他代码、新工具就能被调用。

三项都通过，就说明 Agent 在你的业务场景里完整复现了工具调用循环。

#### 4、迁移前置假设清单

迁移顺利的前提是具备以下条件，动手前先核对：

- **会写带类型注解和 docstring 的 Python 函数**：这是工具函数的基本规范，docstring 尤其不能省（第二章已演示漏写会直接报 ValueError）；
- **有可用的模型 API Key 且模型支持工具调用**：本案例用 `deepseek-chat`，换其他模型时需确认该模型支持工具调用（function calling），不支持工具调用的模型（如纯推理型号）无法驱动这套循环；
- **理解工具调用循环不是默认知识**：不要假设「模型能自己决定调工具」是理所当然的——它是本案例反复演示的核心机制。迁移时若 Agent 行为不符预期，先回到消息流逐条排查，定位是「模型没调工具」「参数缺失被追问」还是「工具返回有误」。

把这三点核对清楚，本案例的订单助手就能稳妥地迁移成你自己业务的智能体。


---

## LangChain 结构化输出（structured-output）从零到一跑通实操手册

### 一、开篇：让 Agent 返回「能直接编程消费」的数据

案例 1 已经跑通了 `create_agent` 的工具调用循环：模型自主决定调哪个工具、何时调，最终生成一段自然语言回答。那段回答对「人」很友好，但对「下游程序」并不友好——它是一坨自由文本，程序想从中取出某个字段，还得自己写解析逻辑。本案例要解决的正是这个问题：让 Agent 不返回自由文本，而是返回**经过校验的结构化对象**，下游程序可以直接 `.字段名` 取值。

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)。在 LangChain v1 中，让 Agent 返回结构化数据的官方机制是给 `create_agent` 传入 `response_format` 参数，对应文档页 [docs.langchain.com/oss/python/langchain/structured-output](https://docs.langchain.com/oss/python/langchain/structured-output)。

举一个贴近业务的场景：电商客服每天收到成百上千条客户评论，运营想把每条评论自动归类——情感是正面还是负面、属于哪类问题、紧急程度多高。如果让 Agent 用自由文本回答，得到的是「这条评论情感偏负面，主要是物流问题，比较紧急」这样一句话，程序没法直接拿来统计。而结构化输出能让 Agent 直接吐出一个对象，`sentiment="negative"`、`category="logistics"`、`urgency=5`，程序可以立刻用它做计数、过滤、排序。

本案例涉及三个关键技术对象：

- **Pydantic schema（数据模型）**：用 Pydantic 定义的一个类，声明「我要的结构化数据长什么样」——有哪些字段、各是什么类型；
- **`response_format` 参数**：传给 `create_agent`，告诉它「这次调用请按这个 schema 返回结构化结果」；
- **`structured_response`**：调用结果字典里的一个 key，校验过的结构化对象就落在这里。

下文按「准备数据与 schema → 配置结构化输出 → 自由文本对比 → 策略选择 → 换 schema 复用」的顺序推进，每一步都有真实终端输出佐证。本案例沿用案例 1 的工作目录与虚拟环境，不再重复讲 `create_agent` 的工具调用循环，只聚焦在结构化输出这一层。

---

### 二、准备工作：评论数据与 Pydantic schema

#### 1、准备客户评论文本

结构化输出的教学核心是「自由文本 → 结构化对象」的转换，最直观的输入就是几条真实业务文本。新建 `reviews.py`，写入 7 条电商客户评论，覆盖物流延误、商品损坏、好评、虚假描述、退款纠纷、发错货、复购好评等多种场景，情感极性正负中性都有，给后面的抽取实验提供丰富的测试输入。

```bash
source .venv/bin/activate
python3 -c "exec(open('reviews.py').read()); print('actual_reviews:', len(reviews)); [print(f'  [{i+1}] {r[:50]}') for i, r in enumerate(reviews)]"
wc -l reviews.py
```

![终端输出 reviews.py 核验结果：actual_reviews 为 7，逐条列出 7 条评论文本前 50 字，文件共 16 行](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step1-reviews-py.png)

```
=== reviews.py 核验 ===
actual_reviews: 7
  [1] 物流速度太慢了！...
  [2] 收到商品后发现包装严重破损...
  [3] 这次购物体验非常棒！...
  [4] 买的是100ml但收到的是50ml...
  [5] 退款申请提交了十天...
  [6] 发错货了！...
  [7] 第二次购买了...
```

这 7 条评论是后续所有抽取实验的统一输入。它们的情感极性故意做了区分——既有「物流速度太慢、要求退款」的强负面，也有「购物体验非常棒」的正面，还有「描述不符」这类需要语义判断才能归类的中性场景。后面会看到，Agent 对这些不同极性的评论都能正确归类。

#### 2、定义 Pydantic schema：ReviewAnalysis 与 OrderInfo

有了输入文本，下一步是声明「我想要的结构化结果长什么样」。这件事由 Pydantic 完成。Pydantic 是 Python 生态里最主流的数据校验库，官网为 [docs.pydantic.dev](https://docs.pydantic.dev/)，它的核心用法是：继承 `BaseModel` 定义一个类，用类型注解声明每个字段，Pydantic 会在实例化时自动校验数据是否合规。本案例不展开教 Pydantic，只用到它最基础的「定义字段 + 类型注解」能力。

新建 `schemas.py`，定义两个数据模型。`ReviewAnalysis` 用于评论分析，含三个字段；`OrderInfo` 用于订单信息抽取，含四个字段（第六章会用它演示「换 schema 即换业务」）。注意字段上的 `Field(description=...)`——这段描述文字不只是给人看的注释，它会被框架传给模型，引导模型「这个字段该填什么」：

```python
# schemas.py（节选）
from pydantic import BaseModel, Field

class ReviewAnalysis(BaseModel):
    """客户评论分析结果"""
    sentiment: str = Field(description="情感极性：positive / negative / neutral")
    category: str = Field(description="问题类别：logistics / product_quality / refund 等")
    urgency: int = Field(description="紧急程度，1-5 的整数，5 最紧急")

class OrderInfo(BaseModel):
    """订单信息抽取结果"""
    order_id: str = Field(description="订单编号，如 ORD-20240301-001")
    product_name: str = Field(description="商品名称")
    amount: float = Field(description="订单金额，单位元")
    status: str = Field(description="订单状态：shipped / delivered / disputed 等")
```

运行 `schemas.py` 的 `__main__` 块，确认两个 schema 的字段定义正确、能正常实例化：

```bash
python3 schemas.py
```

![终端输出 schemas.py 核验：ReviewAnalysis 字段为 sentiment、category、urgency，OrderInfo 字段为 order_id、product_name、amount、status，两个 Pydantic 实例验证通过](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step2-schemas-py.png)

```
=== schema 定义核验 ===
ReviewAnalysis fields: ['sentiment', 'category', 'urgency']
OrderInfo fields: ['order_id', 'product_name', 'amount', 'status']
ReviewAnalysis 示例: sentiment='negative' category='logistics' urgency=4
OrderInfo 示例: order_id='ORD-20240301-001' product_name='保温杯 500ml' amount=128.0 status='disputed'
```

这里有一个省事的细节：`pydantic` 随 `langchain` 1.3.2 一并装好，无需额外 `pip install`。两个 schema 直接实例化成功，Pydantic v2 的字段校验正常工作。`ReviewAnalysis` 的 `urgency` 是 `int` 类型、`OrderInfo` 的 `amount` 是 `float` 类型——这些类型约束后面会派上用场：模型填进来的值会被强制转成声明的类型，下游程序拿到的就是真正的整数和浮点数，而不是字符串。

---

### 三、配置结构化输出：response_format + ToolStrategy

#### 1、用 ToolStrategy 包装 schema 传给 create_agent

schema 准备好了，现在把它接到 Agent 上。LangChain v1 提供了一个 `response_format` 参数，传入它就开启结构化输出。但 schema 不是直接裸传，而是用一个**策略类**包一层。本案例主线用的是 `ToolStrategy`（工具调用策略），从 `langchain.agents.structured_output` 导入。

`ToolStrategy` 的含义后文会详细展开，这里先记住它的作用：它告诉框架「用工具调用（tool calling）协议来约束模型输出符合 schema」。新建 `step3_create_agent_structured.py`，把 `ToolStrategy(ReviewAnalysis)` 传给 `response_format`：

```python
# step3_create_agent_structured.py（节选）
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from schemas import ReviewAnalysis

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(ReviewAnalysis),  # 关键：开启结构化输出
)
print("Agent created:", type(agent).__name__)
```

```bash
python3 step3_create_agent_structured.py
```

![终端输出 Step 3 结果：Strategy type 为 ToolStrategy，Strategy schema 为 ReviewAnalysis，Agent created 为 CompiledStateGraph，response_format passed 为 ToolStrategy(ReviewAnalysis)](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step3-create-agent-structured.png)

```
=== Step 3: create_agent with response_format=ToolStrategy ===
Schema: ReviewAnalysis
Fields: ['sentiment', 'category', 'urgency']
Strategy type: ToolStrategy
Strategy schema: ReviewAnalysis
Agent created: CompiledStateGraph
response_format passed: ToolStrategy(ReviewAnalysis)
=== Agent 已就绪，等待 Step 4 invoke ===
```

`create_agent` 的返回类型是 `CompiledStateGraph`——这一点与案例 1 完全一致，说明无论是否开启结构化输出，`create_agent` 底层都是把配置编译成一张 LangGraph 可执行图。区别只在于：传了 `response_format` 后，这张图在生成最终回答前，会多走一道「按 schema 约束输出」的环节。这里 `tools=[]` 是空的，因为本案例的重点不是工具调用，而是结构化输出本身——Agent 直接读评论文本、按 schema 抽取，不需要额外工具。

#### 2、invoke 一条评论，读 structured_response

Agent 就绪，发出第一次调用。`invoke` 的传参方式与案例 1 一致——传一个含 `messages` 的字典。关键差别在返回结果：开启结构化输出后，结果字典里会多出一个 `structured_response` key。新建 `step4_invoke_structured.py`，invoke 第 1 条评论（物流延误 + 退款诉求），把结果的 key、`structured_response` 的类型和字段都打印出来：

```python
# step4_invoke_structured.py（节选）
result = agent.invoke({"messages": [{"role": "user", "content": reviews[0]}]})

print("result keys:", list(result.keys()))
sr = result["structured_response"]
print("类型:", type(sr).__name__)
print("  .sentiment =", sr.sentiment)
print("  .category  =", sr.category)
print("  .urgency   =", sr.urgency)
```

```bash
python3 step4_invoke_structured.py
```

![终端输出 Step 4 结果：result keys 为 messages 和 structured_response，类型为 ReviewAnalysis，完整对象 sentiment 为 negative、category 为 logistics、urgency 为 5，三个字段访问成功，绿色勾号提示下游程序可直接 .field 取值](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step4-structured-instance.png)

```
=== Step 4: invoke 一条评论，读 structured_response ===
输入评论: 物流速度太慢了！下单三天还没发货，客服说在备货中，我等不了了，要求退款。这个售后态度真的很差！

=== result keys ===
['messages', 'structured_response']

=== structured_response ===
类型: ReviewAnalysis
完整对象: sentiment='negative' category='logistics' urgency=5
  .sentiment  = negative
  .category   = logistics
  .urgency    = 5

✅ structured_response 字段访问成功——下游程序可直接 .field 取值
```

这是本案例最核心的一步，三个细节值得讲清楚：

1. **`result` 只有两个 key**：`messages` 和 `structured_response`。`messages` 是案例 1 已经熟悉的消息流，`structured_response` 是这次新增的结构化结果。设计很干净——结构化对象不混在消息里，单独放一个 key。
2. **`structured_response` 是真正的 Python 对象**：它的类型是 `ReviewAnalysis`（就是第二章定义的那个类），不是字符串、不是字典。所以可以直接 `sr.sentiment`、`sr.urgency` 取值，IDE 还能自动补全字段名。
3. **模型的语义推断正确**：这条评论是「物流延误 + 要求退款」，模型抽出 `sentiment="negative"`、`category="logistics"`、`urgency=5`（最高紧急度），判断准确。而且 `urgency` 是整数 `5` 而非字符串 `"5"`——类型被 schema 强制约束住了。

到这里，结构化输出的完整闭环已经跑通：定义 schema → `create_agent(response_format=...)` → `invoke` → 读 `result["structured_response"]`，拿到一个校验过的对象。后面几章都是在这个闭环上做深化和对比。

#### 3、结构化为什么「可信赖」：校验机制的两层保护

读者看到 `structured_response` 能直接取值，可能会有一个疑问：模型是概率性生成的，万一它填了一个不合规的值（比如 `urgency` 填了超出 1-5 范围的 10），会怎样？这关系到「结构化结果到底可不可信」，值得专门验证一下。

设计一个对照实验 `ext2_schema_validation.py`：用一个带强约束的 schema（`urgency` 限定 1-5），分三种情况测试——正常评论、故意诱导越界的极端评论、以及手动构造一个越界实例：

```bash
python3 ext2_schema_validation.py
```

![终端输出 schema 校验行为：测试 1 urgency 为 3 校验通过，测试 2 极端评论 LLM 自动将紧急度收敛到 urgency 为 5，测试 3 手动构造 urgency 为 10 被 Pydantic 抛出 ValidationError 拦截，错误信息清晰指出 urgency 必须在 1-5 之间](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--extension-2-schema-validation.png)

```
【测试 1】正常评论: 快递延误两天，有点不满意，但商品质量还好。
  ✅ 校验通过: sentiment='negative' category='物流问题' urgency=3

【测试 2】极端评论（故意诱导越界）: 账号被盗，资金损失严重，这是10级紧急情况！
  ✅ 校验通过: sentiment='negative' category='账号安全' urgency=5
  → LLM 正确地把极端场景映射到最高 urgency=5（而非越界值10）

【测试 3】手动越界实例（展示 Pydantic 直接校验）
  ❌ Pydantic 直接拦截: ValidationError
  错误信息: urgency: Value error, urgency 必须在 1-5 之间，收到 10
```

这个实验揭示了结构化输出的两层保护机制：

- **第一层是 field description 引导**：测试 2 里评论明说「10 级紧急」，但模型仍然填入 `urgency=5`——因为字段描述写了「1-5 的整数」。好的字段描述能在源头引导模型输出合法值，这相当于把提示词工程下沉到了 schema 层。
- **第二层是 Pydantic 强制校验**：测试 3 手动构造一个 `urgency=10` 的实例，Pydantic 的校验器立刻抛出 `ValidationError`，错误信息精确指出问题。这是最后一道防线——即便模型罕见地填了越界值，框架在从模型输出提取参数后会立即做 Pydantic 校验，不合规就拦下。

两层叠加，`structured_response` 才能被下游程序放心消费。这里也带出一个实测发现：`category` 字段在本实验的 schema 里没加枚举约束，模型填入了中文（「物流问题」「账号安全」）而非预期的英文。这说明若要严格约束某个字段的取值，应在字段描述里明确列出可选项，或用 `Literal` 类型注解锁死——这是生产中提高一致性的常用手段。

---

### 四、自由文本 vs 结构化：核心对比

#### 1、同一条评论，两种输出方式

前面单独看了结构化输出，但它的价值要在对比中才看得最清楚。设计一个对照实验 `step5_compare_free_vs_structured.py`：用同一条评论，分别让两个 Agent 处理——方案 A 不带 `response_format`（返回自由文本），方案 B 带 `response_format=ToolStrategy`（返回结构化对象），把两者的结果摆在一起：

```bash
python3 step5_compare_free_vs_structured.py
```

![终端对比输出：方案 A 不带 response_format 返回 str 类型的 JSON 文本，键名是中文「情感极性」、urgency 值是字符串「高」；方案 B 带 response_format 返回 ReviewAnalysis 对象，sentiment 为 negative、category 为 logistics、urgency 为整数 5；核心结论是自由文本难解析、结构化对象可直接 .field 使用](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step5-text-vs-struct.png)

```
【方案 A】不带 response_format——自由文本
  result keys: ['messages']
  类型: str
  内容（前200字）: {
  "情感极性": "负面",
  "问题类别": "物流/包装破损",
  "紧急程度": "高"
}
  ❌ 下游程序无法直接取值——需要手动解析字符串

【方案 B】带 response_format=ToolStrategy——结构化输出
  result keys: ['messages', 'structured_response']
  类型: ReviewAnalysis
  对象: sentiment='negative' category='logistics' urgency=5
  .sentiment = negative / .category = logistics / .urgency = 5
  ✅ 下游程序可直接 .field 取值——无需解析字符串
```

这个对比把两种方式的差异摊得很透，整理成表：

| 维度 | 方案 A：不带 response_format | 方案 B：带 response_format |
|------|----------------------------|---------------------------|
| **result keys** | 只有 `messages` | `messages` + `structured_response` |
| **结果类型** | `str`（字符串） | `ReviewAnalysis`（Python 对象） |
| **键名** | 中文「情感极性」（模型自由发挥） | `sentiment`（schema 锁定） |
| **urgency 值** | 字符串「高」 | 整数 `5` |
| **下游消费** | 需手动解析字符串 | 直接 `.field` 取值 |

最值得注意的是方案 A 的输出：即便提示模型「请输出 JSON」，模型也用了中文键名「情感极性」（而不是 `sentiment`）、字符串值「高」（而不是整数 5）。也就是说，**靠提示词让模型「尝试格式化」，结果仍是类型不安全、键名不可控的字符串，没法直接编程消费**。这恰好解释了 LangChain v1 为什么把「提示模型输出 JSON 再手动解析」这种旧做法移除、改用 `response_format` 机制——把结构化约束交给框架，而不是赌模型每次都按要求格式化。

---

### 五、策略选择：ToolStrategy vs ProviderStrategy

#### 1、三种写法对比与 DeepSeek 实测

第三章用了 `ToolStrategy`，但 `response_format` 其实接受三种写法。设计实验 `step6_strategy_compare.py` 把它们摆在一起对比：① 直接传 schema 类（让框架自动选策略）② 显式传 `ToolStrategy` ③ 显式传 `ProviderStrategy`（探测 DeepSeek 是否支持）：

```bash
python3 step6_strategy_compare.py
```

![终端输出 Step 6 策略对比：写法 1 直接传 schema 和写法 2 显式 ToolStrategy 结果完全一致，都返回 ReviewAnalysis 对象 sentiment 为 positive、category 为 praise、urgency 为 1；写法 3 ProviderStrategy 报 BadRequestError 400，提示 This response_format type is unavailable now，确认 DeepSeek 不支持 provider 原生结构化输出](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step6-strategy-compare.png)

```
【写法 1】response_format=ReviewAnalysis（直接传 schema）
  → 结果: sentiment='positive' category='praise' urgency=1 ✅

【写法 2】response_format=ToolStrategy(ReviewAnalysis)（显式）
  → 结果: sentiment='positive' category='praise' urgency=1 ✅（与写法 1 完全一致）

【写法 3】response_format=ProviderStrategy(ReviewAnalysis)（显式 ProviderStrategy）
  ❌ BadRequestError 400: "This response_format type is unavailable now"
  → DeepSeek 不支持 ProviderStrategy
```

三个结果带出三个结论：

1. **写法 1 等价于写法 2**：直接传 schema 类时，框架会自动选策略。对 DeepSeek 来说，它自动降级到了 `ToolStrategy`——所以写法 1 和写法 2 的结果完全一致。
2. **`ProviderStrategy` 在 DeepSeek 上报 400 错误**：错误信息是 `This response_format type is unavailable now`。这是预期内的行为，不是 bug——它揭示了一个真实的兼容性边界。
3. **策略差异封装在内部**：三种写法的 Agent 节点结构相同，策略差异被封装在模型节点内部，对调用方透明。

⚠️ 这里的 `ProviderStrategy` 报错值得专门说明：它不是程序写错了，而是 DeepSeek 这家 provider 没有提供「原生结构化输出 API」端点。实验代码用 `try/except` 优雅地捕获了这个错误并继续运行，不影响主线。生产中遇到这类「某 provider 不支持某策略」的情况，正确做法就是退回到兼容性更广的 `ToolStrategy`，而不是为了用 `ProviderStrategy` 去换模型。

#### 2、两种策略的底层机制与兼容性矩阵

报错本身是最好的教学材料——它逼着我们搞清楚 `ToolStrategy` 和 `ProviderStrategy` 到底差在哪。专门做一个对比实验 `ext1_tool_vs_provider.py`，把两种策略对同一条评论的效果和兼容性铺开：

```bash
python3 ext1_tool_vs_provider.py
```

![终端输出 ToolStrategy 与 ProviderStrategy 完整对比：ToolStrategy 成功返回 ReviewAnalysis 实例，sentiment 为 negative、category 为 refund、urgency 为 5；ProviderStrategy 报 400 BadRequestError；下方策略选择参考表列出 DeepSeek、OpenAI、Claude、本地 Ollama 四种 provider 对两种策略的支持情况](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--extension-1-tool-vs-provider.png)

```
【1】ToolStrategy（tool calling 兜底）
  原理：用工具调用协议要求 LLM 返回符合 schema 的参数
  适用：任何支持 tool calling 的模型（包括 DeepSeek）
  ✅ 成功 → sentiment='negative' category='refund' urgency=5

【2】ProviderStrategy（provider 原生结构化输出）
  ❌ 报错: BadRequestError 400 "This response_format type is unavailable now"
  → 确认：DeepSeek 不支持 ProviderStrategy

策略选择参考表：
  DeepSeek deepseek-chat     ToolStrategy ✅   ProviderStrategy ❌
  OpenAI GPT-4o              ToolStrategy ✅   ProviderStrategy ✅
  Anthropic Claude 3.5       ToolStrategy ✅   ProviderStrategy ✅
  本地 Ollama 模型            ToolStrategy ✅   ProviderStrategy ❌（一般不支持）
```

两种策略的本质区别在于「用什么手段约束模型输出符合 schema」：

- **`ToolStrategy`（工具调用兜底）**：把 schema 的字段封装成一个「工具」的参数，让模型以「调用工具」的方式来「填写」这些字段。框架再从模型返回的工具调用内容里提取参数，做 Pydantic 校验。它的好处是适用面广——任何支持工具调用（function calling）的模型都能用，包括 DeepSeek。
- **`ProviderStrategy`（provider 原生）**：直接调用 provider 自家的「结构化输出 API」（如 `response_format=json_schema` 端点），让 provider 在 API 层面保证返回符合 schema。它的约束更直接、更可靠，但前提是该 provider 提供了这个端点——DeepSeek 目前没有，所以报 400。

整理成兼容性矩阵，方便选型：

| Provider | ToolStrategy | ProviderStrategy | 选型建议 |
|----------|:-:|:-:|---------|
| DeepSeek deepseek-chat | ✅ | ❌ | 必须用 ToolStrategy |
| OpenAI GPT-4o | ✅ | ✅ | 两者都可，ProviderStrategy 更稳 |
| Anthropic Claude 3.5 | ✅ | ✅ | 两者都可，ProviderStrategy 更稳 |
| 本地 Ollama 模型 | ✅ | ❌（一般不支持） | 用 ToolStrategy |

实用结论：国内常用的 DeepSeek 只能走 `ToolStrategy`；如果换成 OpenAI 或 Claude，两种策略都可用，`ProviderStrategy` 理论上更可靠（API 层面硬约束，比工具调用的间接约束更稳）。换 provider 时，框架已经把策略抽象好了，往往只需改一个参数——这正是 LangChain 把策略做成可插拔的价值。

---

### 六、换 schema 即换业务：复用验证

#### 1、换 OrderInfo schema 抽订单文本

前面所有实操都围绕「评论分析」这一个 schema。本案例最后验证一个关键命题：**换一个业务场景，需要改多少代码？** 把 `ReviewAnalysis` 换成第二章定义的 `OrderInfo`，处理 3 条订单描述文本，看框架代码要不要动。新建 `step7_reuse_order_schema.py`：

```python
# step7_reuse_order_schema.py（节选）
from schemas import OrderInfo  # 唯一改动：换 schema 类名

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(OrderInfo),  # ReviewAnalysis → OrderInfo
)
for text in order_texts:
    result = agent.invoke({"messages": [{"role": "user", "content": text}]})
    info = result["structured_response"]
    print(f"  .order_id={info.order_id} / .amount={info.amount} / .status={info.status}")
```

```bash
python3 step7_reuse_order_schema.py
```

![终端输出 Step 7 OrderInfo schema 复用结果：3 条订单文本各自抽取出 OrderInfo 实例，含 order_id、product_name、amount、status 四个字段，三个绿色勾号确认复用验证通过，框架代码对比显示唯一改动是 schema 类名](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--step7-reuse.png)

```
--- 订单文本 1 ---
类型: OrderInfo
  .order_id     = ORD-20240301-001
  .product_name = 500ml保温杯
  .amount       = 128.0
  .status       = shipped

--- 订单文本 2 ---
类型: OrderInfo / order_id=ORD-20240315-088 / product_name=雨伞 / amount=68.0 / status=disputed

--- 订单文本 3 ---
类型: OrderInfo / order_id=ORD-20240320-156 / product_name=护肤套装 / amount=399.0 / status=delivered

=== 框架代码对比 ===
  唯一改动：schema 类名（ReviewAnalysis → OrderInfo），其余代码 0 改动
```

结果印证了命题：**只把 `ReviewAnalysis` 换成 `OrderInfo`，其余代码一字未改**，Agent 就从「评论分析」切换到了「订单抽取」，3 条订单文本全部正确抽取（`shipped`/`disputed`/`delivered` 状态判断准确）。这就是结构化输出「换 schema 即换业务」的核心价值——业务逻辑由 schema 定义，换业务等于换 schema，框架代码是稳定骨架。

#### 2、批量抽取与结构化数据的可计算性

最后用一个收口实验展示结构化输出的终极价值。前面都是单条抽取，生产中更常见的是批量处理。`ext3_batch_extract.py` 把第二章的全部 7 条评论批量抽取，并直接对结构化结果做统计：

```bash
python3 ext3_batch_extract.py
```

![终端输出批量抽取 7 条评论结果：7 条评论全部成功抽取 ReviewAnalysis 实例，汇总表展示 sentiment、category、urgency 三列；统计分析显示情感分布 negative 5 条、positive 2 条，平均紧急度 3.9，高紧急 5 条，批量处理成功率 7/7 即 100%](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-2--shot--extension-3-batch-extract.png)

```
批量处理 7 条评论：
[1] 物流速度太慢了...     → negative  logistics             urgency=5
[2] 收到商品后包装破损...  → negative  product_quality       urgency=5
[3] 这次购物体验非常棒...  → positive  praise                urgency=1
[4] 买的是100ml但收到50ml → negative  description_mismatch  urgency=5
[5] 退款申请十天未到账...  → negative  refund                urgency=5
[6] 发错货了！红色→蓝色... → negative  wrong_item            urgency=5
[7] 第二次购买好评...      → positive  praise                urgency=1

汇总统计：
  情感分布: {'negative': 5, 'positive': 2}
  平均紧急度: 3.9
  高紧急（urgency>=4）: 5 条
  批量处理成功率: 7/7 (100%)
```

这个实验有三个值得记下的观察：

1. **批量一致性 100%**：7 条评论全部返回 `ReviewAnalysis` 实例，零失败，`ToolStrategy` 在批量场景下表现稳定。一次 `create_agent`、循环 `invoke`，框架层面的批量处理天然可行。
2. **结构化数据可直接计算**：「情感分布」「平均紧急度」「高紧急条数」这些统计，全部用 Python 的 `Counter`、`sum` 直接算出来，没有任何字符串解析。这就是结构化输出最实在的价值——**让「AI 分析结果」变成「可编程的数据」**，运营拿到的不再是一堆需要人读的文本，而是能直接进 BI 报表、能触发自动化流程的结构化字段。
3. **模型输出存在随机性**：评论 [2]「包装破损」在这次批量里被归为 `product_quality`，而在第四章的对比实验里被归为 `logistics`——同一文本多次调用可能有细微差异。这是大语言模型的固有特性，生产场景下建议在字段描述里给出更明确的分类指引，或用 `Literal` 类型把可选值锁死，以提高一致性。

---

### 七、自学迁移指南：把评论分析换成你的抽取业务

本案例用「客户评论分析」和「订单信息抽取」两个场景跑通了结构化输出，但这套结构与具体业务无关。要把它迁移到自己的抽取任务（如简历解析、合同要素提取、工单分类），关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的业务）

唯一需要改写的是 **Pydantic schema**。把 `schemas.py` 里的数据模型换成你业务需要的字段即可，规范保持不变：

- **字段名与类型**：换成你要抽取的字段，类型按需选 `str`/`int`/`float`/`bool`，甚至嵌套的 `list`、子模型；
- **`Field(description=...)`**：每个字段都写清楚描述，这段文字直接引导模型「这个字段该填什么」，是抽取质量的关键；
- **约束（可选）**：需要锁死取值范围的字段，用 `Literal` 类型或在描述里列举可选项（如把 `category` 限定为固定几个英文枚举值）。

下面是「评论分析 schema → 你的业务 schema」的最小改写骨架，以简历解析为例，对照着改即可：

```python
# 改之前（本案例的评论分析 schema）
class ReviewAnalysis(BaseModel):
    """客户评论分析结果"""
    sentiment: str = Field(description="情感极性：positive / negative / neutral")
    category: str = Field(description="问题类别：logistics / product_quality 等")
    urgency: int = Field(description="紧急程度，1-5 的整数")

# 改之后（换成简历解析，以抽取姓名/技能/年限为例）
class ResumeInfo(BaseModel):
    """简历信息抽取结果"""
    name: str = Field(description="候选人姓名")
    skills: list[str] = Field(description="技能列表，如 ['Python', 'SQL']")
    years: int = Field(description="工作年限，整数")
```

字段、类型、描述三处都换成了业务相关内容，但「继承 `BaseModel` + 类型注解 + `Field` 描述」的规范一字未变——把改写后的 schema 用 `ToolStrategy` 包一层传给 `response_format`，Agent 就能抽取新业务的结构化数据。

#### 2、保持不变的部分（结构骨架）

下面这些不需要改动，它们是迁移后依然成立的骨架：

- **`create_agent(response_format=...)` 的调用方式**：把 schema 用策略类包一层传进去，结构不变；
- **`invoke` 的调用入口**：传 `{"messages": [...]}`、读 `result["structured_response"]` 的方式不变；
- **`structured_response` 是 Python 对象**：永远可以直接 `.字段名` 取值，下游消费方式不变；
- **策略选型逻辑**：DeepSeek 等国内模型用 `ToolStrategy`，OpenAI/Claude 可考虑 `ProviderStrategy`——这条选型规则与具体 schema 无关。

#### 3、迁移后如何验证跑通

换完 schema 后，按本案例的验收方式自检，确认迁移成功：

1. **单条抽取验证**：构造一段符合新业务的文本，`invoke` 后检查 `result` 里是否有 `structured_response` key，且其类型是你定义的新 schema 类；
2. **字段取值验证**：对 `structured_response` 逐个 `.字段名` 取值，确认每个字段的值和类型都符合预期（整数字段是 `int`、不是字符串）；
3. **批量复用验证**：循环处理多条文本，确认全部返回结构化实例、可直接用 `Counter`/`sum` 做统计，无需字符串解析。

三项都通过，就说明结构化输出在你的业务场景里完整跑通了。

#### 4、迁移前置假设清单

迁移顺利的前提是具备以下条件，动手前先核对：

- **已掌握案例 1 的 `create_agent`**：本案例是在案例 1 基础上加 `response_format` 一层，若对 `create_agent` 的工具调用循环还不熟，建议先回到案例 1；
- **会定义基础的 Pydantic `BaseModel`**：能继承 `BaseModel`、用类型注解声明字段、写 `Field` 描述。不需要精通 Pydantic，但这是 schema 的基本功，可参考 [Pydantic 官方文档](https://docs.pydantic.dev/)；
- **理解「结构化 vs 自由文本」的差异不是默认知识**：不要假设「让模型输出 JSON」就等于结构化——第四章已演示，靠提示词得到的 JSON 是类型不安全的字符串。真正的结构化要靠 `response_format` + schema 校验；
- **确认所用模型的策略兼容性**：换 provider 前先核对兼容性矩阵——DeepSeek 只能用 `ToolStrategy`，硬上 `ProviderStrategy` 会报 400。迁移时若抽取报错，先回到第五章的策略选型逻辑排查。

把这几点核对清楚，本案例的评论分析就能稳妥地迁移成你自己业务的结构化抽取智能体。


---

## LangChain 中间件系统（middleware-system）从零到一跑通实操手册

### 一、开篇：把横切逻辑从「到处手写」变成「声明式挂载」

案例 1 已经跑通了 `create_agent` 的工具调用循环：模型自主决定调哪个工具、何时调，框架执行后把结果喂回模型，直到生成最终回答。但在真实工程里，一个 Agent 上线后还要承担很多与「业务问答」无关、却又躲不掉的事情：每次调模型前记一条日志、限制单次会话最多调几次模型（控成本）、把用户消息里的手机号、邮箱脱敏后再送给模型、工具抛错时不让整个 Agent 崩溃。这类逻辑有一个共同特征——它们与具体业务无关，却散落在程序的每一个调用点上。软件工程里把这种「跨越多个模块、到处都要插一段相同代码」的逻辑称为**横切关注点（cross-cutting concern）**，通俗讲就是「每个地方都要加的同一段代码」。

把横切逻辑直接塞进工具函数或 Agent 主流程，会带来两个问题：一是同一段代码复制粘贴到处都是，改一次要改 N 处；二是业务逻辑和横切逻辑搅在一起，读代码的人分不清哪行是主线、哪行是辅助。LangChain v1 给出的解法是 **middleware（中间件）**——把这些横切逻辑写成独立单元，在创建 Agent 时通过 `middleware=[...]` 参数声明挂上去，而不必改动工具函数和主流程一行代码。对应官方文档页为 [docs.langchain.com/oss/python/langchain/middleware](https://docs.langchain.com/oss/python/langchain/middleware)，源码模块为 `langchain.agents.middleware`。

middleware 的核心机制是**钩子（hook）**：框架在 Agent 执行的若干固定时机预留了「挂载点」，middleware 把自己的逻辑挂到这些点上，到点了框架自动回调。LangChain v1 提供 6 个 hook，按触发时机分成两类：

- **节点 hook**（在某个固定时刻触发，观察或修改状态）：`before_agent`（智能体循环开始前）、`before_model`（每次调模型前）、`after_model`（每次调模型后）、`after_agent`（智能体循环结束后）；
- **包裹 hook**（把目标调用「包」在中间，可在调用前后都插手）：`wrap_model_call`（包住一次模型调用）、`wrap_tool_call`（包住一次工具调用）。

本案例围绕这 6 个 hook 展开，复用案例 1 已经写好的工具集（`tools.py` 里的 `query_order`、`track_shipping`、`calc_shipping_fee`、`query_inventory`），不再重复讲工具调用循环本身，只聚焦 middleware 这一层。下文按「确认环境 → 写第一个装饰器式 middleware → 挂内置 middleware → 看透执行顺序 → 用 hook 控制执行流 → 换 agent 复用」的顺序推进，每一步都有真实终端输出佐证。

本案例涉及的核心技术对象有三个：

- **`AgentMiddleware`**：所有 middleware 的基类，无论是装饰器式还是类式写法，底层都是它的子类；
- **6 个 hook**：middleware 挂载逻辑的 6 个时机，理解它们的触发时刻与执行顺序是本案例的原理核心；
- **内置 middleware**：LangChain 随框架附带的 14 个开箱即用 middleware（限流、脱敏、重试、降级等），一行声明即可启用。

---

### 二、准备工作：确认 middleware 环境与工具集复用

#### 1、确认 middleware 模块就位

本案例沿用案例 1 的工作目录与 Python 虚拟环境（venv），框架版本为 `langchain` 1.3.2、Python 3.13.13。middleware 的全部能力都集中在 `langchain.agents.middleware` 这一个模块下，运行实操前先确认它能正常导入。新建 `step1_middleware_base.py`，逐项验证 6 个 hook、基类与几个内置 middleware 是否就位，并确认案例 1 的工具集仍可用：

```python
# step1_middleware_base.py（节选）
from langchain.agents.middleware import (
    before_agent, before_model, after_model, after_agent,  # 4 个节点 hook
    wrap_model_call, wrap_tool_call,                        # 2 个包裹 hook
    AgentMiddleware,                                        # 基类
    ModelCallLimitMiddleware, PIIMiddleware, SummarizationMiddleware,  # 内置
)
from langchain.agents import create_agent
from tools import query_order, track_shipping, query_inventory
```

运行后，终端逐项打印出模块就位情况与工具集复用结果：

```bash
source .venv/bin/activate
python step1_middleware_base.py
```

![终端输出 step1_middleware_base.py：6 个 hook 函数 before_model/after_model 等可导入 + AgentMiddleware 基类路径 langchain.agents.middleware.types + ModelCallLimitMiddleware/PIIMiddleware/SummarizationMiddleware 内置模块 + 工具集 query_order/track_shipping/query_inventory 复用验证 + 基础 agent CompiledStateGraph 组装成功](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step1-middleware-base.png)

这一步确认了三件事：

1. **6 个 hook 函数全部可从 `langchain.agents.middleware` 一处导入**——`before_model`、`after_model`、`before_agent`、`after_agent`、`wrap_model_call`、`wrap_tool_call`，无需分散到多个子模块去找；
2. **基类 `AgentMiddleware` 的真实路径是 `langchain.agents.middleware.types.AgentMiddleware`**——后文所有 middleware 不管哪种写法，追溯到底都是它的子类；
3. **案例 1 的工具集原样可用**——`query_order`、`track_shipping`、`query_inventory` 返回的 mock 数据照常，基础 Agent（不挂任何 middleware）依然编译成 `CompiledStateGraph`，与案例 1 完全一致。

这里有一个后文会用到的关键发现先记下来：内置的 `PIIMiddleware` 自带的脱敏类型只有 5 种（email、credit_card、ip、mac_address、url），**不含中文手机号**。要脱敏中文手机号，得通过 `detector` 参数传一个正则——这一点在第四章脱敏实操时会展开。

#### 2、6 个 hook 与基类 AgentMiddleware 总览

进入实操前，先建立对 6 个 hook 触发时机的整体认识。它们覆盖了一次 Agent 执行从开始到结束的关键节点：

| hook | 类型 | 触发时机 | 典型用途 |
| --- | --- | --- | --- |
| `before_agent` | 节点 | 智能体循环开始前（仅一次） | 初始化审计上下文、注入全局信息 |
| `before_model` | 节点 | 每次调模型前 | 打日志、脱敏、限流前置检查 |
| `after_model` | 节点 | 每次调模型后 | 统计 token、记录模型决策 |
| `after_agent` | 节点 | 智能体循环结束后（仅一次） | 收尾、汇总、上报 |
| `wrap_model_call` | 包裹 | 包住一次模型调用 | 模型降级、最后一刻改写请求 |
| `wrap_tool_call` | 包裹 | 包住一次工具调用 | 工具错误捕获、重试、结果改写 |

需要特别留意「每次调模型」这个措辞。案例 1 已经讲过，一个含工具调用的问题，工具调用循环会**多次**调用模型——第一次让模型决定调哪个工具，工具结果喂回后再调一次让模型生成最终回答。因此 `before_model` / `after_model` 在一次 `invoke` 里会触发**多次**，而 `before_agent` / `after_agent` 只在整个循环的头尾各触发一次。这个差异是后文很多现象的根源，下一步就能在真实日志里看到。

---

### 三、第一个 middleware：装饰器式 @before_model 打日志

#### 1、写装饰器式 middleware 并挂载

最轻量的 middleware 写法是装饰器式：写一个普通函数，用 `@before_model` 装饰它，函数就变成了一个 middleware。下面写一个最简单的日志 middleware，在每次调模型前打印当前消息数：

```python
# step2_log_middleware.py（节选）
from langchain.agents.middleware import before_model, after_model

@before_model
def log_before(state, runtime):
    msgs = state["messages"]
    print(f"[before_model] 消息数={len(msgs)}")
    return None  # 返回 None = 不修改 state，继续正常流程

@after_model
def log_after(state, runtime):
    print("[after_model] 模型已返回")
    return None

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    system_prompt="你是一个订单运营助手。",
    middleware=[log_before, log_after],   # 声明挂载，不改动工具和主流程
)
```

装饰器式 middleware 的函数签名是固定的：`fn(state, runtime)`。`state` 里能拿到当前的消息流（`state["messages"]`），`runtime` 是运行时上下文。返回值是 `dict | None`——返回 `None` 表示「我只观察、不修改」，继续正常流程；返回 `dict` 则可以修改 Agent 状态（后文 `jump_to` 会用到）。挂载方式就是把这两个 middleware 放进 `create_agent` 的 `middleware=[]` 列表，工具函数和系统提示词一行没改。

运行，问一个需要调工具的问题：

```bash
python step2_log_middleware.py
```

![终端输出 step2_log_middleware.py：log_before 类型为 langchain.agents.middleware.types.AgentMiddleware 子类 + invoke 触发 before_model 消息数=1 → after_model → before_model 消息数=3 → after_model 各 2 次 + 最终消息数 4](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step2-log-middleware.png)

输出里有两个值得拆解的现象：

第一，`log_before` 这个函数被装饰后，打印它的类型，得到的是 `AgentMiddleware` 的子类，类名正是函数名 `log_before`。这揭示了 `@before_model` 装饰器的本质——它是**语法糖**：背后动态创建了一个继承 `AgentMiddleware`、只实现 `before_model` 方法的类。也就是说，装饰器式和后文的类式写法，底层是同一套机制，没有本质区别。

第二，一次 `invoke` 里，`before_model` 触发了 **2 次**，`after_model` 也触发了 2 次，且消息数从 1 变到 3：

- 第 1 次 `before_model`（消息数=1）：此时只有用户的 `HumanMessage`，模型即将决定调哪个工具；
- 第 2 次 `before_model`（消息数=3）：此时消息流里已有 `HumanMessage` + `AIMessage(tool_calls)` + `ToolMessage`，工具结果已喂回，模型即将生成最终回答。

消息数 1→3→4 的变化，正对应案例 1 讲过的工具调用循环：`HumanMessage` → `AIMessage(带 tool_calls)` → `ToolMessage` → `AIMessage(最终回答)`。这就直观印证了上一节强调的「每次调模型都触发一次 `before_model`」——含一次工具调用的问题需要两轮模型调用，于是 `before_model` 触发两次。

#### 2、装饰器式 vs 类式：两种写法选型

装饰器式之外，middleware 还有一种「类式」写法——直接继承 `AgentMiddleware`，在类里实现需要的 hook 方法。两种写法功能等价，但适用场景不同。把同一段日志逻辑分别用两种写法实现，跑一遍做对比：

```python
# ext2_decorator_vs_class.py（节选）
# 写法一：装饰器式
@before_model
def deco_before(state, runtime):
    print(f"[装饰器式 before_model] 消息数={len(state['messages'])}")
    return None

# 写法二：类式（可携带实例状态）
class CountingMiddleware(AgentMiddleware):
    def __init__(self, tag):
        self.tag = tag
        self.call_count = 0          # 实例状态，跨多次调用累积

    def before_model(self, state, runtime):
        self.call_count += 1
        print(f"[类式 before_model] [{self.tag}] 第{self.call_count}次 · 消息数={len(state['messages'])}")
        return None

    def after_model(self, state, runtime):
        print(f"[类式 after_model] [{self.tag}] 调用总数={self.call_count}")
        return None
```

```bash
python ext2_decorator_vs_class.py
```

![终端输出 ext2_decorator_vs_class.py：装饰器式 deco_before 父类 AgentMiddleware（动态创建子类）vs 类式 CountingMiddleware 显式继承 AgentMiddleware 可携带状态 call_count，对比表格展示两者底层机制相同、触发次数一致](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--extension-2-decorator-vs-class.png)

对比下来，两种写法的关系很清楚：

- **底层统一**：`@before_model` 装饰出来的类与 `class M(AgentMiddleware)` 写出来的类，父类都是 `AgentMiddleware`，hook 触发时机、触发次数完全一致；
- **装饰器式的优势是简洁**：单个 hook、无状态的简单逻辑，一个函数加一行装饰器就搞定；
- **类式的优势是完整**：一个类里可以同时实现多个 hook（如上例同时实现 `before_model` 和 `after_model`），还能携带**实例状态**——例子里的 `call_count` 在多次调用间累积，记录这个 middleware 一共被触发了几次，装饰器式做不到这一点。

选型可以记一条朴素的判断线：**单 hook、无状态用装饰器；多 hook 或需要状态用类**。本案例后文统计 token、按 agent 独立计数的场景，都会用到类式写法。

---

### 四、内置 middleware：一行声明换横切能力

自己写 middleware 之外，LangChain 还随框架附带了一批开箱即用的内置 middleware。它们覆盖了最常见的横切场景，用法是「一行声明」——不用写任何 hook 逻辑，直接实例化挂到 `middleware=[]` 列表即可。本章用两个最有代表性的内置 middleware（限流、脱敏）演示，并对其余内置项做一次概览。

#### 1、ModelCallLimitMiddleware：给 Agent 装一个调用次数闸门

`ModelCallLimitMiddleware` 用来限制 Agent 调用模型的次数，是控制成本和防止失控循环的常用手段。它有三个核心参数：

- `thread_limit`：整个会话线程累计的模型调用上限；
- `run_limit`：单次 `invoke` 运行内的模型调用上限；
- `exit_behavior`：超限后的行为，`'end'`（默认，安静结束）或 `'error'`（抛异常）。

```python
# step3_call_limit.py（节选）
from langchain.agents.middleware import ModelCallLimitMiddleware

# run_limit=2：单次运行最多调 2 次模型
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[log_before, ModelCallLimitMiddleware(run_limit=2)],
)
```

```bash
python step3_call_limit.py
```

![终端输出 step3_call_limit.py：ModelCallLimitMiddleware 参数签名 thread_limit/run_limit/exit_behavior + run_limit=2 两次 invoke（before_model 各触发 2 次正常完成）+ exit_behavior='error' run_limit=1 触发 ModelCallLimitExceededError: Model call limits exceeded: run limit (1/1)](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step3-call-limit.png)

实测结果分两种情况：

- **`run_limit=2`（够用）**：一个含工具调用的问题需要两轮模型调用，恰好不超限，Agent 正常完成。`before_model` 日志显示触发了 2 次，与上一章的循环规律一致；
- **`run_limit=1` + `exit_behavior='error'`（触发拦截）**：单次运行只允许调一次模型，但工具调用循环至少需要两轮，于是第 2 次模型调用时直接抛出异常：

```
ModelCallLimitExceededError: Model call limits exceeded: run limit (1/1)
```

这里 `exit_behavior` 的两种模式对应两种工程取向：`'end'`（默认）让 Agent 在超限时安静地结束、返回已有结果，适合「尽力而为、不报错」的场景；`'error'` 直接抛出带具体数字的异常 `run limit (1/1)`，适合需要明确感知「这次被限流了」并做处理的场景。错误消息里的 `(1/1)` 表示「已用 1 次 / 上限 1 次」，定位起来一目了然。

还有一个执行顺序的细节：日志里自定义的 `log_before` 在 `ModelCallLimitMiddleware` 的限流检查之前打印——因为 `middleware=[log_before, ModelCallLimitMiddleware(...)]` 列表里 `log_before` 排在前面，`before_model` 按列表正序执行。这条顺序规律是下一章的主题。

#### 2、其他常用内置 middleware 一览

除了限流，LangChain 内置的 middleware 还有不少。运行一个巡演脚本，把内置清单和两个有代表性的内置项跑出来看：

```bash
python ext3_builtin_tour.py
```

![终端输出 ext3_builtin_tour.py：ToolRetryMiddleware 参数签名 max_retries=2/backoff_factor=2.0/retry_on/on_failure='continue' + flaky_query 实际调用 2 次（重试 1 次成功）+ ModelFallbackMiddleware 真实签名 first_model,*additional_models + 14 个内置 middleware 导出列表](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--extension-3-builtin-tour.png)

LangChain v1 当前导出 14 个内置 middleware，覆盖的横切场景包括：

| 内置 middleware | 用途 |
| --- | --- |
| `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` | 模型 / 工具调用次数限流 |
| `PIIMiddleware` | 敏感信息脱敏 |
| `ModelRetryMiddleware` / `ToolRetryMiddleware` | 模型 / 工具调用失败自动重试 |
| `ModelFallbackMiddleware` | 主模型失败时降级到备用模型 |
| `SummarizationMiddleware` / `ContextEditingMiddleware` | 上下文摘要 / 裁剪 |
| `HumanInTheLoopMiddleware` | 关键操作前插入人工审批 |
| `TodoListMiddleware` / `LLMToolSelectorMiddleware` / `LLMToolEmulator` | 任务清单 / 工具筛选 / 工具模拟 |
| `ShellToolMiddleware` / `FilesystemFileSearchMiddleware` | Shell 工具 / 文件搜索 |

巡演里实测了两个：

- **`ToolRetryMiddleware`**：参数比限流丰富——`max_retries=2`（默认重试 2 次）、`backoff_factor=2.0`（退避乘数，每次重试等待时间翻倍）、`retry_on=(Exception,)`（默认捕获所有异常）、`on_failure='continue'`（重试耗尽后继续而非抛错）。实测里一个会随机失败的 `flaky_query` 第 1 次调用失败，middleware 自动重试，第 2 次成功——比手写 try/except 多了退避策略，更省心；
- **`ModelFallbackMiddleware`**：这里有一个实操中踩到的坑值得提醒。它的真实签名是 `(first_model, *additional_models)`——**位置参数**，不是 `fallback_model=` 这样的关键字参数。正确用法是 `ModelFallbackMiddleware("deepseek:deepseek-chat", "openai:gpt-4o")`，第一个参数是首选降级目标、之后是再次降级的链。最初按 kwargs 写法 `fallback_model=...` 调用会直接报 `TypeError`。这提示一条通用经验：内置 middleware 的参数风格并不统一，挂载前最好确认一下它的真实签名。

#### 3、PIIMiddleware：把敏感信息挡在模型之外

`PIIMiddleware` 用来在消息送进模型之前对敏感信息（PII，个人可识别信息）脱敏。这是合规场景里高频的需求——用户消息里的手机号、邮箱不该原样流到模型服务商那边。它支持两种脱敏策略：`redact`（整段替换成占位符）和 `mask`（部分遮罩、保留尾部用于识别）。

如第二章所述，`PIIMiddleware` 自带的脱敏类型只有 5 种（email、credit_card、ip、mac_address、url），**不含中文手机号**。脱敏中文手机号需要通过 `detector` 参数传一个正则。下面同时挂两个 `PIIMiddleware`——一个用内置 email 类型、一个用自定义手机号正则：

```python
# step4_pii_middleware.py（节选）
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order],
    middleware=[
        PIIMiddleware("email", strategy="redact"),                    # 内置类型
        PIIMiddleware("phone", detector=r"1[3-9]\d{9}", strategy="mask"),  # 自定义中文手机号正则
        log_pii_before,                                               # 自定义日志，看脱敏后的消息
    ],
)
```

`PIIMiddleware` 的第一个参数是脱敏类型名。用内置类型（如 `"email"`）时只需传名字；用自定义类型（如这里的 `"phone"`）时，名字可以任取，但必须配 `detector` 参数告诉它怎么识别——这里传的正则 `r"1[3-9]\d{9}"` 匹配中国大陆手机号（1 开头、第二位 3-9、共 11 位）。

```bash
python step4_pii_middleware.py
```

![终端输出 step4_pii_middleware.py：PIIMiddleware 5 种内置类型 + email 脱敏 customer@example.com→[REDACTED_EMAIL] + 中文手机号 mask 13812345678→****5678 + DeepSeek 回答中引用脱敏后的 ****5678 证明模型从未看到真实号码](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step4-pii-masked.png)

两个脱敏规则都生效了：

- **email（redact 策略）**：输入「我的邮箱是 customer@example.com，帮我查订单 A1001 的状态」，送进模型前变成「我的邮箱是 `[REDACTED_EMAIL]`，帮我查订单 A1001 的状态」——整个邮箱被替换成占位符；
- **手机号（mask 策略）**：输入里的 `13812345678` 被遮罩成 `****5678`——前 7 位用 `****` 替换、保留后 4 位。`mask` 策略遵循信息最小化原则，保留尾号便于人工识别，但隐去了完整号码。

这里最值得记下的一点是脱敏的**时机与效果**：脱敏发生在 `before_model`（消息送进模型之前），所以模型从头到尾都只看到脱敏后的内容。实测里 DeepSeek 的最终回答中引用的也是 `****5678` 而非真实号码——这从输出端反向证明了**模型从未接触到真实手机号**，脱敏不是「展示给人看的遮罩」，而是真正挡在了模型输入之前。把 `detector` 换成别的正则（如身份证号、银行卡号），就能复用同一套机制脱敏任意自定义敏感信息。

---

### 五、执行顺序铁律：before 正序 / after 逆序 / wrap 嵌套

前面几章每次只挂一两个 middleware。真实工程里一个 Agent 往往同时挂好几个，这时一个绕不开的问题浮现：**多个 middleware 的 hook 按什么顺序触发？** 这是本案例的原理核心，也是必须亲眼看清的部分。

#### 1、3 个 middleware 同挂，看 before / after 触发顺序

挂 3 个 middleware（记为 M1、M2、M3，按此顺序放进列表），每个都在 `before_model`、`after_model` 里打印自己的标识，跑一个含工具调用的问题，把完整触发序列打出来：

```python
# step5_hook_order.py（节选）
class OrderM(AgentMiddleware):
    def __init__(self, tag): self.tag = tag
    def before_model(self, state, runtime):
        print(f"→ [before_model] {self.tag}  (消息数={len(state['messages'])})")
    def after_model(self, state, runtime):
        print(f"← [after_model]  {self.tag}")

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[OrderM("M1"), OrderM("M2"), OrderM("M3")],  # 列表顺序 M1, M2, M3
)
```

```bash
python step5_hook_order.py
```

![终端输出 step5_hook_order.py：before_agent M1 → before_model M1→M2→M3 → after_model M3→M2→M1（两轮 model call）→ after_agent M3→M1，铁律总结表格展示 before 正序 / after 逆序 / wrap 嵌套](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step5-hook-order.png)

触发序列里规律一目了然。以第一轮模型调用为例：

```
→ [before_model] M1   ┐
→ [before_model] M2   │  before 正序：M1 → M2 → M3
→ [before_model] M3   ┘
← [after_model]  M3   ┐
← [after_model]  M2   │  after 逆序：M3 → M2 → M1
← [after_model]  M1   ┘
```

提炼成一条铁律：**`before_*` 系列按列表正序触发（M1→M2→M3），`after_*` 系列按列表逆序触发（M3→M2→M1）**。这是一种栈式结构——先进的后出，像穿衣服和脱衣服：进入时按顺序一层层穿上（M1 最先穿、最贴里），退出时反过来一层层脱下（M3 最后穿、最先脱）。

实测里这条铁律的稳健性体现在几个方面：

1. **两轮模型调用都遵守**：含工具调用的问题有两轮 model call，两轮的 `before_model` 都是 M1→M2→M3、`after_model` 都是 M3→M2→M1，没有例外；
2. **`before_agent` / `after_agent` 同样遵守**：本例里 M1 实现了 `before_agent`（循环开始前触发一次）、M2/M3 未实现，`after_agent` 则按逆序 M3→M1 触发（M2 未实现该 hook 故跳过）。可见**铁律不随 hook 类型改变**——不管是 model 级还是 agent 级、before 还是 after，正序进、逆序出的规律一致；
3. **未实现的 hook 自动跳过**：一个 middleware 没实现某个 hook，框架就跳过它、继续下一个，不报错。

理解这条铁律的实际意义在于：当多个 middleware 的逻辑有依赖关系时（比如「先脱敏再打日志」要求脱敏 middleware 排在日志 middleware 前面），列表顺序就成了必须精心安排的配置。第四章脱敏实操里 `PIIMiddleware` 排在自定义日志 middleware 之前，正是利用了这条正序规律——脱敏先发生，日志才能记到脱敏后的消息。

#### 2、wrap_model_call 嵌套：俄罗斯套娃式的包裹

节点 hook（before/after）的顺序看清楚了，包裹 hook（`wrap_model_call`）的行为还需要补一块。和 before/after「到点触发一下」不同，`wrap_model_call` 是把一次模型调用「包」在中间——它能在调用前后都插手，结构上更像层层嵌套。挂 3 个带 `wrap_model_call` 的 middleware，打印它们的入口和出口：

```bash
python ext1_hook_order_trace.py
```

![终端输出 ext1_hook_order_trace.py：before_model 正序 M1→M2→M3 + wrap_model_call 嵌套入口 M1→M2→M3 出口 M3→M2→M1 形成俄罗斯套娃 + after_model 逆序 M3→M2→M1，两轮 model call 均如此](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--extension-1-hook-order-trace.png)

完整触发序列把三种执行模式一次摊开：

```
→ [before_model] M1            ┐
→ [before_model] M2            │ before 正序
→ [before_model] M3            ┘
↓ [wrap_model_call] M1 入口（最外层）    ┐
    ↓ [wrap_model_call] M2 入口（中间层）  │ wrap 嵌套：
        ↓ [wrap_model_call] M3 入口（最内层）│   入口正序、出口逆序
        ↑ [wrap_model_call] M3 出口（最内层）│
    ↑ [wrap_model_call] M2 出口（中间层）  │
↑ [wrap_model_call] M1 出口（最外层）    ┘
← [after_model]  M3            ┐
← [after_model]  M2            │ after 逆序
← [after_model]  M1            ┘
```

`wrap_model_call` 形成的是「俄罗斯套娃」结构：M1 在最外层包着 M2，M2 包着 M3，M3 最内层、最贴近真实的 LLM 调用。进入时入口按正序 M1→M2→M3 一层层往里走，到最里面执行真实模型调用，再按逆序 M3→M2→M1 一层层往外退。

把三种执行模式放一起看，会发现它们其实是**同一条「正序进、逆序出」铁律的三种表达**：

```
before_model 正序     →  [M1 → M2 → M3]
wrap_model_call 嵌套  ↓  M1 { M2 { M3 { LLM } } }
after_model 逆序      ←  [M3 ← M2 ← M1]
```

`wrap_model_call` 嵌套结构的工程价值在于：最内层的 middleware「最接近」模型，可以在真实调用发生的最后一刻改写请求（例如临时切换模型、调整参数），这正是 `ModelFallbackMiddleware` 这类降级 middleware 的实现基础。

---

### 六、hook 不只是观察者：控制 Agent 执行流

前面用到的 hook 大多是「观察者」——打日志、统计、脱敏，看完不改变 Agent 的执行路径。但 hook 的能力不止于此，它还能当「拦截者」，主动改变 Agent 的行为。本章看两个控制类的用法：工具出错时接管处理、以及让 Agent 提前退出。

#### 1、wrap_tool_call：工具抛错时不让 Agent 崩溃

工具函数在真实业务里会失败——数据库连不上、外部 API 超时、参数非法。如果不处理，工具一抛异常，整个 Agent 就崩了。`wrap_tool_call` 把一次工具调用包在中间，能捕获工具抛出的异常、转换成一条正常的工具结果喂回模型，让 Agent 优雅地继续而不是崩溃。

这里有一个实操中真实踩到、值得重点标注的坑——`wrap_tool_call` 的 handler 签名。它的完整签名是：

```python
fn(request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage]) -> ToolMessage
```

最初想当然地把 `handler` 当成零参数函数 `handler()` 来调，结果触发 `TypeError: execute() missing 1 required positional argument`。查 `langchain.agents.middleware.types` 源码（约第 2047 行）才确认：`handler` 需要把 `request` 传回去——正确写法是 `handler(request)`。这条经验提示：包裹 hook 的签名和节点 hook（`fn(state, runtime)`）完全不同，挂之前务必确认真实签名，不能凭装饰器式的印象去猜。

```python
# step6_wrap_tool_call.py（节选）
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

@wrap_tool_call
def handle_tool_error(request, handler):
    try:
        return handler(request)          # 注意：handler 要传 request，不是 handler()
    except Exception as e:
        # 工具抛错 → 转成一条 ToolMessage 喂回模型，Agent 不崩溃
        return ToolMessage(
            content=f"工具执行失败：{e}，建议稍后重试",
            tool_call_id=request.tool_call["id"],   # 必须带，否则模型报 400
        )
```

返回的 `ToolMessage` 有一个**必须带**的字段：`tool_call_id=request.tool_call["id"]`。它把这条结果和模型发起的工具调用请求对应起来——如案例 1 讲过的，工具结果靠 `tool_call_id` 路由回正确的请求。漏掉这个字段，模型会因为「有工具调用却没有对应结果」而返回 400 错误。

```bash
python step6_wrap_tool_call.py
```

![终端输出 step6_wrap_tool_call.py：fragile_query('ERROR') 直接调用抛 ValueError + handle_tool_error 类型为 AgentMiddleware 子类 + 测试1正常完成消息数4 + 测试2捕获 ValueError 转 ToolMessage + agent 未崩溃最终回答建议重试](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step6-wrap-tool-call.png)

实测两种情况：

- **测试 1（工具正常）**：`wrap_tool_call` 透明传递，Agent 正常完成，消息数 4，和没挂 middleware 时一样；
- **测试 2（工具抛错）**：故意让 `fragile_query("ERROR")` 抛 `ValueError`，`wrap_tool_call` 捕获异常、转成一条「工具执行失败，建议稍后重试」的 `ToolMessage` 喂回模型，DeepSeek 拿到这条结果后优雅地回答「建议稍后重试」——**整个 Agent 没有崩溃**。

这里也能看到 `wrap_tool_call` 和 `before_model` 的两个本质差异：返回值类型不同（`wrap_tool_call` 返回 `ToolMessage`，`before_model` 返回 `dict | None`）；职责层次不同（`wrap_tool_call` 处理工具执行错误，模型层面的错误归 `wrap_model_call` / `before_model` 管）。顺带一提，`@wrap_tool_call` 装饰器和 `@before_model` 一样，背后也是动态创建 `AgentMiddleware` 子类。

#### 2、jump_to：让 Agent 在调模型前提前退出

`wrap_tool_call` 是在工具层接管，更进一步的控制是让 Agent **根本不调模型就提前结束**。`before_model` hook 配合 `jump_to` 返回值就能做到——典型场景是合规拦截：用户消息里出现违禁词时，不必把它送给模型，直接返回一条拦截消息、结束循环，既合规又省一次模型调用的成本。

```python
# ext4_jump_to_early_exit.py（节选）
from langchain.agents.middleware import before_model, hook_config
from langchain_core.messages import AIMessage

@before_model
@hook_config(can_jump_to=["end"])    # 必须显式声明跳转权限
def content_filter(state, runtime):
    last = state["messages"][-1].content
    if "退款" in last:               # 命中违禁词
        print("[ContentFilter] 检测到违禁词「退款」→ jump_to=end")
        return {
            "messages": [AIMessage(content="您的问题包含敏感词「退款」，已被自动拦截，请联系人工客服。")],
            "jump_to": "end",        # 直接跳到结束，模型不被调用
        }
    return None                      # 未命中 → 正常流程
```

两个关键点：其一，要用 `jump_to` 必须先用 `@hook_config(can_jump_to=["end"])` 显式声明跳转权限，否则运行时报错——这是框架防止误用跳转的安全设计；其二，`before_model` 返回一个含 `jump_to` 的 `dict`（这正是第三章说的「返回 dict 可修改状态」），同时可以注入一条自定义 `AIMessage` 作为拦截回复。

```bash
python ext4_jump_to_early_exit.py
```

![终端输出 ext4_jump_to_early_exit.py：测试1正常问题消息总数4，测试2含违禁词退款触发 ContentFilter 直接 jump_to=end 消息总数仅2（模型从未被调用），jump_to 用法总结与 ModelCallLimitMiddleware 对比](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--extension-4-jump-to-early-exit.png)

效果对比鲜明：

- **正常问题**：4 条消息（Human → AI(工具调用) → Tool → AI(最终回答)），完整走完工具调用循环；
- **含违禁词的问题**：只有 2 条消息（Human → AI(拦截消息)）。模型**从未被调用**——`before_model` 在调模型前就拦截了，注入拦截消息后直接 `jump_to="end"`，省下了一次 LLM 调用。

`jump_to` 和第四章的 `ModelCallLimitMiddleware` 形成一组互补：`ModelCallLimitMiddleware` 是内置的自动限流（按次数机械地拦），`jump_to` 是基于业务逻辑的自定义退出（按内容灵活地拦，还能注入任意自定义回复）。两者印证了同一件事——middleware 不只是旁观者，它握有改变 Agent 执行路径的能力。

---

### 七、换 agent 即复用：middleware 与业务解耦

middleware 的价值最终要落到「复用」上——同一段横切逻辑写一次，能挂到任意 Agent。本章验证这个关键命题：把一个审计 middleware 挂到两个工具集完全不同的 Agent 上，看它是否都能正常工作、且互不干扰。

```python
# step7_middleware_reuse.py（节选）
class AuditMiddleware(AgentMiddleware):
    def __init__(self, name):
        self.name = name
        self.call_count = 0
    def before_model(self, state, runtime):
        self.call_count += 1
        print(f"[before_model] [{self.name}] 第 {self.call_count} 次")

# Agent 1：订单助手
audit1 = AuditMiddleware("订单助手")
agent1 = create_agent(model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping], middleware=[audit1])

# Agent 2：运营助手（工具集完全不同）
audit2 = AuditMiddleware("运营助手")
agent2 = create_agent(model="deepseek:deepseek-chat",
    tools=[calc_shipping_fee, query_inventory], middleware=[audit2])
```

```bash
python step7_middleware_reuse.py
```

![终端输出 step7_middleware_reuse.py：AuditMiddleware 父类 AgentMiddleware + agent1[订单助手]触发 before_model 2 次/after_model 显示工具调用 query_order,track_shipping + agent2[运营助手]同格式 2 次/工具 calc_shipping_fee,query_inventory + 复用小结 audit1.call_count=2/audit2.call_count=2](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-3--shot--step7-middleware-reuse.png)

复用验证通过，几个结论清晰：

1. **同一个 `AuditMiddleware` 类，挂到两个工具集完全不同的 Agent 都正常触发**——订单助手（`query_order` + `track_shipping`）和运营助手（`calc_shipping_fee` + `query_inventory`）各自的 `before_model` 都按预期触发了 2 次；
2. **实例状态互相独立**：`audit1.call_count` 和 `audit2.call_count` 各自计数（都是 2），两个实例不互相干扰——这正是第三章「类式 middleware 可携带实例状态」的实战价值；
3. **`after_model` 里能看到模型这一轮决定调哪些工具**（通过 `state["messages"][-1].tool_calls`），审计逻辑因此能记录每个 Agent 的真实行为。

这就完成了 middleware 的核心论证：**横切逻辑从「在每个 Agent 里复制粘贴」变成了「写一次、声明式注册到任意 Agent」**。middleware 与 Agent 的具体业务（工具集、提示词）完全解耦——同一个审计、限流、脱敏 middleware，可以原样挂到订单助手、运营助手，乃至后续案例里的检索增强 Agent、深度 Agent 上。

---

### 八、自学迁移指南：把示例 middleware 换成你的横切逻辑

本案例用日志、限流、脱敏、审计几个示例跑通了 middleware 机制，但这套机制与这些具体逻辑无关。要把它迁移到自己的横切需求（自定义限速、操作审计、内容合规、成本控制等），关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的横切逻辑）

需要改写的只有 middleware 内部的 hook 逻辑，挂载方式不变：

- **选 hook**：先确定你的逻辑该挂在哪个时机。要在调模型前做的（脱敏、前置检查、合规拦截）挂 `before_model`；调模型后做的（统计 token、记录决策）挂 `after_model`；工具错误处理挂 `wrap_tool_call`；模型降级、最后一刻改写请求挂 `wrap_model_call`；整个循环头尾各一次的初始化和收尾挂 `before_agent` / `after_agent`；
- **写 hook 体**：换成你的真实逻辑。本案例打印日志，真实业务里这里可以写文件、调审计系统、查限速配额、对接合规接口；
- **选写法**：单 hook、无状态用装饰器式（`@before_model`）最省事；多 hook 或需要跨调用累积状态（如计数、配额）用类式（继承 `AgentMiddleware`）。

下面是「示例日志 middleware → 你的审计 middleware」的最小改写骨架，对照着改即可：

```python
# 改之前（本案例的示例日志 middleware）
@before_model
def log_before(state, runtime):
    print(f"[before_model] 消息数={len(state['messages'])}")
    return None

# 改之后（换成你的业务：把每次模型调用写入审计文件）
class FileAuditMiddleware(AgentMiddleware):
    def __init__(self, log_path):
        self.log_path = log_path
    def before_model(self, state, runtime):
        with open(self.log_path, "a") as f:           # 换成你的真实逻辑
            f.write(f"{datetime.now()} 调用模型，消息数={len(state['messages'])}\n")
        return None
```

可以看到，hook 体、写法（这里因为要带 `log_path` 状态而改用类式）都换成了业务相关内容，但「实现哪个 hook 方法 + 返回 `None` 表示继续」这套规范一字未变——把改写后的 middleware 放进 `create_agent` 的 `middleware=[]` 列表，Agent 就拥有了新的横切能力。

#### 2、保持不变的部分（结构骨架）

下面这些不需要改动，它们是迁移后依然成立的骨架：

- **挂载方式**：`create_agent(..., middleware=[...])` 把 middleware 放进列表声明挂载，工具函数和系统提示词一行不改；
- **6 个 hook 的触发时机**：`before_*` / `after_*` / `wrap_*` 各自的触发时刻固定，与你的具体逻辑无关；
- **执行顺序铁律**：多个 middleware 同挂时，`before_*` 正序、`after_*` 逆序、`wrap_*` 嵌套——这条规律不随 hook 类型和 middleware 数量改变，列表顺序就是你安排依赖关系的开关；
- **解耦特性**：同一 middleware 可挂到任意 Agent，实例状态互相独立。

#### 3、迁移后如何验证跑通

换完 middleware 后，按本案例的方式自检，确认迁移成功：

1. **触发验证**：挂上你的 middleware，跑一个含工具调用的问题，确认 hook 按预期触发——注意含一次工具调用的问题会触发**两轮** `before_model` / `after_model`，别误以为触发了多余的次数；
2. **顺序验证**：同时挂 3 个 middleware，各 hook 打印自己的标识，确认 `before_*` 正序、`after_*` 逆序，与本案例第五章的序列一致；
3. **复用验证**：把同一 middleware 挂到另一个工具集不同的 Agent，确认无需改 middleware 代码、它就能在新 Agent 上正常工作，且实例状态互不干扰。

三项都通过，就说明你的横切逻辑在 middleware 机制上完整跑通了。

#### 4、迁移前置假设清单

迁移顺利的前提是具备以下条件，动手前先核对：

- **已掌握案例 1 的 `create_agent`**：middleware 是挂在 `create_agent` 之上的一层，工具调用循环、消息流（`HumanMessage` / `AIMessage` / `ToolMessage`）这些概念若还不熟，建议先回到案例 1；本案例的工具集也直接复用案例 1 的 `tools.py`；
- **会写 Python 装饰器与类**：装饰器式 middleware 需要理解「装饰器给函数包一层」，类式 middleware 需要会继承基类、用 `__init__` 维护实例状态。不需要精通，但要能读懂这两种写法；
- **分清 hook 签名差异不是默认知识**：节点 hook 是 `fn(state, runtime)`、包裹 hook 是 `fn(request, handler)`，两者完全不同。迁移时若遇到 `TypeError`，先回头确认挂的 hook 真实签名（必要时查 `langchain.agents.middleware.types` 源码），不要凭印象套用；
- **内置 middleware 参数风格不统一**：用内置 middleware 前确认它的真实签名——例如 `ModelCallLimitMiddleware` 用关键字参数（`run_limit=2`），而 `ModelFallbackMiddleware` 用位置参数（`first_model, *additional_models`），不能假设都用 kwargs。

把这几点核对清楚，本案例的示例 middleware 就能稳妥地迁移成你自己业务的横切逻辑层。


---

## LangChain 持久化记忆：让 Agent 记住多轮对话从零到一跑通实操手册

### 一、开篇：从「一问一答的健忘」到「有记忆的连续会话」

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)。它的底层图执行引擎是 LangGraph（[github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)），本案例要用到的记忆机制正是由 LangGraph 提供。

用 `create_agent` 搭起来的 Agent（智能体），默认是**无状态**的——每一次 `invoke` 调用都是独立的一问一答，模型不记得上一轮说过什么。这在很多场景里会立刻暴露问题：一个订单客服助手，用户第一句报了订单号 A1001，第二句问「我刚说的订单号是什么」，无状态的 Agent 只能回答「您还没有告诉我订单号」。它不是答错，而是**根本没有「上一句」的概念**。

打个日常的比方：无状态的 Agent 像一个患了健忘症的客服，每接一句话都像第一次见到你，永远要你从头报一遍信息。本案例要做的，是给这个客服装上「记事本」——让它在同一个会话里记住前文，把「一问一答」升级成「连续对话」；同时还要保证不同用户的记事本互不混淆，张三的订单号绝不会串到李四的会话里。

实现这套记忆机制，靠的是两个核心对象：

- **checkpointer（检查点存储器）**：Agent 每走完一步，就把当前的完整对话状态存一份档。下一次调用时，框架自动把存档读回来接着跑。它是「记事本」的本体。
- **thread_id（会话线程标识）**：每一个独立会话用一个 `thread_id` 区分。同一个 `thread_id` 的多次调用共享一段记忆，不同 `thread_id` 之间彼此隔离。它是「这是谁的记事本」的索引。

本案例在案例 1 的基础上展开——沿用案例 1 已经写好的 `create_agent` 与工具集 `tools.py`（`query_order` 查订单、`track_shipping` 查物流、`calc_shipping_fee` 算运费），不重复讲工具调用循环本身，只聚焦「持久化记忆」这一层。改动其实只有一处：给 `create_agent` 多传一个 `checkpointer` 参数。下文按「加 checkpointer → 验证多轮记忆 → 打开 checkpoint 看内部 → 验证 thread 隔离 → 升级持久化存储 → 换业务复用」的顺序推进，每一步都有真实终端输出佐证。

---

### 二、准备工作：复用案例 1 的 Agent，加一个 checkpointer 参数

#### 1、确认环境与 InMemorySaver 就位

本案例沿用案例 1 的工作目录与 Python 虚拟环境（venv），框架版本为 `langchain` 1.3.2、`langgraph` 1.2.2、Python 3.13.13。多轮记忆所需的 `InMemorySaver`（内存检查点存储器）随 `langgraph` 一并安装，无需额外装包——它是开发阶段最常用的 checkpointer，把对话状态存在进程内存里。

`InMemorySaver` 的 import 路径在 `langgraph.checkpoint.memory` 下。运行实操前，先确认它能正常导入：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
```

若读者从零起步、本机尚无此环境，完整路径为：用 `python -m venv .venv` 创建虚拟环境，`source .venv/bin/activate` 激活，再 `pip install langchain langchain-deepseek` 安装核心依赖（`langgraph` 会作为依赖被自动拉取，`InMemorySaver` 随之就位）。此外需要一个 DeepSeek API Key——在 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取后，通过环境变量 `export DEEPSEEK_API_KEY=你的key` 注入。模型选 `deepseek-chat`（支持工具调用），而非 `deepseek-reasoner`。

#### 2、给 create_agent 传 checkpointer=InMemorySaver()

让 Agent 具备记忆能力，唯一的代码改动是在 `create_agent` 里多传一个 `checkpointer` 参数。新建 `step1_checkpointer_agent.py`，把案例 1 的 Agent 组装方式原样搬过来，只加这一行：

```python
# step1_checkpointer_agent.py
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import query_order, track_shipping, calc_shipping_fee

checkpointer = InMemorySaver()                       # 新增：实例化内存检查点存储器

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
    checkpointer=checkpointer,                        # 新增：把 checkpointer 挂上去
)
print("agent 类型:", type(agent).__name__)
print("agent.checkpointer:", type(agent.checkpointer).__name__)
```

运行验证 Agent 能正常组装、`checkpointer` 已挂载：

```bash
cd "工作目录" && source .venv/bin/activate
python step1_checkpointer_agent.py
```

![终端输出：InMemorySaver 实例化成功，模块路径 langgraph.checkpoint.memory；create_agent + checkpointer 组装成功，返回 CompiledStateGraph；agent.checkpointer 已挂载，类型为 InMemorySaver；结论行三个绿色勾](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step1-agent-with-checkpointer.png)

```
[OK] InMemorySaver 实例化成功: <class 'langgraph.checkpoint.memory.InMemorySaver'>
[OK] create_agent + checkpointer 组装成功: <class 'langgraph.graph.state.CompiledStateGraph'>
[OK] agent 类型: CompiledStateGraph
[OK] agent.checkpointer 已挂载: <class 'langgraph.checkpoint.memory.InMemorySaver'>
```

这里有一个值得记下的细节：**加了 checkpointer 之后，`create_agent` 的返回类型仍然是 `CompiledStateGraph`，与案例 1 不加 checkpointer 时完全一致**。也就是说，记忆能力不改变 Agent 的对象类型，`invoke` / `stream` / `get_state` 这些方法都照常可用——记忆是「叠加」上去的能力，不是另起一套 API。同时，挂上去的 checkpointer 可以通过 `agent.checkpointer` 直接访问，类型正是 `InMemorySaver`。

光挂上 checkpointer 还不够，真正触发记忆的开关是调用时传入的 `thread_id`——下一章就会用到。

---

### 三、多轮记忆实操：同一 thread_id 记住前文

#### 1、第一轮：告知订单号 A1001

记忆的开关在 `invoke` 的第二个参数 `config` 里。`config` 是一个嵌套字典，把会话标识放在 `configurable.thread_id` 下：

```python
config_u1 = {"configurable": {"thread_id": "u1"}}    # u1 是这次会话的线程标识

# Round 1：用户告知订单号
result = agent.invoke(
    {"messages": [{"role": "user", "content": "你好，我的订单号是 A1001，请帮我记住。"}]},
    config_u1,                                         # 关键：带上 config
)
```

`step2_multi_turn.py` 在同一个 `thread_id=u1` 下连跑三轮对话。第一轮先让用户报出订单号 A1001：

```bash
python step2_multi_turn.py
```

![三轮对话终端输出：Round 1 用户告知订单号 A1001，Agent 回复「我已记住你的订单号是 A1001」；Round 2 用户问「我刚说的订单号是什么」，Agent 答 A1001 并显示 PASS；Round 3 用户说「帮我查一下这个订单的状态」未重提订单号，Agent 自主用 A1001 查询；底部统计 thread_id=u1 总消息数 8、actual_turns 3](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step2-first-turn.png)

```
=== Round 1: thread_id=u1 · 告知订单号 ===
用户: 你好，我是客户小明，我的订单号是 A1001，请帮我记住。
Agent: 好的，小明！我已记住你的订单号是 **A1001**。
```

到这里，第一轮对话产生的消息（用户那句话 + Agent 的回复）已经被 `InMemorySaver` 以 `thread_id=u1` 为键存了档。真正要验证的，是第二轮调用时这段历史能不能被自动读回来。

#### 2、第二轮：不重提订单号，验证 Agent 记住 A1001

第二轮用**同一个 `config_u1`** 再次 `invoke`，这次直接问「我刚说的订单号是什么」，故意不再提 A1001：

```python
# Round 2：复用同一个 config_u1，问一个依赖前文的问题
result = agent.invoke(
    {"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]},
    config_u1,                                         # 与 Round 1 同一个 thread_id
)
```

这是整个案例最核心的一步：

![终端显示：用户问「我刚才说的订单号是什么？」，Agent 回答「你刚才说的订单号是 A1001」并显示 PASS 绿色勾「agent 记住了 A1001，多轮记忆验证通过」；底部原理解读说明 checkpointer 在每个 super-step 边界存档、thread_id 是会话主键、第二轮 invoke 时 langgraph 自动从 InMemorySaver 加载历史](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step3-remembers.png)

```
用户: 我刚才说的订单号是什么？
Agent: 你刚才说的订单号是 **A1001** 😊 有什么需要我帮忙的吗？
[PASS] ✅ agent 记住了 A1001！多轮记忆验证通过
```

Agent 答出了 A1001，而这一轮的输入里**根本没有这个订单号**。它从哪里知道的？这背后的机制是本案例的原理核心，值得拆清楚：

1. **checkpointer 在每个 super-step 边界存档**：LangGraph 把一次 `invoke` 的执行拆成若干个 super-step（超步，图执行的最小推进单位），每走完一个 super-step，checkpointer 就把当前的完整对话状态（含全部 messages）存一份档。第一轮跑完，A1001 那段对话已经在档里了。
2. **thread_id 是会话主键**：`InMemorySaver` 内部以 `thread_id` 为键存储不同会话的状态。第二轮传入同一个 `config_u1`，框架据此找到 `thread_id=u1` 的存档。
3. **第二轮自动加载历史**：第二轮 `invoke` 时，LangGraph 先从 `InMemorySaver` 把 `thread_id=u1` 的历史消息读回来，拼在这一轮的新消息前面，再一起交给模型。于是模型看到的不是孤零零一句「我刚说的订单号是什么」，而是包含第一轮的完整对话。

一句话概括：**记忆不是模型「记住」的，是 checkpointer 把历史存下来、每轮调用前自动回填给模型的**。模型本身依然无状态，有状态的是 checkpointer 这个外部存储。

#### 3、第三轮：累积上下文，自主调用工具

第三轮进一步验证记忆的「累积」效果。用户说「帮我查一下这个订单的状态」——这里的「这个订单」依然没点名，指代的正是前两轮反复出现的 A1001：

```
=== Round 3: thread_id=u1 · 第三轮追问（累积记忆验证）===
用户: 帮我查一下这个订单的状态。
Agent: 订单 **A1001** 的当前状态是：**已发货**，预计**明天到达**！🎉
```

如 step2 截图底部所示，三轮跑完，`thread_id=u1` 的存档里累积了 8 条消息，`actual_turns: 3`。这一轮 Agent 做了两件事：先从历史里认出「这个订单」= A1001，再自主调用案例 1 的 `query_order` 工具去查状态。可见记忆与工具调用循环是叠加生效的——模型既利用了 checkpointer 回填的上下文，又走了完整的工具调用循环。

---

### 四、打开 checkpoint 引擎盖：get_state 看快照

多轮记忆跑通后，自然的问题是：**checkpoint 里到底存了什么？** Agent 提供了 `get_state(config)` 方法，能把指定 `thread_id` 当前的存档原样打印出来。

#### 1、get_state 返回 StateSnapshot

`step4_get_state.py` 先建立两轮对话（查 A1001 状态、查 A1002 物流），再调用 `agent.get_state(config)` 打印这份存档的全部字段：

```python
snapshot = agent.get_state(config_u1)
print("StateSnapshot 字段:", list(snapshot._fields))
print("messages 总数:", len(snapshot.values["messages"]))
print("next =", snapshot.next)
```

```bash
python step4_get_state.py
```

![终端显示 get_state 返回 StateSnapshot 类型；StateSnapshot 共 8 个字段 values/next/config/metadata/created_at/parent_config/tasks/interrupts；values.messages 含 8 条消息（human/ai/tool 类型全部可见）；next=() 表示对话已结束处于 END 节点；config 含 thread_id=u1 + checkpoint_id UUID；metadata 含 source=loop step=8 ls_integration=langchain_create_agent；结论行四个绿色勾](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step4-checkpoint-snapshot.png)

```
[OK] get_state 返回类型: <class 'langgraph.types.StateSnapshot'>
[OK] StateSnapshot 字段: ['values', 'next', 'config', 'metadata', 'created_at', 'parent_config', 'tasks', 'interrupts']

--- values (当前 State) ---
  messages 总数: 8
--- next (下一步执行节点) ---
  next = ()                            ← 对话已结束，处于 END 节点
--- config (含 checkpoint_id) ---
  checkpoint_id = 1f15c0d0-a392-65ea-8008-926dc03d7383
--- metadata (checkpoint 元信息) ---
  metadata = {'source': 'loop', 'step': 8, ..., 'ls_integration': 'langchain_create_agent'}
```

`get_state` 返回的是一个 `StateSnapshot`（状态快照），共 8 个字段，每个字段的含义如下：

| 字段 | 含义 |
| --- | --- |
| `values` | 当前对话状态，核心是 `values["messages"]`——完整的消息历史 |
| `next` | 下一步要执行的图节点。`()` 表示对话已到终点（END），无待执行节点 |
| `config` | 本快照的定位信息，含 `thread_id` 与 `checkpoint_id`（每个快照的唯一 UUID） |
| `metadata` | 元信息，含 `source`、`step`（第几个 super-step）等 |
| `created_at` | 快照创建时间 |
| `parent_config` | 上一个快照的 config，快照之间靠它串成链 |
| `tasks` | 待执行任务（本案例为空，人在回路 HITL 场景会有值） |
| `interrupts` | 中断点（本案例为空，HITL 场景会有值） |

有两个字段尤其值得说清楚。

其一是 **`next`**。它揭示了 Agent 当前停在图执行的哪一步：`next=()` 表示对话处于终态（END，已经吐出最终回答）；`next=('model',)` 表示停在「等待模型」；`next=('tools',)` 表示停在「等待工具执行」。这个字段在后面的「时间旅行」一节会变成一条硬约束。

其二是 **`metadata.ls_integration`**，它的值是 `'langchain_create_agent'`。这条元信息坐实了一个底层事实：**`create_agent` 不是独立实现，它底层就是 LangGraph**。案例 1 里看到的返回类型 `CompiledStateGraph` 是 LangGraph 的类，这里的 checkpoint 机制也是 LangGraph 的能力——`create_agent` 是 LangGraph 之上的一层便捷封装。

#### 2、get_state_history：看完整时间线

`get_state` 看到的是「当前」一份快照。如果想看「从头到尾每一步」的全部快照，用 `get_state_history(config)`。`ext4_inspect_checkpoint.py` 先跑两轮带工具调用的对话，再展开 `values["messages"]` 的全量结构与历史快照时间线：

```python
# 全量 messages
for i, m in enumerate(snapshot.values["messages"]):
    print(f"[{i:02d}] type={type(m).__name__}")

# 历史快照
for h in agent.get_state_history(config):
    print(f"step={h.metadata['step']}  checkpoint_id={h.config['configurable']['checkpoint_id']}")
```

![终端显示 get_state 全量 messages 结构：8 条消息含 human/ai/tool 四种类型，调工具的 ai 消息 content 为空并携带 tool_calls 字段，tool 消息为工具返回结果；下半部 get_state_history 列出 10 个快照时间线，step -1 到 step 8，每个 super-step 对应一个 checkpoint_id UUID](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--extension-1-inspect-checkpoint.png)

```
[00] type=human   → 查一下 A1001 的状态。
[01] type=ai      → tool_calls: ['query_order'] | content: (empty)
[02] type=tool    → 已发货 · 预计明天到达
[03] type=ai      → 订单 A1001 当前状态为：已发货...
[04] type=human   → 再查 A1002 的物流。
[05] type=ai      → tool_calls: ['track_shipping'] | content: (empty)
[06] type=tool    → 暂无物流信息，商品尚未发货
[07] type=ai      → 订单 A1002 目前暂无物流信息...
```

展开到这一层，checkpoint 的存储真相就清楚了：

1. **checkpoint 存的是完整 messages 列表，不是「对话摘要」**。每条消息原样保留，包括模型调工具时的「思考」（藏在 `tool_calls` 字段里）和工具的返回结果（`tool` 类型消息）。messages 里有四种 type：`human`（用户输入）、`ai`（模型回复，调工具时 `content` 为空、携带 `tool_calls`）、`tool`（工具返回）、`ai`（最终文字回复）。一次工具调用在 messages 里占 3 条（ai + tool + ai）。
2. **`get_state_history` 倒序返回**：`history[0]` 是最新快照，`history[-1]` 是 `step=-1` 的初始空快照。本例两轮对话共产生 10 个快照（step −1 到 8）。
3. **每个 super-step 对应一个 `checkpoint_id`**：`checkpoint_id` 是 UUID，是定位某一历史时刻的锚点——下一节的时间旅行就靠它。

#### 3、时间旅行：从历史快照重放

既然每个历史时刻都有一个 `checkpoint_id`，那就能「回到过去」：把某个历史快照的 `checkpoint_id` 填进 `config`，从那一刻重新出发继续对话。这就是时间旅行（time travel）。

`ext4_time_travel.py` 先跑三轮带工具调用的对话（产生 13 个快照），再选一个历史点重放：

```python
# 从历史快照里挑一个「稳态」快照（next == ()）
stable = [h for h in agent.get_state_history(config) if h.next == ()]
target = stable[-1]                                   # 第一轮结束时的快照

replay_config = {
    "configurable": {
        "thread_id": "xxx",
        "checkpoint_id": target.config["configurable"]["checkpoint_id"],
    }
}
agent.invoke({"messages": [{"role": "user", "content": "我们聊了什么？我的订单号是多少？"}]}, replay_config)
```

![终端显示 13 个快照列表，其中 3 个稳态快照（next=()）用绿色勾标记；从第一轮结束快照（step=3）出发时间旅行，追问「我们聊了什么」，Agent 回复记得 A1001（已发货）但不知道第二轮的 A1002；底部工程铁律三行总结：只能从稳态快照出发](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--extension-4-time-travel.png)

从第一轮结束的快照出发追问「我的订单号是多少」，Agent 回答「您之前问我查询订单 **A1001** 的状态，结果已经显示为已发货」——它记得第一轮的 A1001，却「不知道」第二轮才查的 A1002。这正是时间旅行的语义：从历史点重放，看到的只有那一刻之前的上下文。

这一节藏着一条用实操踩出来的工程铁律，必须讲清楚：

> **时间旅行只能从 `next=()` 的「稳态快照」出发。**

实操中首次尝试，挑的是一个 `next=('tools',)` 的进行中快照——它的最后一条 AI 消息含 `tool_calls`，但还没有对应的 `tool` 返回消息。从这种快照重放，DeepSeek API 直接返回 400 错误：`An assistant message with tool_calls must be followed by tool messages`（带 tool_calls 的助手消息必须跟着 tool 消息）。原因是这种快照停在工具调用循环的「半中间」，状态不完整。

修复办法就是上面代码里的那行 filter：`[h for h in get_state_history(config) if h.next == ()]`，只取对话已经走完整轮、停在终态的稳态快照。记住这条，时间旅行才能稳定工作。

---

### 五、thread_id 隔离：多用户记忆互不串台

前面所有对话都在 `thread_id=u1` 下进行。真实产品同时服务成千上万用户，必须保证 A 用户的记忆绝不串到 B 用户。这一层靠 `thread_id` 隔离实现。

#### 1、换 thread_id=u2，验证不记得 A1001

`step5_isolation.py` 先用 `thread_id=u1` 建立 A1001 的记忆，再换一个全新的 `thread_id=u2` 问同样的问题：

```python
config_u1 = {"configurable": {"thread_id": "u1"}}    # u1：已经知道 A1001
config_u2 = {"configurable": {"thread_id": "u2"}}    # u2：全新会话

# 在 u2 里问「我刚说的订单号是什么」
agent.invoke({"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]}, config_u2)
```

```bash
python step5_isolation.py
```

![终端显示：先用 thread_id=u1 建立 A1001 记忆并确认记得；换 thread_id=u2 全新会话，被问订单号时 Agent 回复「您刚才没有提供订单号哦」；PASS 绿色勾标记 u2 不知道 A1001、两会话记忆互不串台；u2 提供自己订单号 B2002 后建立独立记忆；底部最终隔离验证 u1 与 u2 各 6 条消息、actual_threads 2、结论两个绿色勾](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step5-isolation.png)

```
=== 先用 thread_id=u1 建立 A1001 的记忆 ===
[OK] u1 确认记得 A1001 ✅

=== 换 thread_id=u2 · 全新会话 · 隔离验证 ===
用户(u2): 我刚才说的订单号是什么？
Agent(u2): 您刚才没有提供订单号哦，请问您的订单号是多少？
[PASS] ✅ 隔离验证通过：u2 不知道 A1001，两会话记忆互不串台

actual_threads: 2 (≥ declared minimum 2) ✅
```

同一个 `agent` 实例，只是把 `config` 里的 `thread_id` 从 `u1` 换成 `u2`，记忆就完全隔离了：u2 这个会话被问到订单号时，老老实实回答「您还没提供」。截图后半段还展示了 u2 报出自己的订单号 B2002 后，建立起独立于 u1 的记忆——两个 `thread_id` 各存各的，最终 `thread_id=u1` 与 `thread_id=u2` 的存档各有 6 条消息，`actual_threads: 2`。

#### 2、交叉提问验证不串台

为了把隔离验证得更彻底，`ext4_thread_isolation.py` 让两个用户存入不同信息后**交叉提问**：

```bash
python ext4_thread_isolation.py
```

![终端显示：建立两个独立会话，user-alice 存入北京+A1001，user-bob 存入上海+A1002；交叉提问验证，Alice 被问「我在哪个城市、订单多少」回复 Alice/北京/A1001（正确），Bob 被问同样问题回复上海/A1002（正确）；PASS 绿色勾交叉验证通过 Alice 不知道 Bob 的上海/A1002；底部 user-alice 与 user-bob 各 6 条消息独立、actual_threads 2](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--extension-3-thread-isolation.png)

`user-alice` 存「北京 + A1001」，`user-bob` 存「上海 + A1002」，然后分别问「我在哪个城市、订单号多少」。Alice 的会话准确答出「北京、A1001」，Bob 的会话准确答出「上海、A1002」，谁也不知道对方的信息。这背后的机制是：

1. **`thread_id` 是命名空间（namespace）**：`InMemorySaver` 内部以 `thread_id` 为键存储各自独立的 messages 列表，键不同则内存空间完全隔离。
2. **一个 agent 实例承载无限会话**：不需要为每个用户创建一个 agent。同一个 `agent` + 不同的 `config["configurable"]["thread_id"]`，就是不同用户的独立会话。
3. **生产里的标准写法**：`thread_id = str(user.id)` 是最直接的多用户实现——每个用户的 ID（或邮箱、session token）当作 `thread_id`，天然得到一人一份独立记忆。`thread_id` 不限于 `"u1"`/`"u2"` 这种短串，任意字符串都行。

---

### 六、持久化升级：从 InMemorySaver 到 SqliteSaver

`InMemorySaver` 有一个绕不开的边界：它把状态存在**进程内存**里。进程一退出，内存清空，所有 `thread_id` 的记忆全部消失。开发调试够用，但凡是需要「重启后还记得」的场景——本地演示、生产服务——就得换一档持久化更强的 checkpointer。

#### 1、SqliteSaver：跨进程持久化

`SqliteSaver`（SQLite 检查点存储器）把状态写进一个 SQLite 数据库文件，进程退出后文件还在，重新打开就能恢复记忆。它不随 `langgraph` 默认安装，需要单独装一个包：

```bash
pip install langgraph-checkpoint-sqlite
```

> ⚠️ 注意：SqliteSaver 的 DB 文件必须放在 APFS 主盘（如 `/tmp/` 或 `~/`），不要放在 ExFAT 格式的外置磁盘上。ExFAT 不支持 POSIX 文件锁，SQLite 的 WAL 模式会失败。本案例实验机器的外置 SSD 恰是 ExFAT，因此 DB 路径选了 `/tmp/`。

`step6_sqlite_saver.py` 分两个阶段验证「跨进程持久化」：阶段 1 用 `SqliteSaver` 建立含 A1003 的对话并落盘，阶段 2 重新打开同一个 DB（模拟进程重启）再问订单号：

```python
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = "/tmp/langchain_case4_checkpoint.db"        # APFS 主盘路径

# 推荐用 context manager 管理 DB 连接
with SqliteSaver.from_conn_string(db_path) as checkpointer:
    agent = create_agent(model=..., tools=..., checkpointer=checkpointer)
    # ...对话、查询...
```

```bash
python step6_sqlite_saver.py
```

![终端显示：SqliteSaver import OK，路径 langgraph.checkpoint.sqlite，DB 文件位置 /tmp/langchain_case4_checkpoint.db（主盘 APFS）；阶段 1 用 SqliteSaver 建立李四 A1003 对话，checkpoint 落盘 DB 文件 20480 bytes 确认落盘；阶段 2 重新打开 DB 模拟重启后恢复，Agent 回复「您刚才说的订单号是 A1003」；PASS 绿色勾 SqliteSaver 跨进程持久化验证通过、重启后仍记得 A1003；底部对比总结 InMemorySaver 重启全清 vs SqliteSaver 磁盘持久化重启保留](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step6-sqlite-restart.png)

```
=== 阶段 1: 用 SqliteSaver 建立对话 ===
用户: 我是李四，我的订单是 A1003。
[OK] checkpoint 已落盘，messages 数: 2
[OK] DB 文件大小: 20480 bytes (20.0 KB) — 确认落盘

=== 阶段 2: 重新打开 DB（模拟重启后恢复）===
用户: 我刚才说的订单号是多少？（新进程实例、重新打开 DB）
Agent: 您刚才说的订单号是 **A1003**。
[PASS] ✅ SqliteSaver 跨进程持久化验证通过！重启后仍记得 A1003
```

阶段 2 是一个**全新的 agent 实例、重新打开的 DB 连接**，却答出了阶段 1 才说过的 A1003——记忆跨进程留存了下来。这里最值得注意的是迁移成本：从 `InMemorySaver` 换到 `SqliteSaver`，**只改 `checkpointer=` 这一个参数**，`invoke` / `get_state` / `get_state_history` 这些调用代码一行不动。接口完全统一是 checkpointer 体系的设计要点。

#### 2、重启丢 vs 重启留：对比验证

为了说清「为什么需要 SqliteSaver」，`ext4_memory_vs_sqlite.py` 把两档 checkpointer 放在一起对比，各自模拟一次「重启」：

```bash
python ext4_memory_vs_sqlite.py
```

![终端显示对比：对比 1 InMemorySaver 重启记忆丢失，进程 1 告知 A1001，进程 2 新实例模拟重启后询问，Agent 回复「您没有提供订单号」，OK 符合预期重启后忘了 A1001；对比 2 SqliteSaver 重启记忆保留，进程 1 告知 A1001 DB 4096 bytes 落盘，进程 2 重新打开同 DB 询问，Agent 回复「您之前提到的订单号是 A1001」，OK 持久化生效；底部对比总结表格列出 InMemorySaver 与 SqliteSaver 重启前后差异、迁移成本 checkpointer 一行替换](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--extension-2-memory-vs-sqlite.png)

对比结果一目了然：

- **`InMemorySaver` 的「重启」** = 新建一个 `InMemorySaver` 实例。原来的内存状态完全消失，进程 2 问订单号时 Agent 回答「您没有提供订单号」——符合预期，内存档随进程而逝。
- **`SqliteSaver` 的「重启」** = 重新 `SqliteSaver.from_conn_string(同一个 DB 路径)`。SQLite 文件保留了所有 checkpoint，进程 2 加载后无缝恢复，答出「您之前提到的订单号是 A1001」。

这种「反例对照」恰恰是理解持久化价值的最好载体：先看见 InMemorySaver「忘了」，才能真正体会 SqliteSaver「记得」意味着什么。

#### 3、checkpointer 三档差异

把 checkpointer 的三档放在一起，它们构成一条「开发 → 本地持久 → 生产」的线性升级路径，接口完全一致，只是存储介质不同：

| checkpointer | 存储介质 | 重启后 | 额外安装 | 适用阶段 |
| --- | --- | --- | --- | --- |
| `InMemorySaver` | 进程内存 | 记忆全清 | 无（随 langgraph 自带） | 开发、调试、单元测试 |
| `SqliteSaver` | 本地 SQLite 文件 | 记忆保留 | `pip install langgraph-checkpoint-sqlite` | 本地持久、单机演示 |
| `PostgresSaver` | PostgreSQL 数据库 | 记忆保留 | `pip install langgraph-checkpoint-postgres` | 生产、多实例、高并发 |

选型逻辑很直接：开发阶段图快用 `InMemorySaver`；需要重启不丢用 `SqliteSaver`；上生产、要支撑多实例和高并发就上 `PostgresSaver`。三档之间切换，业务代码不变，只换 `checkpointer=` 这一处。

---

### 七、换数据即换业务：多轮订票偏好复用

本案例前面用「订单客服」场景演示记忆机制，但这套机制与「订单」这个领域无关。最后验证一个关键命题：**把对话内容整个换掉，记忆机制还成立吗？** `step7_reuse_booking.py` 把场景换成「多轮订票」——用户小张分三轮逐步交代订票偏好，看 Agent 能不能累积记住，同时另一个用户小李的会话保持隔离：

```bash
python step7_reuse_booking.py
```

![终端显示：用户小张多轮订票偏好记忆，Round 1 汇总常用路线北京→广州常规重量 2kg，Round 2 未重提路线直接问「这次预估运费」Agent 答北京→广州 2kg 运费 23 元，PASS 换数据复用验证通过 agent 记住小张订票偏好，Round 3 问 5kg 运费答 38 元并给出 2kg/5kg 对比表；用户小李独立会话不知道小张偏好，Round 1 Agent 要求小李提供起始城市目的城市重量，PASS 隔离验证小李不知道小张的北京→广州偏好；底部统计 user-zhang 12 条消息、user-li 2 条、actual_turns 3、actual_threads 2，结论三个绿色勾](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-4--shot--step7-booking-reuse.png)

```
小张 Round 2: 这次从 **北京 → 广州**（2kg）的预估运费是 **23 元**。（无需重提路线）
[PASS] ✅ 换数据复用验证通过：agent 记住小张的订票偏好（北京→广州）

小李 Round 1: 好的！请告诉我起始城市、目的地城市和重量（小李不知道小张偏好）
[PASS] ✅ 隔离验证：小李不知道小张的北京→广州偏好

user-zhang checkpoint messages: 12
user-li   checkpoint messages: 2
actual_turns(zhang): 3 ✅   actual_threads: 2 ✅
```

小张第二轮只说「这次的运费多少」，没重提「北京→广州」，Agent 照样基于第一轮记住的路线算出 23 元；第三轮问 5kg 时还能给出 2kg/5kg 的运费对比。与此同时，小李的会话被问到时老老实实要求「请提供起始城市、目的地、重量」——它对小张的偏好一无所知。

这印证了那个命题：**把对话场景从「查订单」换成「订票」，checkpointer 与 thread_id 的机制原样生效，一行代码不用改**。记忆机制与具体业务领域解耦，换业务等于换对话内容，记忆这一层是稳定的底座。

---

### 八、自学迁移指南：把客服记忆换成你的多轮场景

本案例用订单客服与订票两个场景跑通了持久化记忆，但这套结构能迁移到任何需要「记住多轮上下文」的业务——多轮问诊、多轮选品、多轮表单填写。迁移的关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的业务）

需要改写的只有两处，且都不涉及记忆机制本身：

- **对话内容 / 工具**：把订单场景换成你自己的业务。工具函数（`tools.py`）换成你的业务函数（查病历、查库存、查航班……），对话内容换成你的领域。这一层完全沿用案例 1 的工具规范（带类型注解、带 docstring、返回字符串），与记忆机制无关。
- **thread_id 的取值**：本案例用 `"u1"`/`"u2"` 这种演示串。生产里换成真实的用户标识，最常见的写法是 `thread_id = str(user.id)`，也可以用用户邮箱、会话 token——任意字符串都行，只要保证「同一个会话用同一个值、不同会话用不同值」。

#### 2、保持不变的部分（结构骨架）

下面这些是迁移后依然成立的骨架，原样照搬：

- **挂 checkpointer 的方式**：`create_agent(..., checkpointer=InMemorySaver())` 这一行结构不变，只在需要持久化时把 `InMemorySaver()` 换成 `SqliteSaver` 或 `PostgresSaver`。
- **带 config 调用的方式**：`agent.invoke({"messages": [...]}, {"configurable": {"thread_id": ...}})`——靠 `config` 传 `thread_id` 触发记忆，这个调用形态不变。
- **看 checkpoint 的方式**：`agent.get_state(config)` 看当前快照、`agent.get_state_history(config)` 看历史时间线，调试记忆问题时依然靠它们。
- **隔离的语义**：同一个 agent 实例 + 不同 `thread_id` = 不同用户独立记忆，这条不变。

#### 3、迁移后如何验证跑通

换完业务后，按本案例的验收方式自检，确认迁移成功：

1. **多轮记忆验证**：在同一个 `thread_id` 下连续 `invoke` 至少 3 轮，第二轮起故意不重提前文已交代的关键信息（如订单号 / 病历号 / 航班号），确认 Agent 仍能答出——证明记忆累积生效。
2. **thread 隔离验证**：开两个不同 `thread_id` 的会话，各存不同信息后交叉提问，确认彼此不串台、`actual_threads ≥ 2`。
3. **持久化验证（若用 SqliteSaver）**：建立对话落盘后，新建进程重新打开同一个 DB，确认重启后记忆仍在。

三项都通过，就说明记忆机制在你的业务场景里完整复现。

#### 4、迁移前置知识假设清单

迁移顺利的前提是具备以下条件，动手前先核对。这里分两类：一类是「真前置知识假设」——不具备就会卡住、且不是装个包能解决的；另一类是「基本环境要求」——装包、路径之类的工程准备。

**【真前置知识假设、须先具备】**

- **已掌握案例 1 的 `create_agent` 与工具调用循环**：本案例的 Agent 组装方式、工具集都直接复用案例 1。若 `create_agent`、`messages` 消息流（`HumanMessage` / `AIMessage` / `ToolMessage`）这些概念还不熟，建议先回到案例 1。
- **理解「无状态 vs 有状态」的区别**：不要默认「模型自己会记住上一句」——模型本身是无状态的，记忆来自外部的 checkpointer。迁移时若 Agent「忘了」前文，先确认两点：是不是漏传了 `checkpointer`，或者两次调用的 `thread_id` 是不是同一个。

**【基本环境要求、动手前准备】**

- **用 SqliteSaver 时会装额外的包，并注意 DB 落盘位置**：`pip install langgraph-checkpoint-sqlite` 不能省；DB 文件放 APFS 主盘，避开 ExFAT 等不支持 POSIX 文件锁的文件系统，否则 SQLite 会报锁相关的错误。
- **时间旅行时只从稳态快照出发**：用 `get_state_history` 做重放时，记得 filter 出 `next=()` 的稳态快照，从含未完成 `tool_calls` 的进行中快照重放会被模型 API 拒绝（返回 400）。

把这几点核对清楚，本案例的客服记忆就能稳妥地迁移成你自己业务的有记忆 Agent。


---

## LangChain 人在回路（Human-in-the-Loop）：让 Agent 在危险动作前暂停等人审批从零到一跑通实操手册

### 一、开篇：从「Agent 自作主张」到「危险动作前先让人点头」

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)。它的底层图执行引擎是 LangGraph（[github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)），本案例要用到的「人在回路」（Human-in-the-Loop，简称 HITL，指在自动化流程中插入人工决策环节）机制，正是由 LangGraph 提供。

前面的案例已经把 Agent（智能体）搭成了一个能自主调用工具的执行体——它会自己决定调哪个工具、传什么参数。但「自主」有时正是风险所在。设想一个订单客服 Agent，用户说「给我退款」，Agent 判断属实后，**直接就调用了退款工具，钱当场打了出去**。退款、转账、删除数据、对外发邮件，这类动作有一个共同特征：执行了就收不回来。把这种不可逆的决定权完全交给模型，在生产系统里是不可接受的。

人在回路要解决的就是这个问题：让 Agent 在执行危险动作**之前**停下来，把「我打算退这笔款，金额 299 元，订单 A1001，批不批」这件事抛给人工，等人点了头再继续；人若否决，这笔退款就不执行。整个过程像是给 Agent 的危险操作加了一道审批闸门——闸门没开，钱出不去。

实现这套机制，靠的是三个核心对象：

- **interrupt（中断）**：在工具内部调用，作用是让图（graph，LangGraph 把 Agent 的执行流建模成一张状态图）执行到此处暂停，并把需要人工过目的信息抛出来。它是「闸门」本身。
- **Command(resume=...)（续跑指令）**：人工做完决定后，用它把审批结果（批准 / 拒绝）回传给暂停的图，让图从断点继续往下跑。它是「开闸 / 关闸的钥匙」。
- **checkpointer（检查点存储器）**：图暂停时，当前的完整执行状态必须有地方存档，否则人工审批的这段时间里状态就丢了。checkpointer 负责把暂停点的状态保存下来，续跑时再读回来。**这是人在回路的硬前提——没有 checkpointer，interrupt 无法暂停。**

本案例在案例 4（持久化记忆）的基础上展开。案例 4 已经讲清了 checkpointer 与 `InMemorySaver`（内存检查点存储器）的用法，本案例直接复用那套配置，不再重复讲存储原理，只聚焦「暂停 → 审批 → 续跑」这条审批回路。下文按「搭好带审批的 Agent → 触发暂停 → 看清待审批内容 → 批准路径 → 拒绝路径 → 四铁律 → 换业务复用」的顺序推进，每一步都有真实终端输出佐证。其中有一个会让多数人意外的行为——续跑时节点会从头重新执行一遍——本案例会用执行日志把它直接摆在眼前。

---

### 二、准备工作：复用案例 4 的 Agent，加一个 mock 危险工具

#### 1、确认环境与 interrupt / Command 就位

本案例沿用案例 1、案例 4 的工作目录与 Python 虚拟环境（venv），框架版本为 `langchain` 1.3.2、`langgraph` 1.2.2、Python 3.13.13。人在回路所需的 `interrupt` 与 `Command` 都在 `langgraph.types` 模块下，随 `langgraph` 一并安装，无需额外装包。`InMemorySaver` 的用法与案例 4 完全一致。

若读者从零起步、本机尚无此环境，完整路径为：用 `python -m venv .venv` 创建虚拟环境，`source .venv/bin/activate` 激活，再 `pip install langchain langchain-deepseek` 安装核心依赖（`langgraph` 会作为依赖被自动拉取）。此外需要一个 DeepSeek API Key——在 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取后，通过环境变量 `export DEEPSEEK_API_KEY=你的key` 注入。模型选 `deepseek-chat`（支持工具调用），而非 `deepseek-reasoner`。

这里要先澄清一个容易混淆的点：`interrupt` **是一个函数对象**（`langgraph.types.interrupt`），不是异常类，调用方式是 `interrupt(待审批信息)`。它的内部确实是靠抛异常来实现暂停的（这一点在第七章四铁律会展开，也是反例的根源），但写工具代码时，把它当成一个普通函数调用即可。

新建 `step1_hitl_agent.py`，验证三个核心对象与 checkpointer 全部就位：

```bash
cd "工作目录" && source .venv/bin/activate
python step1_hitl_agent.py
```

![终端输出：InMemorySaver 实例化成功；create_agent + checkpointer 组装返回 CompiledStateGraph；interrupt、Command 从 langgraph.types 导入可用；refund_order 工具就绪，全部 PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step1-hitl-agent-setup.png)

输出确认：`InMemorySaver` 实例化成功，`create_agent` 挂上 `checkpointer` 后返回 `CompiledStateGraph`（已编译状态图），`interrupt` / `Command` 可用，mock 危险工具 `refund_order` 就绪。组装 Agent 的方式与案例 4 一致，唯一新增的是下面这个危险工具。

#### 2、定义 mock 危险工具 refund_order（在工具内调 interrupt）

退款是一个典型的不可逆动作，本案例用它作为「危险工具」的样板。关键设计是：**在工具真正执行退款逻辑之前，先调一次 `interrupt`**，把订单号、金额等信息抛出去等人审批。

```python
from langgraph.types import interrupt
from langchain.tools import tool

@tool
def refund_order(order_id: str, amount: float) -> str:
    """给指定订单退款。order_id 为订单号，amount 为退款金额（元）。"""
    # 关键：执行退款前先暂停，把审批信息抛给人工
    approval = interrupt({
        "action": "refund_order",
        "order_id": order_id,
        "amount": amount,
    })
    # 下面这段只有人工 resume 之后才会真正跑到
    if approval == "approve":
        return f"✅ 退款已执行：{order_id} ¥{amount} 成功"
    else:
        return f"❌ 退款已拒绝：{order_id} ¥{amount} 被驳回"
```

这里有两个要点：第一，`interrupt(dict)` 的参数完全由开发者自定义，传什么、传多少字段都可以——审批界面要展示给运营看的信息，全靠这个 dict 携带；第二，`interrupt()` 的**返回值**就是人工后续通过 `Command(resume=...)` 传回来的值，工具内用它判断走批准还是拒绝分支。这条「值的传递通路」是人在回路信息往返的关键，后面会反复用到。

还有一个实操中务必注意的细节：系统提示词（system prompt）必须明确指示模型在用户要求退款时**直接调用 `refund_order` 工具**。实测中 DeepSeek 有时会自作主张先调用 `query_order` 查一遍订单再思考，迟迟不调退款工具，导致 interrupt 压根没触发。稳妥做法是系统提示词写清「用户要求退款时必须立即调用 refund_order，不需要先查询」，用户消息也用「立即退款」这类明确措辞，而非含糊的「请帮我看看退款」。

---

### 三、触发暂停：invoke 撞上 interrupt

#### 1、invoke 返回含 __interrupt__，而不是把异常抛给调用方

工具就绪后，用 `invoke` 发起一次退款请求，观察图撞上 `interrupt` 时的行为。

```bash
python step2_invoke_interrupt.py
```

![终端输出：invoke 触发退款，返回值含 __interrupt__ 键，内含 Interrupt 对象与审批详情；get_state 显示 state.next = ('tools',)，图暂停在 tools 节点等待](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step2-interrupt-invoke.png)

这里出现了一个和直觉不太一样、但务必理解清楚的设计。`interrupt` 内部虽然靠抛异常暂停，但 `invoke()` 调用本身**正常返回**，并不会把异常抛到调用者面前。返回的是一个 dict，里面有两个键：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "立即给订单 A1001 退款 299 元"}]},
    config={"configurable": {"thread_id": "refund-001"}},
)
# result 形如：
# {
#   'messages': [...],
#   '__interrupt__': [Interrupt(value={'action': 'refund_order', 'order_id': 'A1001', 'amount': 299.0}, ...)]
# }
```

`'__interrupt__'` 这个键的存在，就是「图暂停了、有东西等你审批」的信号。换句话说，判断 Agent 是否停在审批点，看返回 dict 里有没有 `__interrupt__` 键即可。

除了返回值，还可以用 `get_state()` 从 checkpointer 里查暂停状态。它会显示 `state.next = ('tools',)`，明确告诉你图当前暂停在 `tools`（工具）节点，正等着续跑。待审批的数据也有两处可查：返回值的 `result['__interrupt__']`，以及 `state.tasks[0].interrupts`，两者内容一致。

需要注意，这里的 `thread_id`（会话线程标识）和案例 4 是同一个概念。人在回路的「暂停—续跑」必须在同一个 `thread_id` 下进行——续跑时要靠它找回暂停点的存档，这也正是为什么 checkpointer 是硬前提。

#### 2、两种实现路线：手写 interrupt 与 HumanInTheLoopMiddleware

在继续往下之前，有必要说明 LangChain 提供了两条等价的人在回路实现路线，本案例主线走的是其中一条，但两条都值得了解，因为它们的续跑格式有一个容易踩的差异。

- **路线 A（手写 interrupt）**：就是上面 `refund_order` 的写法——在工具内部直接调 `interrupt`。控制最精细，审批界面要展示的数据完全由工具自定义。本案例主线采用这条。
- **路线 B（HumanInTheLoopMiddleware，声明式中间件）**：用 `HumanInTheLoopMiddleware`（导入自 `langchain.agents.middleware`，中间件机制见案例 3）声明哪些工具需要审批，审批拦截逻辑由中间件统一处理，工具本体代码里看不到 `interrupt`，更干净。

把两条路线放在一起实跑同一个退款审批，结果如下：

```bash
python ext5_4_middleware_vs_manual.py
```

![终端输出：Route A 手写 interrupt，interrupt.value 为自定义 dict（action/order_id/amount），Command(resume='approve') 退款成功；Route B 用 HumanInTheLoopMiddleware，interrupt.value 含 action_requests/review_configs，Command(resume=dict decisions) 退款成功；末尾两路线对比表](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--extension-4-middleware-vs-manual.png)

两条路线都能跑通同一个审批效果，但**续跑时传给 `Command(resume=...)` 的格式不同**，这是初学者最容易踩的一个坑：

```python
# 路线 A（手写 interrupt）：resume 传普通字符串
Command(resume="approve")

# 路线 B（HumanInTheLoopMiddleware）：resume 必须传 dict，含 decisions 列表
Command(resume={"decisions": [{"type": "approve"}]})
```

实测中，给路线 B 误传了路线 A 的字符串格式 `Command(resume="approve")`，会直接报 `TypeError: string indices must be integers`——根因是中间件内部会按 `interrupt(...)["decisions"]` 这种下标方式取值，要求 resume 必须是 dict。此外，路线 B 的 `interrupt.value` 结构也不同，包含 `action_requests` 和 `review_configs` 两个字段，而非工具自定义的 dict；它还支持 `approve` / `edit` / `reject` / `respond` 四种决策类型，功能更丰富。

两条路线实操中**二选一**即可，不必都实现。本案例主线后续都基于路线 A，因为它更直观地暴露了 `interrupt` 的工作机制，适合用来讲原理。

---

### 四、看清待审批内容：interrupt 暂停态全貌

#### 1、打印审批横幅与详情

图暂停后，真实系统会把待审批信息推送到运营的审批界面。本节用终端打印模拟这个界面，把 `interrupt` 抛出的内容完整展示出来。

```bash
python step3_print_interrupt.py
```

![终端输出：HUMAN APPROVAL REQUIRED 横幅，下方列出待审批详情 action=refund_order、order_id=A1001、amount=299 元，提供 approve/reject 两个选项；底部 state.next=('tools',) 表示暂停中](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step3-interrupt-pause.png)

`[HUMAN APPROVAL REQUIRED]`（需要人工审批）横幅下，清晰列出了待审批的动作类型、订单号、金额，以及 `approve` / `reject` 两个可选操作。这些字段全部来自工具里 `interrupt({...})` 传出的那个自定义 dict——审批界面想展示什么，就在工具里往这个 dict 塞什么。底部 `state.next = ('tools',)` 再次确认图正暂停等待。

`interrupt` 还带一个 ID，用于在「一次暂停里有多个待审批项」（multi-interrupt）的场景中识别具体是哪一项。单审批场景下不必关心它。

#### 2、两种视角提取待审批信息

待审批信息其实可以从两个不同的视角拿到，理解这一点有助于在真实系统里灵活取数。

```bash
python step4_tool_call_details.py
```

![终端输出：视角一从 interrupt.value 取 action/order_id/amount；视角二从 AIMessage.tool_calls 看到模型的完整决策链 query_order → refund_order；两视角信息互补](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step4-tool-call-details.png)

- **视角一：`interrupt.value`**——也就是工具自定义的那个 dict，直接拿到 `action` / `order_id` / `amount`。这是审批最常用的数据源。
- **视角二：`AIMessage.tool_calls`**——从模型产出的消息里，能看到模型这一轮**完整的工具调用决策链**。截图里可以看到 DeepSeek 实际是先 `query_order`（查订单）确认了一遍，再 `refund_order`（退款）。这条多工具链在 `interrupt` 暂停之前已经完整记录在消息历史里。

两个视角互补：`interrupt.value` 是工具主动抛给审批方的精炼信息，不依赖工具调用的结构；`tool_calls` 则保留了模型决策的完整上下文。审批系统可以两者结合，既看精炼结论，也能追溯模型为什么要这么做。

---

### 五、批准路径：Command(resume='approve') 续跑执行退款

#### 1、批准续跑，退款执行

人工审批通过后，用 `Command(resume='approve')` 把「批准」这个结果回传给暂停的图，让它从断点续跑。

```python
from langgraph.types import Command

# 同一个 thread_id，传 Command(resume=...) 续跑
result = agent.invoke(
    Command(resume="approve"),
    config={"configurable": {"thread_id": "refund-001"}},
)
```

```bash
python step5_resume_approve.py
```

![终端输出：Command(resume='approve') 续跑，refund_order 执行计数显示为 2 次，最终 ToolMessage 显示退款成功 ¥299，state.next=() 表示图已跑完，approve_path: done](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step5-resume-approve.png)

续跑后，工具内 `interrupt()` 的返回值变成了传入的 `'approve'`，工具据此走批准分支，输出退款成功的 `ToolMessage`（工具消息），`state.next = ()` 表示图已正常跑完。批准路径闭环完成。

注意续跑时 `resume` 传的字符串（这里是 `'approve'`），就是工具里 `approval = interrupt(...)` 那个 `approval` 变量拿到的值。这条「人工决定 → resume 值 → interrupt 返回值 → 工具分支」的传递链，是人在回路信息回传的全部秘密。

#### 2、最反直觉的行为：resume 时节点从头重执行

上面的截图里藏着一个让多数人意外的细节：`refund_order` 的执行计数是 **2**，不是 1。这不是 bug，而是 LangGraph 续跑机制的核心行为——**resume 时，暂停所在的节点会从头重新执行一遍**。

为了把这个行为看得一清二楚，下面这个实验在 `interrupt()` 调用的前后各插一行 print，用一份全局执行日志追踪到底跑了几次：

```python
@tool
def refund_order(order_id: str, amount: float) -> str:
    log.append("START")            # interrupt 之前
    print("BEFORE interrupt")
    approval = interrupt({...})     # 时间切割点
    print("AFTER interrupt")       # interrupt 之后
    log.append("AFTER_INTERRUPT")
    ...
```

```bash
python ext5_1_resume_replay.py
```

![终端输出：第一次 invoke 时 BEFORE interrupt 打印 1 次，执行日志只有 [1] START；第二次 invoke(Command(resume)) 时 BEFORE interrupt 又打印 1 次，日志新增 [2] START，最终 [3] AFTER_INTERRUPT；START 共出现 2 次](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--extension-1-resume-replay.png)

实跑结果把机制摊开了：

- 第一次 `invoke()`：`BEFORE interrupt` 打印 1 次，执行日志只有 `[1] START`——节点跑到 `interrupt()` 就停住了，`AFTER interrupt` 没机会打印。
- 第二次 `invoke(Command(resume='approve'))`：`BEFORE interrupt` **又打印了一次**，日志新增 `[2] START`，然后才 `[3] AFTER_INTERRUPT`。

最终 `START` 出现了 2 次，`AFTER_INTERRUPT` 只出现 1 次。这说明：**`interrupt` 之前的代码，在续跑时会被重新执行一遍**；而 `interrupt` 之后的代码只有续跑那一次才跑得到。

可以把 `interrupt()` 理解成一个「时间切割点」：第一次执行到它，节点暂停并把状态存档；续跑时，节点从第一行重新跑起，但这一次 `interrupt()` 不再真正暂停，而是直接返回 `Command(resume=...)` 传入的值。

这个行为带来一条铁的工程纪律：**`interrupt` 之前绝不能有不可重复的副作用**。如果你在 `interrupt()` 之前就写了数据库、扣了款、发了邮件，那么续跑时这些副作用会再发生一遍。这正是第七章四铁律中「副作用幂等」存在的根本原因。

---

### 六、拒绝路径：Command(resume='reject') 退款被驳回

#### 1、拒绝续跑

人在回路的价值，一半在批准，另一半在能够**拒绝**。把审批结果换成 `'reject'`，其余完全不变：

```python
result = agent.invoke(
    Command(resume="reject"),
    config={"configurable": {"thread_id": "refund-002"}},
)
```

```bash
python step6_resume_reject.py
```

![终端输出：Command(resume='reject') 续跑，refund_order 走拒绝分支，ToolMessage 显示 ❌ 退款被驳回，reject_path: done；底部附两路径对比表](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step6-resume-reject.png)

工具内 `interrupt()` 返回 `'reject'`，走拒绝分支，输出退款被驳回的 `ToolMessage`。退款没有执行，闸门关上了。值得一提的是，拒绝路径同样有「从头重执行」——执行计数也是 2，与批准路径完全对称。换句话说，从头重执行是续跑机制本身的行为，与批准还是拒绝无关。

#### 2、两路径对比：唯一的变量是 resume 的值

把批准和拒绝两条路径并排跑一遍，能看清一件事：两条路径之间，到底什么变了、什么没变。

```bash
python ext5_2_approve_vs_reject.py
```

![终端输出：批准路径 Command(resume='approve') → ✅ 退款已执行 A1001 ¥299 成功；拒绝路径 Command(resume='reject') → ❌ 退款已拒绝 A1001 ¥299 被驳回；两路径图结构、工具、checkpointer 完全相同](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--extension-2-approve-vs-reject.png)

对比结果非常干净：

| 维度 | 批准路径 | 拒绝路径 |
|------|---------|---------|
| 图结构 | 完全相同 | 完全相同 |
| 工具定义 | 完全相同 | 完全相同 |
| checkpointer | 完全相同 | 完全相同 |
| **唯一区别** | `Command(resume='approve')` | `Command(resume='reject')` |
| 结果 | 退款执行 | 退款驳回 |

**`Command(resume=...)` 的值，是路径分叉的唯一控制点。** 这个值通过 `interrupt()` 的返回值传进工具，工具内的 `if` 判断决定走哪条分支。也正因为如此，resume 的值不必局限于 `'approve'` / `'reject'` 两个字符串——它可以是任意值，包括携带审批意见的 JSON 对象、条件参数等等，全看工具内怎么消费它。

---

### 七、四铁律：写人在回路工具不能踩的坑

人在回路的机制本身不复杂，但有几条纪律一旦违反，审批会在你毫不知情的情况下失效。LangGraph 官方文档把它们归纳为四条铁律：

1. **`interrupt` 绝不包进 `try/except`**——`interrupt` 靠抛异常暂停，宽泛的 `except` 会把这个异常吞掉，审批被直接绕过。
2. **不条件跳过 `interrupt`**——不要在 `interrupt` 之外用 `if` 决定「这次要不要审批」（比如「金额小就跳过」）。如果需要条件审批，条件判断要放在 `interrupt` **调用之后**对返回值做，或在工具内部组织，而不是用外层 `if` 把 `interrupt()` 整个跳过。
3. **副作用幂等**——承接第五章的发现，`interrupt` 之前的代码续跑时会重跑一遍，所以任何副作用都必须可以安全地重复执行（幂等）。
4. **不序列化复杂对象**——`interrupt` 抛出的数据会被存进 checkpointer，应传可序列化的简单结构（dict、字符串、数字），不要传数据库连接、文件句柄这类复杂对象。

其中第一条最隐蔽，也最值得用反例演示。

#### 1、铁律反例：interrupt 被 try/except 吞掉，审批彻底失效

下面这个实验故意写一个「错误版」工具，把 `interrupt` 包进宽泛的 `try/except Exception`，再和正确版对比：

```python
# ❌ 错误版（违反铁律 #1）
@tool
def refund_order_BAD(order_id: str, amount: float) -> str:
    try:
        approval = interrupt({"order_id": order_id, "amount": amount})
    except Exception:
        approval = "approve"   # 异常被吞，等于默认批准——危险
    ...

# ✅ 正确版
@tool
def refund_order_GOOD(order_id: str, amount: float) -> str:
    approval = interrupt({"order_id": order_id, "amount": amount})  # 直接调，不包 try
    ...
```

```bash
python ext5_3_iron_rule_violation.py
```

![终端输出：BAD 版 interrupt 被 except 吞掉，异常类型显示为 GraphInterrupt，__interrupt__ 出现 = False，图没有暂停、审批被绕过；GOOD 版 __interrupt__ 出现 = True，正常暂停等待审批](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--extension-3-iron-rule-violation.png)

实跑结果触目惊心：

- **错误版**：`interrupt` 被 `except` 吞掉了，截图里能看到被捕获的异常类型是 `GraphInterrupt`；`__interrupt__` 出现 = `False`，图根本没暂停，直接默认批准把退款执行了——审批形同虚设。
- **正确版**：`__interrupt__` 出现 = `True`，图正常暂停等待人工。

这里暴露了 `interrupt` 的底层真相：它靠抛出一个名为 `GraphInterrupt` 的异常来传递暂停信号（实测确认是 `GraphInterrupt`）。一旦工具代码里有 `try/except Exception` 这种宽泛捕获，就会顺带把 `GraphInterrupt` 吞掉，图误以为工具正常完成，于是 `__interrupt__` 不出现，审批被完全绕过。

正确做法：`interrupt` 调用前后不加任何异常处理；万一工具里确实需要 `try/except`，必须用精确的异常类型（如 `except ValueError`），绝不用裸的 `except Exception`。反例之所以有价值，正在于它把「审批被绕过」这个后果直接演给你看——比单纯讲「不要这样写」要有说服力得多。

---

### 八、换数据即换业务：transfer_funds 转账场景复用

人在回路这套机制最实用的特点是：它与具体业务动作无关。退款能审批，转账、删数据、发邮件同样能审批。本节把危险工具从「退款」换成「转账」，验证整套机制原样可复用。

```bash
python step7_reuse_transfer.py
```

![终端输出：transfer_funds 转账场景，interrupt 机制完全可复用；¥5000 转账批准成功，¥20000 高额转账被驳回；interrupt.value 携带 risk_level 等业务字段；附 4 步复用方法论](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-5--shot--step7-transfer-reuse.png)

实跑里跑了两个转账场景：5000 元的转账审批通过、执行成功；20000 元的高额转账被驳回。整个过程中，`interrupt` / `Command` / `checkpointer` 这三件套**一行没改**，改的只有业务工具本身——把 `refund_order` 换成了 `transfer_funds`。`interrupt.value` 里还顺手携带了 `risk_level`（风险等级）这样的业务字段，证明审批信息可以按业务需要自由扩展。

把复用的步骤抽象出来，就是一套四步方法论：

1. **定义你的危险业务工具**（如 `transfer_funds`、`delete_records`、`send_email`）。
2. **在工具执行真正动作之前，加一次 `interrupt(审批信息 dict)`**，dict 里塞审批界面需要的字段。
3. **外部用 `Command(resume=审批结果)` 续跑**，把人工决定传回工具。
4. **checkpointer 保持不变**——`InMemorySaver` 在开发阶段直接复用即可。

这套方法论与第七章四铁律配合使用，就构成了一个可以套到任意危险动作上的审批模板。

---

### 九、自学迁移指南：把退款审批换成你的危险动作

本案例用退款做样板，但人在回路的真正用途是给**你自己系统里的危险动作**加审批闸门。下面给出把示例迁移到自有业务的完整路径。

#### 1、可替换的部分（换成你的业务）

```python
# 改之前（本案例的退款审批工具）
@tool
def refund_order(order_id: str, amount: float) -> str:
    """给指定订单退款。"""
    approval = interrupt({
        "action": "refund_order",
        "order_id": order_id,
        "amount": amount,
    })
    if approval == "approve":
        return f"✅ 退款已执行：{order_id} ¥{amount}"
    return f"❌ 退款已拒绝：{order_id}"

# 改之后（换成你的业务：以「删除生产数据库表」为例）
@tool
def drop_table(table_name: str) -> str:
    """删除指定数据库表（高危操作）。"""
    approval = interrupt({
        "action": "drop_table",
        "table_name": table_name,
        "risk_level": "critical",     # 审批信息可携带任意业务字段
    })
    if approval == "approve":
        # 真正的删表逻辑放在 interrupt 之后（保证不会因从头重执行而误删）
        return f"✅ 已删除表：{table_name}"
    return f"❌ 删除被驳回：{table_name}"
```

可替换的有三处：**危险工具的名字与参数**、**`interrupt` 抛出的审批信息字段**、**批准 / 拒绝分支里的业务逻辑**。审批信息字段尤其自由——审批界面想展示什么，就往那个 dict 里塞什么。

#### 2、保持不变的部分（结构骨架）

以下骨架原样保留，不要改动：

- `from langgraph.types import interrupt, Command`——导入路径固定。
- 工具内「先 `interrupt(...)` 再执行真正动作」的顺序——危险逻辑必须在 `interrupt` 之后。
- `create_agent(..., checkpointer=InMemorySaver())`——人在回路的硬前提，与案例 4 一致。
- 续跑用 `agent.invoke(Command(resume=审批结果), config={"configurable": {"thread_id": 同一个}})`——`thread_id` 必须与暂停时一致。
- 判断是否暂停看返回 dict 里有没有 `__interrupt__` 键。

#### 3、迁移后如何验证跑通（含验收任务）

迁移完成后，按下面三步自查是否真正闭环：

1. **触发暂停**：`invoke` 一个会调用危险工具的请求，检查返回 dict 里**有** `__interrupt__` 键，且 `get_state().next` 不为空——说明图确实停在了审批点。
2. **批准路径**：`Command(resume='approve')` 续跑，确认危险动作执行、`state.next == ()`。
3. **拒绝路径**：换一个 `thread_id` 重跑，`Command(resume='reject')` 续跑，确认危险动作**没有**执行。两条路径都跑通才算闭环。

**进阶验收任务（条件审批）**：给你的工具加一条「金额 / 风险超过阈值才触发审批」的逻辑。这里必须严守四铁律第二条——条件判断**不能**用外层 `if` 把 `interrupt()` 整个跳过，否则低风险动作根本不存档、机制就破了。正确写法是让 `interrupt` 始终被调用，在它返回后或在审批信息里体现条件，例如：

```python
@tool
def transfer_funds(to_account: str, amount: float) -> str:
    """转账。金额超过 10000 标记为高风险，需重点审批。"""
    # 条件不是用来跳过 interrupt 的，而是作为审批信息的一部分抛出
    approval = interrupt({
        "action": "transfer_funds",
        "to_account": to_account,
        "amount": amount,
        "needs_review": amount > 10000,   # 阈值判断放进审批信息，不在外层跳过 interrupt
    })
    if approval == "approve":
        return f"✅ 转账已执行：{to_account} ¥{amount}"
    return f"❌ 转账被驳回：{to_account}"
```

能跑通「高额触发重点审批、批准 / 拒绝两条路径都正确」，即达成本案例验收标准。

#### 4、迁移前置知识假设清单

迁移本案例前，确认以下前置条件：

- **已掌握 `create_agent` 与工具定义**（案例 1）——本案例的危险工具就是一个普通 `@tool`，只是内部多了一次 `interrupt`。
- **已掌握 checkpointer 与 `thread_id`**（案例 4）——人在回路的暂停与续跑完全依赖这套持久化机制，没有 checkpointer，`interrupt` 无法暂停。
- **能接受「节点从头重执行」这个反直觉行为**——这一条本案例第五章已专门用执行日志演示，迁移时务必把所有不可重复的副作用放到 `interrupt` 之后。
- **理解「为什么 Agent 需要人工介入」**——核心是：模型对不可逆动作（退款 / 转账 / 删数据 / 发邮件）的判断不能完全自主，必须有人在回路里把最后一道关。

掌握这四点，就可以把本案例的退款审批模板，安全地套用到自己系统里任何一个危险动作上。


---

## LangChain Agent 可观测性（Observability）：给 Agent 接上 Langfuse、在 dashboard 看清每一步调用 从零到一跑通实操手册

### 一、开篇：Agent 为什么比传统 Web 更难调试

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)。前面的案例已经把 Agent（智能体，指能自主决定调用哪个工具、传什么参数的执行体）搭了起来：案例 1 跑通了第一个能调工具的 Agent，案例 4 给它加上了持久化记忆，案例 5 让它在危险动作前暂停等人审批。这些 Agent 有一个共同特点——**一次用户请求，背后是好几步看不见的调用**。

设想案例 5 那个订单客服 Agent。用户问「我的订单 A1001 发货了吗，帮我查下物流」，从用户视角看，它只是隔了几秒回了一段话。但在框架内部，真实发生的是：模型先读问题、决定调 `query_order` 查订单，拿到结果后再决定调 `check_logistics` 查物流，最后把两步结果汇总成一句人话。这中间有三次模型调用、两次工具调用，每一次都有自己的输入、输出、耗时和 token 消耗。

传统 Web 系统出问题，翻一条请求日志、看一行堆栈，基本就能定位。但 Agent 不一样：一次请求里藏着 3 到 5 次模型决策，失败可能发生在任何一步——是模型选错了工具？还是工具收到的参数不对？还是工具自己抛了错？用户只看到「查不了」三个字，开发者面对的却是一条不透明的调用链。**这正是 Agent 可观测性（Observability，指把系统内部运行状态变得可见、可追溯的能力）要解决的问题**：把这条藏在框架内部的调用链完整记录下来，画成一棵能展开的树，让每一步的输入、输出、token、耗时都摆在眼前。

记录这棵调用链的标准做法叫**追踪（Tracing）**，记录下来的一条完整调用链叫一条 **trace**，trace 里的每一个节点（一次模型调用、一次工具调用）叫一个 **observation**（观测项）或 **span**。本案例用来承载这套能力的工具是 Langfuse——一个开源的 LLM 工程与可观测平台，官网为 [langfuse.com](https://langfuse.com/)，源码仓库在 [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)。

![Langfuse 官网首页：开源 LLM 工程平台，主打 Tracing 追踪与可观测能力](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-homepage.png)

选 Langfuse 作为主路径，核心原因是它支持**自托管（self-host，指把整套服务部署在自己的机器上）**：所有 trace 数据存在本地 Docker 里，物理上不离开本机。对国内的金融、医疗、政务等数据不能出境的场景，这一点是硬约束。本案例也会在末尾对比另一条路径 LangSmith（LangChain 官方的 SaaS 可观测服务），但主线全程用 Langfuse self-host 跑通。

本案例覆盖以下几个核心对象与步骤：安装 Langfuse SDK 并核验接入入口、用 Docker Compose 起一套完整的 self-host 栈、把已有 Agent 接上 Langfuse 并上报第一条 trace、在 dashboard 读懂 trace 树的结构与原理、用 trace 定位一次工具失败、最后把同一套接入方式换到一个全新 Agent 上验证可复用性。全程基于真实执行，每一步都有终端输出或 dashboard 截图佐证。

本案例所用的观测对象，沿用案例 4、案例 5 同一类型的多步订单客服 Agent（带工具调用、用内存检查点存储），不再重复讲 Agent 本身怎么搭——可观测的接入与 Agent 的业务逻辑是两件解耦的事，这也正是后面要验证的关键结论之一。

---

### 二、准备工作：选定观测对象、安装 Langfuse SDK

#### 1、选一个「值得被观测」的 Agent 作为对象

可观测的价值只有在多步调用上才看得出来——如果 Agent 只调一次模型、不调工具，那它和普通的一问一答没区别，trace 树退化成一根光杆，看不出门道。所以观测对象至少要满足「≥3 步调用、其中至少 1 次工具调用」。

本案例沿用前序案例同类的订单客服 Agent，按相同方式搭一个带三个工具的版本：`query_order`（查订单）、`check_logistics`（查物流）、`calculate_shipping`（算运费），用案例 4 介绍过的 `InMemorySaver`（内存检查点存储器）作为 checkpointer。Agent 的搭法与案例 1、案例 4 一致，这里不再展开，本案例只关注怎么给它接上可观测。

#### 2、安装 langfuse 并核验接入入口

Langfuse 的 Python 接入靠官方 SDK，一行装包即可：

```bash
cd hello-langchain && source .venv/bin/activate
pip install langfuse
```

装完后有一个细节务必先核对清楚：**接入入口类 `CallbackHandler`（回调处理器）的 import 路径**。Langfuse 的 SDK 经历过版本演进，老资料里常见的 `from langfuse.callback import CallbackHandler` 在新版已不适用。本案例实测装到的是 langfuse 4.7.1，正确的 import 路径是：

```python
from langfuse.langchain import CallbackHandler
```

`CallbackHandler` 是 Langfuse 接入 LangChain / LangGraph 的桥梁——它本质是一个回调处理器，挂到 Agent 的执行配置上之后，会自动把每一步调用上报成 trace。这个类是整条接入链路的入口，后面所有步骤都围绕它展开。

新建 `step1_obs_target.py`，把「SDK 版本、import 路径、观测对象 Agent 的工具清单与 checkpointer」一次性核验：

```bash
python step1_obs_target.py
```

![终端：langfuse 4.7.1 安装完成，from langfuse.langchain import CallbackHandler 返回 OK，观测对象 Agent 已就绪（类型 CompiledStateGraph，3 工具 query_order / check_logistics / calculate_shipping，checkpointer 为 InMemorySaver），PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step1-langfuse-install.png)

终端输出确认了几件事：langfuse 版本 4.7.1，`CallbackHandler` 的 import 路径可用，观测对象是一个编译后的状态图（`CompiledStateGraph`），带 3 个工具——满足「≥3 步调用」的观测前提。到这里，SDK 一侧准备就绪，接下来要把承接 trace 数据的 Langfuse 服务端先立起来。

> 版本提示：`pip install langfuse` 无需任何额外 extra 参数。若读者装到的版本与本案例不同，只要是 v4 系列，`from langfuse.langchain import CallbackHandler` 这一路径都成立。

---

### 三、用 Docker Compose 起一套 Langfuse self-host

Langfuse self-host 不是单个容器，而是一整套服务：Web 前端、后台 worker、PostgreSQL（关系库）、ClickHouse（列式分析库，存 trace）、MinIO（S3 兼容对象存储，存大字段）、Redis（缓存队列）。官方把这套编排好放在一个 `docker-compose.yml` 里，整体启动。

#### 1、下载官方编排文件并启动

```bash
mkdir -p langfuse && cd langfuse
curl -sL "https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml" -o docker-compose.yml
docker compose up -d
```

启动前，有几处配置必须按本机情况调整，否则容器起不来或起来了连不上。下面逐个说明，这些都是本案例实测踩过的坑。

##### 1.1 端口冲突：PostgreSQL 宿主端口改 5433

官方 compose 默认把 PostgreSQL 的 5432 端口映射到宿主机。若本机已有别的 postgres 占用 5432（本案例实验机上有一个 `gbrain-pg` 容器占着），端口绑定会失败。改法是只动宿主侧端口，容器内仍保持 5432：

```yaml
# docker-compose.yml 中 postgres 服务的 ports
ports:
  - "127.0.0.1:5433:5432"   # 宿主改 5433，容器内仍 5432
```

这里要理解一点：Langfuse 的 web 和 worker 容器连 PostgreSQL 走的是 Docker 内部网络地址 `postgres:5432`，宿主机映射的端口只用于在容器外直连调试。所以宿主端口改成 5433，完全不影响 Langfuse 内部通信。

##### 1.2 初始化变量：LANGFUSE_INIT 是一条链，缺一不可

手动用 Web UI 注册账号、建组织、建项目、生成 API Key，对教学场景太繁琐。Langfuse 提供了一组 `LANGFUSE_INIT_*` 环境变量，能在首次启动时自动把这些都预置好——学员跑完 `docker compose up` 直接就有可用的项目和 API Key。

关键在于这组变量是**链式依赖**：少设一个，整条初始化就会被跳过（日志里只留一条 warn）。必须按顺序全部设齐，写在同目录的 `.env` 文件里：

```bash
# .env
LANGFUSE_INIT_ORG_ID=...            # 组织 ID（UUID，必须先设）
LANGFUSE_INIT_ORG_NAME=langchain-course
LANGFUSE_INIT_PROJECT_ID=...        # 项目 ID（UUID，必须设才能创建 API Key）
LANGFUSE_INIT_PROJECT_NAME=langchain-demo
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-course-demo-public   # 自定义公钥
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-course-demo-secret   # 自定义私钥
LANGFUSE_INIT_USER_EMAIL=admin@langfuse.local
LANGFUSE_INIT_USER_NAME=admin
LANGFUSE_INIT_USER_PASSWORD=...     # 登录密码
```

预置 API Key 的好处是后续接入代码可以直接写死这对公私钥，不用再去 Web UI 里手动复制。

##### 1.3 密码一致性：S3 与 PostgreSQL 两处

还有两处密码必须前后一致，否则容器之间认证失败：

- **MinIO（S3）密码**：Langfuse 用 MinIO 存大字段（如完整的输入输出）。配置里的 `LANGFUSE_S3_*_SECRET_ACCESS_KEY` 必须与 `MINIO_ROOT_PASSWORD` 完全相同。本案例第一次 trace 数据到了后端却无法持久化，根因就是这两个密码没对上。
- **PostgreSQL 密码**：如果自定义了 `POSTGRES_PASSWORD`，那么 `DATABASE_URL` 里的密码段也要同步改。最省事的做法是教学环境直接保留默认密码不覆盖；生产环境则必须两处一起改。

#### 2、启动后验证：登录、看到预置项目、拿到 API Key

`docker compose up -d` 之后，6 个容器全部健康（web 在 3000、worker 在 3030、postgres 在 5433、外加 clickhouse / minio / redis），本案例起的是 Langfuse v3.175.0 OSS 版本。浏览器打开 `http://localhost:3000`，看到的是登录页：

![浏览器访问 http://localhost:3000：docker compose up 启动后 Langfuse 进入登录页（Sign in to your account）](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-dashboard.png)

![Langfuse 登录页全貌：用 .env 中预置的邮箱与密码登录](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-login-page.png)

> ⚠️ 注意：如果本机设置了系统 HTTP 代理（`http_proxy`），浏览器或 curl 访问 `localhost:3000` 可能走代理返回 502。验证连通性时用 `curl --noproxy '*' http://localhost:3000` 绕过代理。这个代理问题在下一章的 Python 接入里还会再遇到一次，要一并处理。

用 `.env` 里预置的邮箱密码登录后，进入组织页——`LANGFUSE_INIT` 变量预置的组织 `langchain-course` 与项目 `langchain-demo` 已经在那里，无需任何手动创建：

![登录成功后进入组织页：langchain-course 组织下已预置 langchain-demo 项目，点 Go to project 进入](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-dashboard-logged.png)

![组织页视图：INIT 变量预置的 langchain-course 组织与 langchain-demo 项目在首次启动即存在，省去手动建项目的步骤](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-after-login.png)

进入项目后，在 Settings → General 能看到这个项目对外的 Host Name（接入时 Python 客户端要连的地址就是它）以及项目的 org/project UUID：

![项目设置页 General：Host Name 显示 http://localhost:3000，langchain-demo 项目的 org/project UUID 在 Debug Information 区块可见](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-project-settings.png)

再到 Settings → API Keys，能看到预置的那对公私钥，页面还贴心地给出了 `.env` 接入片段：

![项目设置页 API Keys：预置的 pk-lf-course-demo-public 公钥与 sk-lf-...cret 私钥，页面给出 LANGFUSE_SECRET_KEY / PUBLIC_KEY / BASE_URL 三件套的 .env 片段](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step2-langfuse-apikeys.png)

这对 API Key（公钥 `pk-lf-course-demo-public` + 私钥 `sk-lf-course-demo-secret`）是 Python 一侧连接 Langfuse 的凭证，下一章马上要用到。服务端到此完全就绪。

---

### 四、把 Agent 接上 Langfuse：上报第一条 trace

服务端起好了，这一章是全案例的核心——让已有的 Agent 在每次运行时，自动把调用链上报到 Langfuse。整个接入只新增三样东西：三个环境变量、一个 `CallbackHandler` 实例、一处 `config` 参数。

#### 1、配置凭证与连接验证

接入第一步是把 Python 客户端连上 Langfuse。需要三个环境变量：

```python
import os
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-course-demo-public"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-course-demo-secret"
os.environ["LANGFUSE_HOST"]       = "http://localhost:3000"
```

`LANGFUSE_HOST` 是 v4 SDK 指定服务端地址的变量，self-host 场景必须显式设成本地的 `http://localhost:3000`（不设的话 SDK 会默认连 Langfuse 云端）。

这里有一处必须前置处理的坑，和上一章浏览器 502 同源：**系统代理也会拦截 Python 的请求**。Langfuse 客户端底层用 httpx/requests 发请求，若本机设了 `http_proxy`，连接 `localhost` 会被代理拦下、`auth_check()` 超时。解法是在 Langfuse 客户端初始化**之前**设好 `NO_PROXY`：

```python
os.environ["NO_PROXY"] = "localhost,127.0.0.1"   # 必须在 Langfuse 客户端初始化前设
```

一句话记住这个坑：**凡是用 Langfuse self-host + 本地访问的场景，curl、Playwright、Python 三处都要各自绕过代理**——curl 用 `--noproxy '*'`，Python 用 `NO_PROXY` 环境变量。

配好之后实例化 `CallbackHandler` 并跑一次 `auth_check()` 验证连接：

```bash
python step3_obs_config.py
```

![终端：step3 设置 LANGFUSE_PUBLIC_KEY / SECRET_KEY / HOST 与 NO_PROXY 后，CallbackHandler 实例化并 auth_check() 连接成功，PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step3-langfuse-connect.png)

`auth_check()` 返回成功，说明 Python 一侧已经能正常连上 self-host 的 Langfuse。

#### 2、接入只改两行：CallbackHandler + callbacks

真正的接入代码非常少。把 `CallbackHandler` 实例通过 `config` 参数的 `callbacks` 字段挂到 Agent 的 `invoke` 调用上即可：

```python
from langfuse.langchain import CallbackHandler

handler = CallbackHandler()                       # ① 建一个回调处理器
agent.invoke(
    {"messages": [{"role": "user", "content": "我的订单 A1001 发货了吗？麻烦帮我查一下物流情况"}]},
    config={"callbacks": [handler]},              # ② 挂到 callbacks 上
)
```

`config={"callbacks": [handler]}` 这一行是接入的全部业务侵入——Agent 的工具、模型、图结构一概不动，只是在调用时多挂了一个回调。`callbacks` 是 LangChain 的标准回调机制，Langfuse 的 `CallbackHandler` 正是实现了这套回调接口，所以能无侵入地嵌进任何 LangChain / LangGraph 的执行流。

还有一个 v4 SDK 特有的关键环境变量必须设，否则 trace 上报会静默失败：

```python
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:3000/api/public/otel"
```

Langfuse v4 SDK 底层走 **OpenTelemetry（简称 OTel，业界通用的可观测数据标准协议）** 上报数据，`OTEL_EXPORTER_OTLP_ENDPOINT` 指定 span 数据的导出地址。不设这个变量，调用链虽然在本地产生了，但导不到 Langfuse 后端——这是 v4 接入最容易漏的一步。

跑起来：

```bash
python step4_obs_invoke.py
```

这次查询「我的订单 A1001 发货了吗」会触发模型先后调用 `query_order` 和 `check_logistics` 两个工具，加上模型自身的多次决策，一共 5 条消息。运行完，打开 Langfuse 的 Tracing 列表，第一条 trace 已经躺在那里：

![Langfuse Tracing 列表：第一条 LangGraph trace 出现，输入「我的订单 A1001 发货了吗」，Observation Levels 列显示 9，Latency 3.77s，Tokens 976→184](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step4-traces-list.png)

列表里这一行信息密度很高：trace 名 `LangGraph`、输入内容、**Observation（观测项）数量 9**、延迟 3.77 秒、token 976 进 184 出。一次看似简单的「查物流」，框架内部实际跑了 9 个嵌套节点——这就是可观测要揭开的东西。点进去就能看到完整的 trace 树。

---

### 五、读懂 trace 树：可观测的原理就在这棵树上

trace 列表只是入口，真正承载「原理」的是点进单条 trace 后那棵可展开的调用树。这一章把它拆开看清楚。

#### 1、trace 树的整体结构

点开刚才那条物流查询 trace：

![Langfuse trace 详情页：左侧 trace 树 LangGraph(root) → model(ChatDeepSeek) → tools → check_logistics，9 层嵌套；右侧展开某节点的输入输出与 token、延迟](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step5-trace-tree.png)

左侧这棵树就是这次 Agent 运行的完整调用链。最外层是 `LangGraph`（根节点，代表整个图的一次执行），往里依次是模型决策节点、工具调度节点、具体的工具调用节点。点中树上任意一个节点，右侧会展开它的输入、输出、token 消耗和延迟。把窗口拉宽，右侧的 observation 详情看得更全：

![同一棵 trace 树在更宽窗口下展开右侧 observation 详情，可逐节点查看 Input / Output / Metadata](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step5-trace-tree-1440.png)

值得注意的是 `check_logistics` 这个工具节点：它完整保存了 Agent 实际传给工具的参数（订单号）和工具返回的结果。这意味着——**不用在工具里加任何 print 或日志，就能看到 Agent 到底传了什么给工具**。这是 trace 最直接的排障价值。

#### 2、三类节点：CHAIN / GENERATION / TOOL

trace 树上的节点不是同一种东西。把一棵更丰富的 trace（一次三工具、三次模型调用的退款咨询）用 Langfuse 的 REST API 拉出来逐个打印，节点类型一目了然：

![终端：拓展实验 1 trace 树解剖——13 个嵌套 span，标注 CHAIN（框架内部节点）/ GENERATION（LLM 调用，含 token 与延迟）/ TOOL（工具调用，含输入参数）三类节点](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--extension-1-trace-anatomy.png)

这棵 trace 共 13 个嵌套 span，归为三类：

| 节点类型 | 含义 | 携带的关键信息 |
| --- | --- | --- |
| **CHAIN** | 框架内部调度节点（LangGraph / model / tools 等） | 只有延迟，无 token |
| **GENERATION** | 一次 LLM 模型调用 | 模型名、input/output token、延迟 |
| **TOOL** | 一次工具调用 | 工具名、输入参数、输出结果 |

把这三类节点和上一节那棵树对上，可观测的原理就清楚了：**Tracing 自动捕获了「模型 → 工具 → 模型」的完整嵌套调用，每一层都带着自己的耗时与消耗。**开发者无需手写任何埋点，这条调用链是框架在执行时通过回调机制自动产生的。

#### 3、从 trace 读出一个工程结论：Agent 为什么贵

这棵被拆开的 trace 还顺手回答了一个常见疑问——Agent 为什么比单次问答烧 token。看三次 GENERATION 节点的 input token：427、527、756，逐步递增。原因是**每一步模型决策的输入，都包含了之前所有工具调用的结果**（上下文在累积）。三次 LLM 调用累计 1710 个 input token、382 个 output token，而用户只问了一句话。这个数字关系，只有在 trace 树里逐节点看 token 才能直观感受到。

下面这张是同一次多步调用的完整 trace 树截图，三类节点在树中的相对位置看得更整体：

![同一次多步调用的完整 trace 树结构（截图全貌），便于对照 CHAIN / GENERATION / TOOL 三类节点在树中的层级位置](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step5-trace-tree-full.png)

---

### 六、可观测的反面价值：用 trace 定位一次工具失败

前面看的都是成功的 trace。但可观测真正不可替代的价值，恰恰在**失败的时候**——这也是 Agent 从「demo 玩具」走向「生产可用」的分水岭。

本节做一个反例演示：故意让一个查库存工具 `query_stock` 在收到 `X` 开头的非法商品码时抛错，然后看 trace 怎么帮你定位。先跑一组对照——正常商品码 `P001` 查询成功，非法商品码 `X999` 触发异常：

```bash
python ext6_3_find_failure.py
```

跑完打开 Tracing 列表，成功和失败的 trace 并排躺着：

![Langfuse Tracing 列表累积 4 条 trace：含一条 X999 故意触发的失败链路与多条正常链路，列表层即可区分成功与失败](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--extension-3-traces-list.png)

点开那条 X999 的失败 trace，展开 `tools` 节点下的 `query_stock`，错误信息直接摆在节点里：

![X999 失败 trace 详情：展开 tools 节点下的 query_stock，可直接看到输入参数与抛出的「无效商品码格式」错误信息](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--extension-3-failure-trace.png)

把「有 trace」和「没 trace」两种排障场景对比一下，价值差距就出来了：

| 场景 | 排障过程 | 耗时 |
| --- | --- | --- |
| **没有 trace** | 用户只反馈「X 开头的商品查不了」，你只能从代码开始猜：翻日志、加 print、复现用户步骤 | 可能 20 分钟 |
| **有 trace** | 直接打开 X999 trace → 展开 `query_stock` 节点 → 看到输入参数和抛出的错误 | 约 2 分钟 |

这正是开篇那个问题的答案：Agent 一次请求含 3 到 5 次调用，失败发生在哪一步，用户看不到、传统日志也拼不全；而 trace 给出的是完整调用链，工具节点里的错误信息无需额外埋点就能看到。**工具是 Agent 最常见的失败点**（参数格式错误、外部服务超时、数据不存在），这些问题在 trace 里都一目了然。

---

### 七、换 Agent 不换接入：验证可复用性

到这里，可观测已经在订单物流 Agent 上跑通了。但教学目标里还有关键一条：这套接入方式能不能**直接套到任意一个新 Agent 上，且代码不用改**。这一节就来验证。

新建一个业务完全不同的 Agent——退款咨询，带三个全新工具：`query_order_v2`（查订单）、`check_refund_policy`（查退款政策）、`check_return_deadline`（查退货期限）。接入可观测的代码，与第四章相比**一行都不用改**：

```python
from langfuse.langchain import CallbackHandler

handler = CallbackHandler()                       # 与第四章完全相同
agent_v2.invoke(
    {"messages": [{"role": "user", "content": "我想申请退款，订单号 B2003"}]},
    config={"callbacks": [handler]},              # 与第四章完全相同
)
```

跑起来：

```bash
python step7_obs_reuse.py
```

这次退款咨询触发了 3 次工具调用、7 条消息，比物流查询那条链路更深。打开 Tracing 列表，新的退款 trace 和第四章那条物流 trace 并排出现（下面这张列表是在跑完本步、第六章失败演示之前捕获的，所以此刻列表里是这两条）：

![Langfuse Tracing 列表：新增的退款咨询链路（3 工具）与第四章的物流查询链路并排，两次接入用的是同一段代码、一行未改](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step7-traces-list-2.png)

点开退款这条 trace，三个全新工具的调用清晰可见：

![退款咨询 trace 树：query_order_v2 + check_refund_policy + check_return_deadline 三工具、7 条消息，嵌套层级比物流查询更深](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--step7-reuse-trace.png)

结论清楚了：**换 Agent 不换接入方式**。三个工具全部不同、业务逻辑全部不同，但 `CallbackHandler` + `config={"callbacks": [handler]}` 这套接入代码一字未动，trace 照样完整上报。这印证了开篇的判断——可观测的接入与 Agent 的业务逻辑是彻底解耦的两件事。这也意味着，后续案例（比如 RAG agent）要加可观测，同样只需挂一行 `callbacks`，检索链路的 trace 会自动出现、而且更丰富。

---

### 八、路径选型：Langfuse self-host 与 LangSmith SaaS 的取舍

主线全程用的是 Langfuse self-host。但可观测还有另一条主流路径——LangSmith，LangChain 官方的 SaaS（云服务）可观测平台。本节把两条路径摆在一起对比，帮读者按自己的场景选型。

LangSmith 的接入比 Langfuse 还省事，**业务代码零改动**，只需三个环境变量：

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls-...        # 在 smith.langchain.com 获取
export LANGSMITH_PROJECT=my-project
```

设好这三个变量，LangChain 会自动把 trace 上报到 LangSmith，连 `CallbackHandler` 都不用建。但「省事」的另一面是数据归属——每次 Agent 调用的输入输出都会上报到 LangSmith 的美国服务器。

把两条路径的差异列清楚：

![终端：拓展实验 2 对比——Langfuse self-host（本地 Docker、数据不出境、免费无限、需 Docker）vs LangSmith SaaS（仅 3 个环境变量、最省事、数据上报美国、free tier 5000/月）](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-6--shot--extension-2-comparison.png)

| 维度 | Langfuse self-host | LangSmith SaaS |
| --- | --- | --- |
| **接入方式** | 显式 `CallbackHandler()` + `config={"callbacks": [handler]}` | 仅 3 个环境变量，业务代码零改动 |
| **数据归属** | 本地 Docker（PostgreSQL + ClickHouse + MinIO），不离开本机 | 上报到 LangSmith 的美国服务器 |
| **合规性** | 数据不出境，金融 / 医疗 / 政务可用 | 数据出境，受限场景不可用 |
| **成本** | 免费、无调用量上限 | free tier 每月 5000 条 trace |
| **运维** | 需自己起并维护 Docker 栈 | 无需运维，开箱即用 |

选型的核心决定因素**不是技术、而是合规**：

- **金融 / 医疗 / 政务等数据不能出境的场景**：只能用 Langfuse self-host，LangSmith 出局。
- **个人项目 / 学习 / 内部原型**：两者都行，LangSmith 更省事、零代码改动。

本案例主线选 Langfuse self-host，正是因为它覆盖了更严苛的合规场景，是「学会一套就能用到任何地方」的稳妥选择。

> 本案例的 LangSmith 路径仅做环境变量层面的演示对比，未实际上报（无 LangSmith API Key）。读者若在个人场景试用，注册 [smith.langchain.com](https://smith.langchain.com/) 拿到 `ls-` 开头的 API Key 后，设好上面三个变量即可。

---

### 九、把可观测接到你自己的 Agent：自学迁移指南

前面验证过「换 Agent 不换接入」，这一章把它整理成一份可直接照搬的迁移清单，方便读者接到自己的任意 Agent 上。

#### 1、前置假设清单

照搬本案例的接入方式，需要满足以下前提：

1. 你已有一个能跑通的 LangChain / LangGraph Agent（能调 `invoke` 或 `stream`）。
2. Agent 至少有一次工具调用——否则 trace 树退化成单节点，看不出可观测的价值。
3. 本机装了 Docker（self-host 路径需要）；若选 LangSmith 路径则不需要 Docker，但需要能访问境外网络。
4. Python 环境已 `pip install langfuse`（v4 系列）。

#### 2、迁移三件事：要改什么、不要改什么、怎么验证

**① 要改什么（接入侧新增，全部与业务无关）：**

- 设三个连接环境变量：`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_HOST`。
- 设一个上报端点：`OTEL_EXPORTER_OTLP_ENDPOINT=http://你的host:3000/api/public/otel`（v4 必设，漏了 trace 上报会静默失败）。
- 若本机有系统代理，设 `NO_PROXY=localhost,127.0.0.1`。
- 建一个 `handler = CallbackHandler()`，在 `invoke` 时传 `config={"callbacks": [handler]}`。

**② 不要改什么（业务侧零侵入）：**

- Agent 的工具定义、模型选择、图结构、checkpointer——一概不动。
- 这正是「换 Agent 不换接入」的含义：第七章用三个全新工具验证过，接入代码一字未改。

**③ 怎么验证（验收标准）：**

- 跑一次带工具调用的 `invoke`，到 Langfuse Tracing 列表确认出现新 trace。
- 点开 trace，在树里找到某个工具节点，确认能看到它的**输入参数和输出结果**。
- 能在 trace 里定位到「某次工具调用传了什么、返回了什么」，就说明可观测已经真正接通——这也是本案例的核心验收点。

#### 3、本案例踩过的坑速查

把前面分散在各章的坑集中列一遍，迁移时对照排查：

| 现象 | 根因 | 解法 |
| --- | --- | --- |
| 访问 localhost:3000 返回 502 | 系统 `http_proxy` 拦截本地请求 | curl 加 `--noproxy '*'`；Python 设 `NO_PROXY`；Playwright 加 noproxy 参数 |
| `auth_check()` 超时 | Python 请求也被系统代理拦截 | 在 Langfuse 客户端初始化前设好 `NO_PROXY=localhost,127.0.0.1` |
| trace 没上报到后端 | 漏设 `OTEL_EXPORTER_OTLP_ENDPOINT`（v4 必设） | 设为 `http://host:3000/api/public/otel` |
| trace 到了后端但无法持久化 | MinIO（S3）密码与 `MINIO_ROOT_PASSWORD` 不匹配 | 两处密码改成完全一致 |
| postgres 端口绑定失败 | 宿主机 5432 被其他 postgres 占用 | compose 里宿主端口改 `127.0.0.1:5433:5432` |
| `LANGFUSE_INIT` 不生效 | INIT 变量链式依赖，缺一即整体跳过 | 按 ORG_ID → ORG_NAME → PROJECT_ID → ... 顺序设齐 |

本案例从安装 SDK、起 self-host 栈、接入上报、读懂 trace 树原理、用 trace 定位失败，到换 Agent 验证复用、对比两条路径选型，完整跑通了 Agent 可观测的全链路。可观测不是 Agent 的可选装饰，而是它从能跑通走向能上生产的关键基础设施——当 Agent 的调用链藏在框架内部、失败可能发生在任何一步时，一棵能展开的 trace 树就是开发者唯一能依靠的眼睛。


---

## LangChain Agentic RAG（智能体检索增强问答）从零到一跑通实操手册

### 一、开篇：让 Agent 自己决定何时检索知识库

检索增强生成（RAG，Retrieval-Augmented Generation）是给大语言模型外接一个私有知识库的常见做法：用户提问时，先从知识库里检索相关片段，再把片段拼进提示词让模型作答，模型由此能回答训练数据里没有的私有问题。传统 RAG 把这条链写死——「先检索、再作答」是固定流程，对应 LangChain 早期的 `RetrievalQA` 链。

本案例做的是另一种形态：**agentic RAG（智能体检索增强问答）**。它把检索器包装成一个工具交给 Agent，由模型自己推理「这个问题要不要检索、检索什么、检索结果够不够用」。如果检索回来的内容不相关，再用一个评分器（Grader）打分，不合格就改写查询重试。检索这件事从「写死的前置步骤」变成了「模型自主决策的一个工具调用」，这是 agentic RAG 与固定 `RetrievalQA` 链最本质的区别。

LangChain 是面向大语言模型应用开发的开源框架，官网为 [langchain.com](https://www.langchain.com/)，源码仓库在 [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)，官方文档站为 [docs.langchain.com](https://docs.langchain.com/)。本案例对应官方 agentic-rag 教程的链路，文档页为 [docs.langchain.com/oss/python/langchain/rag](https://docs.langchain.com/oss/python/langchain/rag)。

本案例建立在前两个案例的基础上，读者最好先跑通它们：

- **案例 1（create_agent 智能体核心）** 已经跑通了「工具调用循环」——模型自主决定调哪个工具、何时调，以及 `@tool` 装饰器、`create_agent` 的用法。本案例把「检索器」当成一个新工具交给 Agent，复用的正是那套循环机制。
- **案例 2（结构化输出）** 已经跑通了 `with_structured_output`（让模型返回经校验的 Pydantic 对象）以及 DeepSeek 上的策略选型。本案例的 Grader 评分器正是靠这套机制把模型的「相关 / 不相关」判断约束成一个结构化字段。

整条链路从知识库文档出发，到最终答案，依次经过这几个环节：

```
加载文档 → 切分成 chunk → 向量化嵌入 → 存入 InMemoryVectorStore
   → as_retriever 包成检索器 → @tool 包成工具 → create_agent 自主检索
   → Grader 评分（相关/不相关）→ 不相关则改写查询重试 → 生成答案
```

下文按这条链路的顺序逐步推进：先搭好「知识库 + 向量检索」这条底座（第二章），再把检索器变成工具交给 Agent（第三、四章），然后加上 Grader 质量门控（第五章），最后验证换一批文档即换一个业务场景（第六章）。每一步都有真实终端输出佐证。

本案例涉及的关键技术对象有五个：

- **InMemoryVectorStore（内存向量库）**：把文档片段的向量存在内存里、支持相似度检索的轻量向量库，来自 `langchain_core.vectorstores`；
- **`as_retriever`**：把向量库包装成统一的「检索器」接口，对外暴露 `k`（返回几条）等检索参数；
- **`@tool`**：案例 1 已用过的工具装饰器，本案例用它把检索器包成一个 Agent 可调用的工具；
- **GradeDocuments**：一个 Pydantic 数据模型，含一个 `binary_score` 字段（取值 `yes` / `no`），承载 Grader 对「文档是否相关」的二元判断；
- **改写重试循环（rewrite loop）**：当检索结果被判不相关时，自动改写查询、重新检索的有限次循环。

---

### 二、准备知识库与向量检索：从 12 篇 FAQ 到 as_retriever

RAG 的底座是一个能按语义检索的知识库。本章把这条底座从零搭起来：准备文档、切分、向量化、入库、包成检索器。本案例的知识库选用自建的电商客服 FAQ 文档——之所以自建而非抓取现成语料，是因为 agentic RAG 的教学核心是「换知识库即换业务」，用一组贴近真实业务的领域文档，读者最容易理解后续如何替换成自己的文档。

#### 1、准备 12 篇产品 FAQ 文档

第一步是准备知识库素材。本案例创建了 12 篇主题各异的电商客服 FAQ 文档，放在 `docs/` 目录下，每篇文件约 1 KB（终端清单显示字节大小在 984 到 1408 之间），覆盖订单、退款、物流、账号、支付、商品、售后、促销、换货、发票、会员、规则 12 个主题：

```bash
mkdir -p docs/
# 通过编辑器写入 faq_001.md 到 faq_012.md（共 12 篇）
ls -la docs/*.md
```

![终端显示 docs 目录下 faq_001.md 到 faq_012.md 共 12 个文件清单，每行含权限、属主、字节大小（984 到 1408 字节不等）、创建时间](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step1-faq-docs.png)

终端列出了 12 个文件，字节大小从 984 到 1408 不等，文档数量为 12，达到了「知识库不少于 10 篇」的下限。这个下限不是随意定的：知识库太薄（少于 10 篇）时检索几乎无意义——文档总量小，语义区分度不够，检索器很难体现「按意思找」的价值。12 篇是让检索效果可观察的一个合理起点。

文档内容是真实的电商客服场景文本，比如 `faq_002.md` 讲退款与退货、`faq_011.md` 讲会员等级权益。后文第六章会看到，把这批 FAQ 整体换成另一批文档（如公司开发规范），整套流程无需改动——这正是自建领域文档的好处：替换路径一目了然。

#### 2、安装依赖并用 RecursiveCharacterTextSplitter 切分

文档准备好后，需要把每篇文档切成更小的片段（chunk）。原因在于向量检索的粒度：整篇文档太长，向量化后语义被「平均」掉，检索精度差；切成小片段后，每个片段聚焦一个话题，检索能精准定位到「讲退款到账时间的那一段」而非「整篇退款文档」。

切分用 LangChain 的 `RecursiveCharacterTextSplitter`（递归字符切分器）。它所在的 `langchain-text-splitters` 包以及后续向量化要用的 HuggingFace 相关包，需要先安装：

```bash
pip install langchain-text-splitters langchain-huggingface sentence-transformers --quiet
```

这三个包的作用：`langchain-text-splitters` 提供切分器；`langchain-huggingface` 提供下一步要用的 `HuggingFaceEmbeddings`；`sentence-transformers` 是 HuggingFace 的句向量库，是 embedding 模型的底层运行时。首次安装时 `sentence-transformers` 体积较大，且后续首次加载模型还会从网络下载几十 MB 的模型权重，需预留时间和网络。

> ⚠️ macOS 外接存储的一个真实坑：本案例的虚拟环境装在外接 SSD 上，安装完依赖后导入 `HuggingFaceEmbeddings` 直接报 `UnicodeDecodeError`。根因是 macOS 在外接磁盘（ExFAT / APFS）上会生成大量以 `._` 开头的资源分叉文件，`transformers` 最新版在扫描 `models/` 目录时会读到这些二进制文件并尝试用 UTF-8 解码，于是报错。解决办法是把这些文件清理掉：
>
> ```bash
> find .venv/lib/python3.13/site-packages/transformers -name "._*" -type f -delete
> find docs/ -name "._*" -type f -delete
> ```
>
> 本案例实操中这一条命令删除了 5726 个 `._*` 文件，之后 `transformers` / `langchain_huggingface` / `sentence_transformers` 全部恢复正常导入。如果读者也在 macOS 外接磁盘上跑、遇到同样的 `UnicodeDecodeError`，用这条 `find ... -delete` 修复即可。

依赖就绪后，把 12 篇文档加载进来，用 `RecursiveCharacterTextSplitter` 切分。关键参数是 `chunk_size`（每片最大字符数）和 `chunk_overlap`（相邻片段的重叠字符数）：

```python
# step2_rag_split.py（节选）
from langchain_text_splitters import RecursiveCharacterTextSplitter

# docs 为加载进来的 12 篇 Document
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
doc_splits = splitter.split_documents(docs)
print("actual_docs:", len(docs), "actual_chunks:", len(doc_splits))
```

```bash
python step2_rag_split.py
```

![终端输出 Step 2 切分结果：actual_docs 为 12、actual_chunks 为 19，splitter type 为 RecursiveCharacterTextSplitter（chunk_size=500, overlap=50），逐条列出前 3 个 chunk 的 source、length（391/425/456 chars）与正文 preview，末行 PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step2-split.png)

12 篇文档切出了 19 个 chunk。输出里逐条列出了前 3 个 chunk 的来源文件、长度和正文预览，比如 chunk[0] 来自 `faq_001.md`、长度 391 字符、预览是「# 订单查询常见问题」。

这里有两个参数选择值得解释。`chunk_size=500` 是每片的目标上限，本案例的 FAQ 文档每篇千字左右，切成 500 字符的片段后，多数文档被切成 1 至 2 片，正好对应「一个问答话题一片」的粒度。`chunk_overlap=50` 让相邻片段重叠 50 字符，作用是防止一个完整句子或一个关键信息恰好被切断在两片边界上——重叠能保证边界处的语义不丢。这两个值在不同语料下需要调整：文档越长、话题越密集，`chunk_size` 可适当调大。

「递归」二字指的是它的切分策略：优先按段落（`\n\n`）切，切不动再按换行、句号、空格逐级回退，尽量在「自然语义边界」处下刀，而不是机械地每 500 字符一刀切断。这是它比朴素的「定长切分」更适合中文文档的原因。

#### 3、HuggingFaceEmbeddings 向量化 + InMemoryVectorStore 入库 + as_retriever

切好的 19 个 chunk 还是纯文本，检索器没法直接按语义比对。需要先把每个 chunk 转成一个向量（embedding，词嵌入）——一串浮点数，让语义相近的文本在向量空间里距离也近。检索时把用户问题也转成向量，找出距离最近的几个 chunk，就实现了「按意思找而非按关键词找」。

向量化用 `HuggingFaceEmbeddings`，底层模型选 `sentence-transformers/all-MiniLM-L6-v2`。这是 HuggingFace 上一个广泛使用的轻量句向量模型，模型页为 [huggingface.co/sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)，它把任意文本编码成 384 维向量，体积小、本地可跑、无需 API Key：

![HuggingFace 上 all-MiniLM-L6-v2 模型页面，标题为 sentence-transformers/all-MiniLM-L6-v2，页面展示该模型把句子和段落映射为 384 维稠密向量的说明与 Usage 示例代码](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step3-hf-model-page.png)

选本地 HuggingFace embedding 而非 `OpenAIEmbeddings`，是出于无 API Key 也能跑通的考虑——本案例全程用 DeepSeek 作为对话模型、用本地 HuggingFace 模型做向量化，二者互不依赖。

向量化后，把 19 个向量存进 `InMemoryVectorStore`（内存向量库），再用 `as_retriever` 把它包成检索器。`InMemoryVectorStore` 是 LangChain 自带的轻量向量库，向量都存在进程内存里，适合教学和原型；`as_retriever(search_kwargs={"k": 3})` 中的 `k=3` 表示每次检索返回最相关的 3 个片段：

```python
# step3_rag_vectorstore.py（节选）
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = InMemoryVectorStore.from_documents(doc_splits, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 检索验证
docs = retriever.invoke("退款需要多久到账？")
for i, d in enumerate(docs):
    print(f"  [{i}] source={d.metadata['source']}")
```

```bash
python step3_rag_vectorstore.py
```

![终端输出 Step 3 结果：actual_docs 12 / actual_chunks 19，加载 HuggingFaceEmbeddings 模型 all-MiniLM-L6-v2，InMemoryVectorStore 构建完成 19 个向量入库，as_retriever 完成 search_kwargs k=3，检索验证 query「退款需要多久到账？」返回 3 个文档 [0]faq_012.md [1]faq_005.md [2]faq_007.md，末行 PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step3-vectorstore.png)

19 个向量入库成功，检索器以 `k=3` 就绪。但这里有一个值得停下来看的细节：用「退款需要多久到账？」做检索验证，返回的第一个片段 `[0]` 来自 `faq_012.md`（讲评价修改），对这个退款问题其实不是最相关的。也就是说，**检索器返回的「最相关 3 篇」里，混进了不相关的文档**。

这不是 bug，而是向量检索的固有特性：embedding 模型对语义的理解有限，尤其是英文优化的 `all-MiniLM-L6-v2` 处理中文时，相似度排序会出偏差。这个现象恰好是后文引入 Grader 的直接动机——既然检索结果可能混入不相关片段，就需要一道质量门控来过滤。这个伏笔先埋在这里，第五章揭晓。

##### embedding 模型选型：换一个多语言模型，中文检索明显变准

既然上一步暴露了「英文模型处理中文不准」的问题，这里顺势做一个对照实验：把 embedding 模型从 `all-MiniLM-L6-v2`（英文优化）换成 `paraphrase-multilingual-MiniLM-L12-v2`（多语言，支持 50 种语言），同样的查询看检索结果差异。换模型只需改一行 `HuggingFaceEmbeddings(model_name=...)` 再重建向量库，其余代码不动：

```bash
python ext7_4_embedding_swap.py
```

![终端输出拓展实验 4 embedding 模型对比：query「退款审核多久」下，模型 A（all-MiniLM-L6-v2）top1 返回 faq_012 评价修改（不相关），模型 B（multilingual-MiniLM-L12-v2）top1 返回 faq_002 退款与退货 FAQ（正确）；query「商品库存不足」下模型 A 全部不相关、模型 B 命中 faq_006 商品库存；结论为多语言模型对中文语义理解更准、换 embedding 只需改 HuggingFaceEmbeddings model_name 一行](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--extension-4-embedding-swap.png)

对比结果很清晰。三个中文查询里，英文优化的模型 A 有两个返回了不相关文档（「退款审核多久」返回评价修改文档、「商品库存不足」返回余额退款文档），而多语言模型 B 三个查询全部命中最相关文档。这带出三条实用结论：

- **中文知识库优先选多语言或中文专用 embedding 模型**：如 `paraphrase-multilingual-MiniLM`、`BAAI/bge-small-zh` 等，检索质量比英文优化模型明显更好。embedding 选型是 RAG 系统最重要的工程决策之一，直接决定检索能不能找对内容。
- **换 embedding 模型零架构成本**：因为 `InMemoryVectorStore` 的 embedding 接口是统一的，换模型只改 `model_name` 一行加重建向量库，检索器、工具、Agent 全不用动。
- **embedding 不准也不致命**：就算 embedding 排序有偏差，第五章的 Grader 还能把不相关结果过滤掉——这从另一个角度说明了 Grader 这道门控的价值。

---

### 三、把检索器变成工具：@tool 包装

底座搭好后，检索器目前还是一个需要开发者手动调用的对象（`retriever.invoke(...)`）。要让 Agent「自主决定何时检索」，得把检索器包装成一个**工具**——案例 1 已经讲过，工具是 Agent 的能力单元，模型靠工具的描述自己判断何时调用。

#### 1、用 @tool 把检索器包成 search_docs 工具

用案例 1 介绍过的 `@tool` 装饰器，把「调用检索器 + 拼接结果」这段逻辑包成一个名为 `search_docs` 的工具。关键在 docstring——案例 1 强调过，docstring 不是注释，而是模型判断「何时调这个工具」的直接依据：

```python
# step4_rag_tool.py（节选）
from langchain_core.tools import tool

@tool
def search_docs(query: str) -> str:
    """搜索电商平台知识库，获取关于订单、退款、物流、账号、支付、售后等问题的答案。"""
    docs = retriever.invoke(query)
    return "\n\n".join(f"[来源: {d.metadata['source']}]\n{d.page_content}" for d in docs)
```

```bash
python step4_rag_tool.py
```

![终端输出 Step 4 结果：工具名称 search_docs，工具描述为搜索电商平台知识库获取订单退款物流账号支付售后等问题答案，工具类型 langchain_core.tools.structured.StructuredTool，工具调用验证 query「退款申请需要几个工作日？」返回 400 chars、来源 faq_008.md，末行 PASS @tool 包装完成可加入 create_agent](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step4-tool-wrap.png)

包装后 `search_docs` 的类型是 `StructuredTool`，工具调用验证返回了来自 `faq_008.md` 的 400 字符内容。这里 docstring 写的是「搜索电商平台知识库，获取关于订单、退款、物流……等问题的答案」——这段话会被 `create_agent` 拼进模型的工具清单，模型据此判断用户问题该不该走这个工具。docstring 的措辞精度，直接决定了工具在边界场景下被不被调用，下面的对照实验把这一点演示得很直观。

##### docstring 决定工具调用：问知识库之外的问题，Agent 怎么反应

工具的 docstring 既然是模型选工具的依据，那么问一个知识库完全覆盖不到的问题，Agent 会怎么做？做一个反例实验，问三类不同的「界外问题」，看 Agent 的工具调用行为：

```bash
python ext7_3_retrieval_miss.py
```

![终端输出拓展实验 3 检索未命中行为观察：问「今天深圳的天气怎么样？」tool_calls 0 次、Agent 不调工具直接用 LLM 回答无法获取实时天气；问「帮我写一首关于春天的诗」tool_calls 0 次、直接创作；问「苹果公司的市值是多少？」tool_calls 1 次、调了 search_docs 但检索无结果后用 LLM 兜底；观察总结指出完全无关问题不调工具、边界模糊问题会误触工具、这正是 Grader 的价值](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--extension-3-retrieval-miss.png)

三个问题的行为各不相同：

- **完全无关的问题（天气、写诗）**：Agent `tool_calls` 为 0，根本不调 `search_docs`，直接用模型自身能力回答。因为这两个问题和 docstring 描述的「电商平台知识库」毫不沾边，模型判断「这个工具帮不上忙」。
- **边界模糊的问题（苹果公司市值）**：Agent 调了一次 `search_docs`——「苹果」这个词与「商品」沾了点边，触发了工具调用；但检索回来的内容不相关，模型随即用自身知识兜底回答。

这印证了三点：其一，`@tool` 的 docstring 是 Agent 工具选择的实际依据，措辞越精确，误触越少；其二，「检索未命中」不会让 Agent 崩溃，它会退回到用模型自身知识兜底；其三，这个「兜底」行为是不可控的——模型可能基于自身知识答一个知识库里根本没有的内容。如何把这个兜底变得可控（明确告诉用户「知识库里没有」），正是第五章 Grader 要解决的问题。

---

### 四、create_agent 自主检索：组装简化版 RAG Agent

工具就绪，现在用案例 1 的 `create_agent` 把模型和 `search_docs` 工具组装成一个完整的 RAG Agent。这一版先不加 Grader，叫「简化版」——目的是先看清 Agent 在 RAG 场景下「自主检索」到底是什么样子。

#### 1、组装 Agent 并观察自主检索与改写

组装方式与案例 1 完全一致：`create_agent` 传入模型和工具列表。模型沿用 DeepSeek 的 `deepseek-chat`（支持工具调用）：

```python
# step5_rag_agent_simple.py（节选）
from langchain.agents import create_agent

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[search_docs],
)
result = agent.invoke({"messages": [{"role": "user",
    "content": "退款审核通过后，用微信支付的订单多久到账？"}]})

for i, msg in enumerate(result["messages"]):
    print(f"  [{i}] {type(msg).__name__} → ...")
```

```bash
python step5_rag_agent_simple.py
```

![终端输出 Step 5 简化版 create_agent 自主检索：agent 类型 CompiledStateGraph，用户问题「退款审核通过后，用微信支付的订单多久到账？」，消息流共 8 条——[0]HumanMessage，[1][3][5] 均为 AIMessage 发起 search_docs 工具调用（query 三次不同：「微信支付 退款 审核通过 到账时间」「退款到账时间 微信支付 多久」「退款 微信支付 到账 原路返回」），[2][4][6] 为 ToolMessage 来源 faq_005.md，[7]AIMessage 最终回答微信支付退款通常 1~7 个工作日到账；末行 PASS、tool_calls 包含 search_docs True](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step5-agent-retrieves.png)

消息流共 8 条，比案例 1 单工具问答的 4 条多了一倍。看 `[1]`、`[3]`、`[5]` 三条 AIMessage——它们都发起了 `search_docs` 工具调用，但每次的 `query` 参数不一样：

- 第 1 次：`微信支付 退款 审核通过 到账时间`
- 第 2 次：`退款到账时间 微信支付 多久`
- 第 3 次：`退款 微信支付 到账 原路返回`

也就是说，**Agent 自己改写了三次查询、检索了三次**。第一次检索的结果不够精准，模型没有直接拿来作答，而是换了一组关键词重新检索；第二次还不满意，再换第三次。直到 `[7]` 才基于检索内容给出最终回答（微信支付退款通常 1 到 7 个工作日到账）。

这个「自动改写查询重试」的行为，是 agentic RAG 区别于固定 `RetrievalQA` 链的最直观体现。固定链只检索一次、拿到什么用什么；而 Agent 把检索当成一个可以反复调用的工具，会像人一样「这次没查准，换个说法再查」。这正是「agent 自主性」在 RAG 场景下的价值。

但这一版也暴露了一个问题：Agent 改写了三次仍未能精准命中「退款到账时间」对应的文档（faq_002），这三次「换关键词重试」全凭模型自己感觉，没有一个明确的标准来判断「这次检索结果到底够不够好、要不要继续改写」。换句话说，**重试的「停止条件」是模糊的**。给重试循环装上一个明确的质量判断标准，正是第五章 Grader 要补的关键一环。

---

### 五、Grader 质量门控：GradeDocuments + binary_score + 改写循环

第三章看到检索可能混入不相关文档，第四章看到 Agent 的改写重试缺一个明确的停止标准。这两个问题的共同答案是 **Grader（评分器）**：每次检索后，让一个评分器逐篇判断「这篇文档和问题相关吗」，相关就停止改写、用它作答，不相关就改写查询重试。这是 agentic RAG 的质量门控核心，也是本案例反偏离约束要求必须跑到的环节。

#### 1、用 GradeDocuments + with_structured_output 创建 Grader

Grader 要输出的是一个明确的「相关 / 不相关」判断。这正是案例 2 讲过的结构化输出的用武之地——定义一个 Pydantic 模型 `GradeDocuments`，只含一个 `binary_score` 字段（取值 `yes` / `no`），再用 `with_structured_output` 把模型的判断约束成这个结构：

```python
# step6_rag_grader.py（节选）
from pydantic import BaseModel, Field

class GradeDocuments(BaseModel):
    """对检索到的文档与问题相关性的二元评分"""
    binary_score: str = Field(description="文档是否与问题相关，回答 'yes' 或 'no'")

# 关键：DeepSeek 需指定 method='function_calling'
grader = llm.with_structured_output(GradeDocuments, method='function_calling')
```

这里有一个 DeepSeek 上的关键坑，与案例 2 的策略选型同源，必须讲清楚：

> ⚠️ `with_structured_output(GradeDocuments)` 默认走 `json_schema` 这种 provider 原生结构化输出模式，而 DeepSeek 不支持它，会直接报 400 错误 `This response_format type is unavailable now`。解决办法是显式指定 `method='function_calling'`，让 DeepSeek 通过工具调用（function calling）的方式返回结构化结果。这与案例 2 中「DeepSeek 必须用 ToolStrategy 而非 ProviderStrategy」是同一个兼容性边界的两种体现——本质都是 DeepSeek 没有原生结构化输出 API、只能走工具调用兜底。DeepSeek、Qwen 等国产模型遇到 `with_structured_output` 报 400，统一用 `method='function_calling'` 解决。

Grader 创建好后，对每次检索到的每篇文档评分：只要有一篇得到 `binary_score=yes`，就判定本轮检索「找到了相关内容」，停止改写；如果三篇全是 `no`，就改写查询重试：

```bash
python step6_rag_grader.py
```

![终端输出 Step 6 Grader 评分与改写循环：Grader 类型 with_structured_output(GradeDocuments)、binary_score 字段 yes/no；测试1 退款相关问题「申请退款后商家多久审核？」第 1 次检索 3 个文档评分 doc[0]faq_007 no、doc[1]faq_009 yes、doc[2]faq_005 no，Grader 判定相关至少 1 个 yes 停止改写；测试2 会员积分问题「黄金会员每年能获得几张折扣券？」doc[0]faq_011 yes、doc[1]faq_011 no、doc[2]faq_008 no，同样停止改写；评分循环总结 测试1 grades=[no,yes,no] 停止、测试2 grades=[yes,no,no] 停止；末行 PASS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step6-grader-score.png)

两个测试都跑出了清晰的评分结果：

- **测试 1（退款审核问题）**：三篇文档评分 `['no', 'yes', 'no']`——`faq_009.md` 被判相关（`yes`），于是「至少 1 个 yes」，停止改写，用它作答。
- **测试 2（会员积分问题）**：三篇文档评分 `['yes', 'no', 'no']`——`faq_011.md`（会员等级权益）被判相关，同样停止改写。

两个测试都在第一轮就找到了相关文档（命中 `yes`），所以都直接 `STOP`。`binary_score` 字段在 DeepSeek 的 function calling 模式下稳定输出 `yes` / `no`，没有出现自由文本或格式漂移。

这里的设计取舍值得点明：Grader 的停止条件是「**至少一篇 yes**」而非「全部 yes」。原因是检索返回的 3 篇里，只要有一篇真正相关，就足够支撑作答，不必苛求三篇全相关。这是「召回」与「精度」之间的一个工程平衡。

##### Grader 的完整决策 trace：相关就停、全不相关就循环改写

上面两个测试都在第一轮命中，没看到「改写重试」真正发生。再做一个实验，专门展示 Grader 在「知识库有答案」和「知识库没有答案」两种情况下的完整决策过程：

```bash
python ext7_1_grader_decision_trace.py
```

![终端输出拓展实验 1 Grader 决策 Trace：测试1 知识库有答案问题「会员积分多久过期？」第 1 轮检索 doc[0]faq_007 binary_score=no、doc[1]faq_011 yes、doc[2]faq_012 no，决策 STOP 找到相关文档 1 轮完成；测试2 知识库外问题「如何在 Python 中实现快速排序算法？」第 1 轮全部 no 决策 REWRITE 改写为「Python 快速排序代码实现示例」、第 2 轮全部 no REWRITE、第 3 轮全部 no REWRITE 达最大重试；总结 binary_score=yes 触发 STOP、全 no 触发 REWRITE 改写循环 3 轮](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--extension-1-grader-decision-trace.png)

两个测试把决策逻辑摊开了：

- **测试 1（会员积分，知识库有答案）**：第 1 轮检索就有 `faq_011.md` 得 `yes`，决策 `STOP`，一轮完成。
- **测试 2（Python 快速排序，知识库没有答案）**：第 1 轮三篇全 `no`，触发 `REWRITE`，模型把查询从「如何在 Python 中实现快速排序算法？」改写成「Python 快速排序代码实现示例」；第 2 轮仍全 `no`，再改写；第 3 轮还是全 `no`，达到最大重试次数后停止。

这个 trace 揭示了改写循环的三个机制：`binary_score=yes` 触发停止（不过度检索）；全 `no` 触发改写重试（模型自动换一组关键词，模拟人「换个方式问」）；以及最关键的——**改写循环有上限（最大重试次数）**。如果没有这个上限，知识库里本就没有的问题会让 Agent 无限改写、无限检索，白白消耗 token。最大重试次数是工程上必须设置的一个参数。当达到上限仍全 `no` 时，意味着知识库里确实没有答案，这时该走 fallback（兜底）策略——明确告诉用户「知识库无此内容」。

##### 简化版 vs 进阶版：Grader 到底带来了什么

回到一个根本问题：第四章的简化版（无 Grader）和本章的进阶版（带 Grader），对用户而言差别到底在哪？做一个直接对比，同一个问题两版都跑：

```bash
python ext7_2_simple_vs_graded.py
```

![终端输出拓展实验 2 简化版 vs 进阶版对比：问题「黄金会员一年有几张折扣券？」（知识库有答案）简化版回答黄金会员一年有 4 张专属 9 折券、进阶版相关文档 faq_011.md 同样回答 4 张，两版结果相同进阶版只用经 Grader 筛选的相关文档；问题「如何在 Python 中快速排序？」（知识库外）简化版没有编程文档但用 LLM 自身知识乱答直接给 quicksort 代码、进阶版相关文档为空 Grader 全判 no 先说明知识库无内容再给通用知识；核心差异 进阶版过滤不相关文档、知识库外问题不乱答](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--extension-2-simple-vs-graded.png)

对比分两种情况：

- **知识库内的问题（黄金会员折扣券）**：两版答案质量相当，都答出了「一年 4 张专属 9 折券」。区别在于进阶版只用了经 Grader 筛选的相关文档（`faq_011.md`），输出更「干净」。
- **知识库外的问题（Python 快速排序）**：这是两版差别最大的地方。简化版检索发现没有编程文档后，**直接用模型自身知识「绕过」知识库答了一段快速排序代码**——这就是幻觉风险：用户以为答案来自知识库，实际是模型自己编的。进阶版的 Grader 把检索结果全判 `no`，于是先明确声明「知识库无相关内容」，再补充通用知识，知识边界清清楚楚。

这个对比点出了 Grader 在企业场景的真正价值：在合规、法律、公司制度这类知识库问答里，**「不知道就说不知道」比「编一个看似合理的答案」重要得多**。简化版速度优先但有幻觉风险，进阶版可控性优先、Grader 充当质量门控——企业级 RAG 几乎都需要这道门控来守住知识边界。

---

### 六、换数据即换业务：复用验证

前五章都围绕电商 FAQ 这一个知识库。本案例最后验证一个关键命题：**把知识库换成另一个完全不同的业务，需要改多少代码？** 把 `docs_dir` 从电商 FAQ 目录换成一批「公司技术开发规范」文档，其余代码原封不动，看 Agent 能不能基于新知识库正确作答。

```python
# step7_rag_reuse.py：唯一改动一行
# docs_dir = Path("docs")       # 原来：电商 FAQ
docs_dir = Path("new_docs")     # 换后：开发规范
# 切分、向量化、入库、@tool、create_agent、Grader 全部代码不变
```

```bash
python step7_rag_reuse.py
```

![终端输出 Step 7 换数据复用：场景为将 FAQ 知识库换成公司技术开发规范文档，框架代码对比显示唯一改动 docs_dir 从 Path('docs') 电商 FAQ 改为 Path('new_docs') 开发规范、其余代码 100% 不变；InMemoryVectorStore 新知识库 5 个 chunk 入库；测试问题「PR 提交需要几个人 review 才能合并？」消息流 4 条——[0]HumanMessage、[1]AIMessage 发起 search_docs、[2]ToolMessage 来源 dev_rule_001.md 代码提交规范、[3]AIMessage 回答所有 PR 必须经过至少 2 名团队成员 review 后才能合并；末行 PASS 换数据复用验收通过、原始知识库电商 FAQ 12 篇换为开发规范 5 篇、代码改动只改了 docs_dir 1 处](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-7--shot--step7-reuse.png)

结果印证了命题：**只改 `docs_dir` 一行，框架代码 100% 不变**，Agent 就从「电商客服问答」切换到了「开发规范问答」。新知识库的 5 个 chunk 入库后，问「PR 提交需要几个人 review 才能合并？」，Agent 自主调用 `search_docs` 从 `dev_rule_001.md` 检索到代码提交规范，正确回答「所有 PR 必须经过至少 2 名团队成员 review 后才能合并」。

这就是 agentic RAG「换知识库即换业务」的核心价值。整套结构——切分、向量化、`InMemoryVectorStore`、`as_retriever`、`@tool` 包装、`create_agent`、Grader 评分——与「电商」这个领域毫无关系，它只是一套通用的知识库问答框架。要把它用到自己的业务，换的只是喂进去的文档。这正是下一章迁移指南要展开的。

---

### 七、自学迁移指南：把电商 FAQ 换成你的知识库

本案例用电商客服 FAQ 跑通了 agentic RAG 的完整链路，但这套结构与「电商」无关。要把它迁移到自己的知识库（产品手册、公司制度、个人笔记、技术文档等），关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的业务）

需要改动的只有两处，且都很轻：

- **知识库文档**：把 `docs/` 目录里的电商 FAQ 换成你自己的文档即可。格式上 Markdown、纯文本均可——第六章已演示，换一批文档只改 `docs_dir` 一行。文档数量建议不少于 10 篇，太薄检索意义不大。
- **embedding 模型（按语言选）**：如果你的知识库是中文，强烈建议把 `HuggingFaceEmbeddings` 的 `model_name` 从英文优化的 `all-MiniLM-L6-v2` 换成多语言或中文专用模型（如 `paraphrase-multilingual-MiniLM-L12-v2`、`BAAI/bge-small-zh`）。第三章的对照实验已证明，多语言模型对中文检索明显更准。换模型只改 `model_name` 一行加重建向量库。

下面是「电商 FAQ → 你的知识库」的最小改写骨架，对照着改即可：

```python
# 改之前（本案例）
docs_dir = Path("docs")  # 电商 FAQ
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 改之后（换成你的中文知识库，如公司制度文档）
docs_dir = Path("company_policies")  # 你的文档目录
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")  # 中文场景换多语言模型
```

此外，`@tool` 装饰的 `search_docs` 的 docstring 最好按你的知识库领域改写——把「电商平台知识库」换成「公司制度知识库」之类的准确描述。第三章演示过，docstring 是 Agent 判断何时检索的依据，描述越贴合你的领域，工具调用越精准、误触越少。

#### 2、保持不变的部分（结构骨架）

下面这些是迁移后依然成立的骨架，不需要改动：

- **切分与入库流程**：`RecursiveCharacterTextSplitter` 切分 → `HuggingFaceEmbeddings` 向量化 → `InMemoryVectorStore.from_documents` 入库 → `as_retriever(k=3)` 包检索器，这条流水线不变；
- **`@tool` 包装检索器的方式**：用 `@tool` 把检索器包成工具，docstring 描述能力，结构不变；
- **`create_agent` 组装方式**：`model` + `tools=[search_docs]` 的组装方式与案例 1 一致；
- **Grader 质量门控**：`GradeDocuments` + `binary_score` + `with_structured_output(method='function_calling')` + 改写循环这套结构不变——尤其 DeepSeek / 国产模型上 `method='function_calling'` 这个参数必须保留。

#### 3、迁移后如何验证跑通

换完文档后，按本案例的验收方式自检，确认迁移成功：

1. **检索验证**：先单独跑检索器（`retriever.invoke("你的领域问题")`），确认返回的片段确实来自相关文档。若返回的全是不相关文档，多半是 embedding 模型不匹配语言，回到第三章换多语言模型；
2. **自主检索验证**：用 `create_agent` 组装后，提一个需要查知识库才能答的问题，`invoke` 后检查消息流里是否出现 `search_docs` 的 `tool_calls` 和对应的 `ToolMessage`，确认 Agent 真的去检索了；
3. **Grader 门控验证**：分别问一个「知识库有答案」和一个「知识库没有答案」的问题。前者应有文档得 `binary_score=yes` 并正常作答；后者应全部 `no`、Agent 明确声明「知识库无此内容」而非编造答案——这一条是 Grader 是否生效的关键标志。

三项都通过，就说明 agentic RAG 在你的知识库上完整跑通了。

#### 4、迁移前置假设清单

迁移顺利的前提是具备以下条件，动手前先核对：

- **已掌握案例 1 与案例 2**：本案例的 `@tool` + `create_agent` 来自案例 1，Grader 的 `with_structured_output` 来自案例 2。若对工具调用循环或结构化输出还不熟，建议先回到对应案例；
- **理解向量检索不是默认知识**：不要假设「检索一定能找对内容」是理所当然的——向量检索是「按语义近似找」，embedding 模型选不对（尤其中文用英文模型）就会找偏。第三章的对照实验专门演示了这一点；
- **DeepSeek / 国产模型必须用 `method='function_calling'`**：Grader 的 `with_structured_output` 在 DeepSeek 上默认会报 400，务必显式指定 `method='function_calling'`。迁移时若 Grader 报 `This response_format type is unavailable now`，先检查这个参数；
- **`InMemoryVectorStore` 是教学/原型选择，不是生产方案**：它把向量存在进程内存里，进程一退向量就没了，每次启动都要重新向量化全部文档。要把 agentic RAG 推到生产，需要把 `InMemoryVectorStore` 换成持久化向量库（如 Chroma、Pinecone 等），并考虑异步检索、批量 Grader 评分、达到最大重试后的 fallback 策略等工程优化——这些超出本案例范围，是生产化时要补的下一步。

把这几点核对清楚，本案例的电商客服问答就能稳妥地迁移成你自己知识库的 agentic RAG 问答系统。


---

## DeepAgents 长程智能体框架（deepagents）从零到一跑通实操手册

### 一、开篇：长程任务为什么需要一套额外的脚手架

案例 1 跑通了 `create_agent` 的工具调用循环，案例 3 又把横切逻辑收进了 middleware（中间件）这一层。到目前为止，搭出来的 Agent 处理「查一个订单、算一笔运费」这种一两步就能结束的短任务绰绰有余。但真实业务里有另一类任务：让 Agent 写一份多源市场调研报告、整理十几篇论文的要点、按章节起草一篇长文。这类任务有一个共同特征——**步骤多、链路长**，往往要十几步甚至几十步才能完成。把这类任务直接交给一个裸的 `create_agent`，会接连撞上三道墙：

- **越走越忘**：任务拆成十几步后，模型走到第 8 步时常常忘了第 3 步的计划，或者重复做已经做过的事。没有一个显式的「待办清单」帮它记住「还剩哪些没干」，长链路就会失控。
- **上下文（context）越堆越满**：每一步检索回来的中间数据都堆进对话历史里，十几步下来，原始资料把模型的上下文窗口（context window，模型单次能读到的文本上限）塞爆。「长任务塞太多中间信息、模型记不过来」正是长程 Agent 最常见的翻车点。
- **中间结果无处暂存**：短任务的中间结果放在对话里就行，长任务却需要一个地方把「第 3 步检索到的数据」存下来，等第 10 步整合时再取出，而不是一直挂在上下文里占地方。

`deepagents` 就是为解决这三道墙而生的一套**开箱即用的长程智能体脚手架**。它由 LangChain 官方维护，项目主页见 [docs.langchain.com/oss/python/deepagents/overview](https://docs.langchain.com/oss/python/deepagents/overview)，源码仓库在 [github.com/langchain-ai/deepagents](https://github.com/langchain-ai/deepagents)，PyPI 包名直接是 [deepagents](https://pypi.org/project/deepagents/)。它的设计定位是「batteries-included agent harness」——电池全装好的智能体脚手架，意思是把长程任务需要的能力预先打包，开发者一行代码就能用上。

需要先讲清楚 `deepagents` 与前两个案例的关系，因为这决定了它的本质：**`deepagents` 不是一个全新的运行时（runtime），而是 `create_agent` 加上一组预装好的 middleware**。案例 3 演示过 middleware 是怎么一个个手动挂到 `create_agent` 上的；`deepagents` 做的事，就是把长程任务最需要的几个 middleware 提前组合好、装进一个叫 `create_deep_agent` 的入口里。换句话说，它和案例 3 是同一套机制，区别只是「开箱即用」对「手动挑装」。这一点会在第三章用 graph nodes（计算图节点）直接验证。

本案例围绕 `deepagents` 的三大机制展开，每个机制正对应上面的一道墙：

- **规划机制（write_todos）**：让 Agent 在开工前先写一份待办清单，逐步更新完成状态，解决「越走越忘」；
- **委派机制（task）**：把耗费上下文的子任务丢给独立的子 Agent（SubAgent）去做，主 Agent 只收最终结果，解决「上下文越堆越满」；
- **虚拟文件系统（write_file / read_file / ls）**：给 Agent 一块可读写的暂存区，中间结果写进文件而不是堆在对话里，这是一种典型的「上下文工程」（context engineering，主动管理模型上下文里放什么）手段。

> ⚠️ 版本说明：`deepagents` 当前处于 pre-1.0 阶段，本手册基于 **v0.6.7** 实测，要求 Python ≥ 3.11、< 4.0。pre-1.0 意味着接口尚未冻结，后续版本的工具名、参数名可能调整。因此本手册的重点放在**不易过期的设计理念**（三大机制、三层取舍）上，具体 API 名都标注了版本基线，落地时建议对照当时的官方 reference 再核对一遍。

---

### 二、准备工作：安装 deepagents 与核对 v0.6.7 API

#### 1、安装 deepagents 并确认版本

本案例沿用前序案例的工作目录与 Python 虚拟环境（venv）。零起点的读者，完整路径是：先确保本机装有 Python 3.11 及以上版本（命令行执行 `python --version` 确认），在项目目录下用 `python -m venv .venv` 建一个虚拟环境并激活，随后安装 `deepagents`：

```bash
cd hello-langchain
.venv/bin/pip install deepagents
```

`deepagents` 是一个独立的 PyPI 包，安装时会自动带上它依赖的 `anthropic`、`langchain-anthropic`、`langchain-google-genai` 等库。安装完成后会显示 `deepagents-0.6.7` 安装成功。

#### 2、核对 v0.6.7 的 API 与内置工具

因为是 pre-1.0 版本，装好后第一件事不是急着写代码，而是**先核对一遍 API**——确认包版本、`create_deep_agent` 入口可导入、三大机制对应的内置工具名是什么、定义子 Agent 需要哪些字段。用一段核验脚本一次性把这些信息打出来：

```python
import deepagents
print('version:', deepagents.__version__)
from deepagents import create_deep_agent              # 主入口
from langchain.agents.middleware import TodoListMiddleware  # 规划机制来源
from deepagents.middleware.subagents import SubAgent  # 子 Agent 定义类型
from deepagents import FilesystemMiddleware           # 虚拟文件系统来源
```

```bash
.venv/bin/python -c "..."   # 上述核验脚本
```

![deepagents 0.6.7 安装核验：version 0.6.7，create_deep_agent / TodoListMiddleware(write_todos) / SubAgent / FilesystemMiddleware 均导入 OK，内置工具 write_todos（规划）+ ls/read_file/write_file/edit_file（虚拟文件系统）+ task（子 Agent 委派），SubAgent 必填字段 name/description/system_prompt 均为 str](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step1-deepagents-install-verify.png)

核验结果给出了贯穿全案例的几个关键事实，值得逐一记下：

1. **三大机制的工具名在此确认**：规划用 `write_todos`，虚拟文件系统用 `ls` / `read_file` / `write_file` / `edit_file`，子 Agent 委派用 `task`。这些名字后面每一步都会反复出现。
2. **规划机制复用的是 langchain 的中间件**：`write_todos` 来自 `langchain.agents.middleware.TodoListMiddleware`——它本就是 LangChain 的一个内置 middleware（案例 3 列过的内置清单里就有 `TodoListMiddleware`），`deepagents` 直接复用，没有重造轮子。这是「`deepagents` = `create_agent` + 预装 middleware」的第一个直接证据。
3. **定义子 Agent 只需三个必填字段**：`SubAgent` 是一个 `TypedDict`（带类型标注的字典），必填字段是 `name`（名字）、`description`（描述）、`system_prompt`（系统提示词），且都是字符串。第五章定义子 Agent、第八章学员自定义子 Agent 都靠这三个字段。

这里还有两个 pre-1.0 的注意点，先标注、后面对应章节会用到：

- `create_deep_agent` 的 `model=None` 默认值自 v0.5.3 起已**弃用**（deprecated），必须**显式传入模型**，不能依赖默认值；
- 内置工具里还有一个 `execute`（执行代码），但它仅在沙箱后端（`SandboxBackendProtocol`）下可用，默认的 `StateBackend` 调用它会返回错误。本案例不涉及代码执行，用默认后端即可。

---

### 三、第一个 deep agent：create_deep_agent 最小示例

#### 1、用 create_deep_agent 一行搭出长程 Agent

确认完 API，先搭一个最小可运行的 deep agent，看看它返回什么、内部长什么样。`create_deep_agent` 的核心入参与 `create_agent` 高度一致：传入模型、工具列表、系统提示词。这里用 `ChatDeepSeek` 作模型、一个 mock 检索工具 `search_market_info`、一句「市场研究助手」的系统提示词：

```python
from deepagents import create_deep_agent
from langchain_deepseek import ChatDeepSeek

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),   # 必须显式传模型（model=None 已弃用）
    tools=[search_market_info],                   # 用户自定义的检索工具
    system_prompt="你是一个市场研究助手。",
)
print(type(agent))                                # 看返回类型
print(agent.get_graph().nodes)                    # 看内部计算图节点
```

```bash
.venv/bin/python step2_deep_agent_min.py
```

![Step 2 create_deep_agent 最小示例终端输出：model 为 ChatDeepSeek(deepseek-chat)，create_deep_agent 返回类型 CompiledStateGraph（模块 langchain.graph.state），isinstance 验证 True，graph nodes 为 ['__start__', 'model', 'tools', 'TodoListMiddleware.after_model', 'PatchToolCallsMiddleware.before_agent']，最小示例验证通过](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step2-create-deep-agent-min.png)

两个观察点值得拆解：

第一，`create_deep_agent` 返回的是 `CompiledStateGraph`（编译后的状态图）——和案例 1 里 `create_agent` 的返回类型**完全一致**。这印证了开篇的判断：`deepagents` 没有引入新的运行时，底层还是同一套 LangGraph 计算图，调用方式（`invoke` / `stream`）也和前两个案例一模一样。

第二，也是最关键的——打印出的 graph nodes 直接揭穿了 `deepagents` 的本质：

```
['__start__', 'model', 'tools', 'TodoListMiddleware.after_model', 'PatchToolCallsMiddleware.before_agent']
```

这串节点里，`__start__` / `model` / `tools` 是案例 1 里基础 Agent 就有的标准节点；多出来的 `TodoListMiddleware.after_model` 和 `PatchToolCallsMiddleware.before_agent` 才是 `deepagents` 自动挂上去的。其中 `TodoListMiddleware` 以 `after_model` 钩子（hook，案例 3 讲过的挂载时机）的形式自动接入——这正是规划机制 `write_todos` 的来源；`PatchToolCallsMiddleware` 以 `before_agent` 钩子接入，负责工具调用的标准化。一行 `create_deep_agent`，背后是好几个 middleware 的自动装配，graph nodes 把这个「自动装配」看得清清楚楚。

#### 2、对照实验：create_deep_agent 与 create_agent + 手装 middleware 的差别

既然 `deepagents` 的本质是「预装 middleware」，那它和案例 3 里「手动挑装 middleware」到底差在哪？用同一个任务、同一个工具，分别用两种方式搭 Agent，把各自的 graph nodes 打出来对比，差异就一目了然：

```python
# 方案 A：create_deep_agent（开箱即用）
agent_a = create_deep_agent(model, tools=[search_data], system_prompt=...)

# 方案 B：create_agent + 手动挂 TodoListMiddleware
agent_b = create_agent(model, tools=[search_data],
                       middleware=[TodoListMiddleware()])
```

```bash
.venv/bin/python ext2_deepagent_vs_create_agent.py
```

![对照实验终端输出：方案 A create_deep_agent 的 graph nodes 含 TodoListMiddleware.after_model + PatchToolCallsMiddleware.before_agent，方案 B create_agent 手装仅含 TodoListMiddleware.after_model（少了 PatchToolCallsMiddleware），对比结论 create_deep_agent = create_agent + TodoListMiddleware + FilesystemMiddleware + SubAgentMiddleware + PatchToolCallsMiddleware，附三层取舍建议](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--extension-2-deepagent-vs-create-agent.png)

对比结果把「开箱即用 vs 手装」的差别量化了：

- **方案 A（`create_deep_agent`）** 的节点里有 `TodoListMiddleware.after_model` 和 `PatchToolCallsMiddleware.before_agent`，并且 `tools` 节点里还自动包含了虚拟文件系统工具集和 `task` 委派工具；
- **方案 B（`create_agent` + 手装一个 `TodoListMiddleware`）** 只有 `TodoListMiddleware.after_model`，没有 `PatchToolCallsMiddleware`，也没有虚拟文件系统和 `task`。

由此可以把 `deepagents` 的等式写完整：

```
create_deep_agent ≈ create_agent
                   + TodoListMiddleware       (规划：write_todos)
                   + FilesystemMiddleware     (虚拟文件系统：write_file/read_file/ls)
                   + SubAgentMiddleware       (委派：task)
                   + PatchToolCallsMiddleware (工具调用标准化)
```

这几个 middleware 全都是 langchain 生态里的独立模块，`deepagents` 的价值就是把它们「预装好了」——省去了手动挑选、组装、调顺序的功夫。代价是依赖包略大一些。所以「开箱即用」并不神秘，它就是案例 3 那套手装动作的成品打包。至于什么时候该用成品、什么时候该自己手装，是第八章三层取舍要回答的问题。

---

### 四、规划机制：write_todos 让长程任务不遗漏

#### 1、给长程任务挂上待办清单

规划机制要解决的是「越走越忘」。它的做法是：拿到一个多步骤任务后，Agent 先调用 `write_todos` 写一份待办清单，把任务拆成若干条 todo（待办项），每完成一批就更新清单状态，直到全部完成。这份清单存在 Agent 的状态（state）里，Agent 每一步都能看到「还剩哪些没做」，于是不会遗漏、也不会重复。

用一个真实的长程任务来触发它——一个四维度的新能源汽车电池市场调研：

```python
task = "请帮我调研新能源汽车电池市场 4 个维度：主要厂商及市占率、核心技术路线、市场规模预测、主要风险因素，最后整合成简报。"

# 流式运行，每次 chunk 里读 state.todos，观察待办清单的变化
for chunk in agent.stream({"messages": [{"role": "user", "content": task}]},
                          config={"recursion_limit": 100}):
    if "todos" in chunk:
        print(chunk["todos"])   # 打印当前待办清单
```

> ⚠️ 工程约束（实测踩坑）：`recursion_limit`（计算图最大迭代步数）的默认值（LangGraph 默认 25）对长程任务**远远不够**。本案例这个 7 步调研任务实际触发了约 50 多次计算图迭代，用默认值会直接抛 `GraphRecursionError`。必须显式把 `config={"recursion_limit": 100}` 设大，长程任务一般建议设到 50–100。这是 deep agent 长程任务必踩的坑，第一次跑就会遇到。

```bash
.venv/bin/python step3_write_todos.py
```

![Step 3 write_todos 规划机制终端输出：首次调用 write_todos 创建 6 条 todos（制定调研计划 in_progress + 搜索厂商市占率/技术路线对比/市场规模预测/风险因素/整合简报 5 条 pending），state.todos 写入 state；逐步执行中清单扩展并全部变为 completed（制定调研计划、搜索主要厂商及市占率、获取宁德时代/比亚迪数据、搜索技术路线对比、搜索市场规模预测、搜索主要风险因素、整合信息并撰写简报，共 7 条）；write_todos 调用次数 6，todos_used: true，每次调用更新状态 pending → in_progress → completed](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step3-write-todos.png)

终端输出把规划机制的运转过程完整摊开了：

- **第一次调用就把任务拆成了清单**：Agent 拿到任务后立即调用 `write_todos`，生成 6 条 todo（一条「制定调研计划」加上五个具体调研步骤）。生成时第一条设为 `in_progress`（进行中）、其余 5 条设为 `pending`（待办）。执行过程中清单还会动态细化——本案例后续把「搜索厂商」拆出了「获取宁德时代/比亚迪数据」一条，最终清单扩展到 7 条并全部完成。
- **`write_todos` 被调用了 6 次**：一次初始规划，加上五次状态更新。Agent 每完成一批任务就回头更新清单，把做完的条目标成 `completed`（已完成）。
- **每条 todo 走的是三态机**：`pending`（待办）→ `in_progress`（进行中）→ `completed`（已完成）。这个状态流转完全由 Agent 自主维护，不需要开发者写任何调度代码。

最终所有 todo 都变成 `completed`，日志末尾的 `todos_used: true` 确认了规划机制确实被触发。这里有两个实现细节值得记下：`write_todos` 是被**自动注入**的（来自 `TodoListMiddleware`，无需手动配置）；`state.todos` 是 `deepagents` 的状态对象 `DeepAgentState` 的内置字段，流式运行时直接从 `chunk["todos"]` 里就能读到，不需要额外挂钩子。

---

### 五、委派机制：定义子 Agent 并用 task 委派

#### 1、定义 SubAgent 并交给主 Agent 委派

委派机制要解决的是「上下文越堆越满」。思路是分工：主 Agent 负责统筹，把具体的、耗费上下文的子任务**委派**给独立的子 Agent（SubAgent）去做。子 Agent 有自己独立的上下文，干完活只把**最终结果**交回主 Agent，中间过程不污染主 Agent 的上下文。

定义子 Agent 用的就是第二章核对过的 `SubAgent` 三字段。这里定义两个分析师子 Agent——一个分析电池厂商、一个对比技术路线，然后通过 `create_deep_agent` 的 `subagents` 参数交给主 Agent：

```python
# SubAgent 是 TypedDict，用字典字面量定义即可
company_analyst = {
    "name": "company_analyst",                       # 名字，委派时用它指认
    "description": "专门分析电池厂商的市场地位",        # 描述，告诉主 Agent 它能干什么
    "system_prompt": "你是电池行业公司分析专家……",     # 系统提示词，决定它怎么干
}
tech_analyst = {
    "name": "tech_analyst",
    "description": "专门对比不同电池技术路线的性能参数",
    "system_prompt": "你是电池技术路线分析专家……",
}

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),
    tools=[search_market_info],
    system_prompt="你是市场研究总协调员，把专业子任务委派给对应的分析师。",
    subagents=[company_analyst, tech_analyst],       # 注册两个子 Agent
)
```

```bash
.venv/bin/python step4_task_delegate.py
```

![Step 4 SubAgent + task 委派机制终端输出：SubAgent 必填字段 name/description/system_prompt；定义子 Agent company_analyst 和 tech_analyst；主 agent 配置 subagents=[company_analyst, tech_analyst]，task 工具由 SubAgentMiddleware 自动注入；运行时 task 委派两次（subagent_type=company_analyst 分析宁德时代/比亚迪市场地位，subagent_type=tech_analyst 对比磷酸铁锂 vs 三元锂技术路线），task 调用次数 2，task_delegated: True；TaskToolSchema 字段 description（详细任务描述+预期输出格式）+ subagent_type（子 agent 类型，须匹配 subagents 列表中定义的 name）](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step4-task-delegate.png)

运行结果确认了委派机制的运作：

- **`task` 工具被调用了 2 次**：主 Agent 分别把「分析厂商市场地位」委派给了 `company_analyst`、把「对比技术路线」委派给了 `tech_analyst`。日志里 `task_delegated: True` 确认机制触发。
- **`task` 工具的参数是 `subagent_type`**：注意这个字段名不是直觉上的 `subagent_name`，而是 `subagent_type`，它的值必须匹配定义子 Agent 时的 `name` 字段。这来自 `task` 工具的参数定义 `TaskToolSchema`，它有两个字段——`description`（要委派的详细任务描述，含上下文与预期输出格式）和 `subagent_type`（委派给哪个子 Agent）。
- **委派描述携带完整上下文**：日志里 `task` 的 `description` 字段写满了具体任务（「请分析宁德时代（CATL）和比亚迪（BYD）在动力电池领域的市场地位……」），而不是甩一句模糊的指令让子 Agent 自己去猜。主 Agent 在委派时就把必要信息一次给足，子 Agent 不必回头找主 Agent 要。

还有一个体验上的细节：`task` 工具的描述会**动态注入**当前可用的子 Agent 列表——也就是说，主 Agent 在运行时就「知道」自己手底下有 `company_analyst` 和 `tech_analyst` 可以差遣，所以才会主动发起委派。

#### 2、量化委派的隔离效果：子 Agent 的上下文压缩

上面看到了委派的动作，但委派到底能不能真的「防止上下文膨胀」？这需要量化验证。设计一个 `data_processor` 子 Agent，让它处理一批较大的原始数据，再看主 Agent 实际收到的结果有多大：

```bash
.venv/bin/python ext3_subagent_isolation.py
```

![拓展实验 3 子 Agent context 隔离证明终端输出：task 结果（主 agent 收到的）长度 185 字符，内容为全球 AI 芯片市场规模 3500 亿美元等精炼摘要 3 句话；原始详细数据（子 agent 处理的）新能源 348 字符 + AI 芯片 337 字符 = 合计 685 字符；压缩比 3.7x；context 隔离验证通过——子 agent 处理的原始数据不会出现在主 agent context 中，主 agent 只收到 task 工具返回的精炼摘要](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--extension-3-subagent-isolation.png)

数据说话：

- 子 Agent 处理的**原始数据是 685 字符**（新能源 348 字符 + AI 芯片 337 字符）；
- 主 Agent 实际收到的 **`task` 结果只有 185 字符**——一段三句话的精炼摘要，含关键数字；
- 压缩比 **3.7 倍**。

更重要的是，那 685 字符的原始数据**根本不会出现在主 Agent 的消息历史里**。`task` 工具的返回值就是子 Agent 的最终回复，而不是子 Agent 的整个工作过程。这才是委派机制防止上下文膨胀的根本：把脏活累活（处理大量原始数据）隔离在子 Agent 内部，主 Agent 只接收提炼后的精华。换算到真实场景——一篇上万字的原始文档丢给子 Agent，它可能只返回两百字的摘要，长程任务因此才不会撑爆上下文窗口。这里也透出一条经验：压缩比越高，子 Agent 的「信息提炼能力」越关键，而提炼能力直接由它的 `system_prompt` 质量决定。

---

### 六、虚拟文件系统：用 write_file / read_file / ls 做上下文工程

#### 1、把中间结果写进虚拟文件而非堆在对话里

第三道墙是「中间结果无处暂存」。`deepagents` 的解法是给 Agent 配一套**虚拟文件系统**——`write_file`（写文件）、`read_file`（读文件）、`ls`（列目录），还有 `edit_file` / `glob` / `grep` 等更细的操作。Agent 可以把每一步的中间结果写成文件存起来，需要时再读回来，而不是让所有数据一直挂在对话上下文里。这是「上下文工程」最直接的一种手段：主动决定什么留在上下文、什么挪到外部暂存。

用一个三话题的调研任务驱动 Agent 自主使用这套文件系统：

```python
task = "请分别调研新能源汽车市场、动力电池竞争格局、电池技术路线趋势三个话题，每个话题的调研结果分别写入一个 markdown 文件，最后列出目录并读取其中一个文件验证。"
```

```bash
.venv/bin/python step5_virtual_fs.py
```

![Step 5 虚拟文件系统终端输出：FilesystemMiddleware 自动注入 write_file/read_file/ls/edit_file/glob/grep；运行时 write_file 三次（ev_新能源汽车市场.md、ev_动力电池竞争格局.md、ev_技术路线趋势.md，各含核心数据预览），ls 列出 / 目录，read_file 读取 ev_新能源汽车市场.md；操作统计 write_file 3 次 + read_file 1 次 + ls 1 次 = file_ops 5；机制验证 write_file=True/read_file=True/ls=True，三大机制全部触发：规划 write_todos + 委派 task + 虚拟FS](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step5-virtual-fs.png)

运行结果显示 Agent 自主完成了一整套文件操作：`write_file` 调用 3 次（三个话题各写一个 markdown 文件）、`ls` 调用 1 次（列出目录确认文件都在）、`read_file` 调用 1 次（读回一个文件验证内容），合计 `file_ops: 5`。整个过程 Agent 自己决定何时写、写什么、何时读——开发者只给了任务，没有手写任何文件调度逻辑。

关于虚拟文件系统，有一个工程选型要点：默认的 `StateBackend` 后端下，虚拟文件随线程（thread）消亡而消失——也就是这次运行写的文件，换个会话就没了，适合「单次任务内暂存」。如果需要跨会话持久保存，要换成 `StoreBackend` 后端。本案例的中间结果暂存用默认的 `StateBackend` 即可。

#### 2、把三大机制的内部状态一次看清

到这里，三大机制都各自跑过了。但它们在一次运行里是怎么交织变化的，还值得用「内部状态追踪」看一遍。通过流式调用同时盯住三处——`chunk["todos"]`（规划清单的实时状态）、`task` 委派记录、虚拟文件操作记录：

```bash
.venv/bin/python ext1_three_mechanisms_trace.py
```

![拓展实验 1 三机制内部状态追踪终端输出：机制① state.todos 三次快照（#1 初始规划全 pending → #3 中间执行部分 completed、task 委派 in_progress → #5 全部 completed）；机制② task 委派历史 1 次，subagent_type=reporter，description 含完整上下文与文件路径 /market_report.md；机制③ 虚拟FS 操作历史 write_file→/data_ev.txt、write_file→/data_battery.txt、ls→/、read_file→/market_report.md；总结 state.todos 变化 5 次、task 委派 1 次、虚拟FS 操作 4 次，chunk['todos'] 实时追踪 + tool_calls 监控 = 三大机制内部状态直接可见](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--extension-1-three-mechanisms-trace.png)

这次追踪补上了三个理解三大机制的关键观察：

1. **`state.todos` 是实时可追踪的**：通过 `chunk["todos"]` 就能拿到每次 `write_todos` 调用后的完整清单快照——无需额外挂钩子。追踪里清晰看到 todo 列表从「全 pending」（#1 初始规划）到「部分 completed」（#3 中间执行）再到「全 completed」（#5 全部完成）的三个阶段，状态更新粒度很细，每次 `write_todos` 调用后立刻反映。
2. **三态机不是简单的标记**：`pending` / `in_progress` / `completed` 是 Agent 自主管理的工作状态，而不是开发者打的标签。
3. **委派时上下文一次给足**：这次 `task` 委派给 `reporter` 子 Agent 时，`description` 字段里带上了完整上下文，包括要读的文件路径 `/market_report.md`——子 Agent 拿到就能干，无需回调主 Agent。这与第五章「委派描述携带完整上下文」的观察相互印证。

---

### 七、三机制综合验证：一次运行看齐全套能力

前面分章拆看了三大机制，本章用一次综合运行把它们摆在一起，确认在同一个任务里三者协同工作，并把每个机制的来源和效果显式打出来：

```bash
.venv/bin/python step6_three_mechanisms.py
```

![Step 6 deepagents 三大机制综合验证终端输出：一行代码 create_deep_agent 自动挂载三大机制——机制① write_todos（规划防遗忘，来源 TodoListMiddleware/langchain 内置，效果 state.todos 维护任务清单）、机制② task（子 Agent 委派，来源 SubAgentMiddleware/deepagents，效果处理专项任务、主 agent 只收精炼结果）、机制③ 虚拟文件系统（context engineering，来源 FilesystemMiddleware/deepagents，效果中间数据写文件 offload 避免 context 窗口堆积）；综合运行序列含 write_todos 创建 5 条、write_file、read_file、ls、task 委派 summarizer；统计 write_todos 4 次、task 1 次、虚拟FS write_file=2/read_file=2/ls=1，state.todos 5 条全部 completed，todos_used=True/task_delegated=True/file_ops=5，验证通过](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step6-three-mechanisms.png)

综合运行的结果干净利落：`write_todos` 调用 4 次（规划）、`task` 调用 1 次（委派一个 `summarizer` 子 Agent）、虚拟文件操作 5 次（`write_file` 2 次 + `read_file` 2 次 + `ls` 1 次），`state.todos` 里 5 条 todo 最终全部 `completed`。日志末尾三个标志位 `todos_used: True` + `task_delegated: True` + `file_ops: 5` 同时为真，意味着三大机制在一次运行里全部被真实触发。

这张截图同时把三大机制的「来源 + 效果」对照清楚地落了档，正好作为复述原理时的依据：

| 机制 | 工具 | 来源 middleware | 解决的问题 |
| --- | --- | --- | --- |
| 规划 | `write_todos` | `TodoListMiddleware`（langchain 内置） | 长链路防遗忘：用 `state.todos` 维护任务清单 |
| 委派 | `task` | `SubAgentMiddleware`（deepagents） | 防上下文膨胀：子 Agent 处理专项任务，主 Agent 只收精炼结果 |
| 虚拟文件系统 | `write_file` / `read_file` / `ls` | `FilesystemMiddleware`（deepagents） | 上下文工程：中间数据写文件 offload（卸载），避免上下文窗口堆积 |

---

### 八、换数据复用与三层取舍

#### 1、换成自己的长程任务：论文整理 + 自定义翻译子 Agent

三大机制的价值最终要落到「能不能换成我自己的任务」上。本节做一次彻底的换数据验证：把市场调研任务整个换成「整理多篇 AI 论文要点」，并定义一个全新的 `translator`（翻译）子 Agent，看三大机制是否原样复用。这一步也是本案例的验收点——学员能否定义自己的子 Agent 并让主 Agent 委派它。

```python
# 学员自定义子 Agent：只需填三个字段
translator = {
    "name": "translator",
    "description": "把英文论文摘要翻译成中文，并用无序列表提炼关键术语",
    "system_prompt": "你是一名 AI 论文翻译专家……",
}

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),
    tools=[fetch_paper],                 # 换成论文检索工具
    system_prompt="你是论文整理助手……",   # 换成论文整理的提示词
    subagents=[translator],              # 换成自定义的翻译子 Agent
)
```

```bash
.venv/bin/python step7_reuse_custom.py
```

![Step 7 换数据复用验证终端输出：定义自定义子 Agent translator（name/description/system_prompt 三必填字段，把英文论文摘要翻译成中文并提炼关键术语）；换数据后任务为多篇论文整理；运行触发 write_todos 规划启动、write_file 三次（attention2017.txt、bert2019.txt、gpt3_2020.txt）、todos 状态更新、task 委派 translator 子 Agent、write_todos 最终标记；统计 write_todos 3 次 + task 1 次（委派 translator 翻译）+ write_file 3 次，state.todos 5 条全部 completed；学员验收点确认——自定义子 Agent translator 三必填字段、主 agent 委派 translator 完成翻译、换数据三机制全部复用；复用结论 三大机制与任务内容解耦，换任务是长程任务可直接套用](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--step7-reuse-custom.png)

换数据后的结果说明三大机制与任务内容是**完全解耦**的：换成论文整理任务后，规划（`write_todos` 3 次）、委派（`task` 1 次，委派给自定义的 `translator`）、虚拟文件系统（`write_file` 3 次，分别存了 `attention2017.txt`、`bert2019.txt`、`gpt3_2020.txt`）全部照常运转，`state.todos` 5 条最终全部 `completed`。学员验收点逐项确认：自定义子 Agent 只填了 `name` / `description` / `system_prompt` 三个字段就生效，主 Agent 成功委派它完成了翻译。

由此得到换数据的复用结论：**要换的只有三样——`tools`（换成你的工具）、`subagents`（换成你的子 Agent）、`system_prompt`（换成你的任务描述）；三大机制本身一行不用改**。任何长程任务——论文整理、分章节写作、多源资料汇总——都可以套用这套规划 + 委派 + 虚拟文件系统的模式。

#### 2、三层取舍：什么时候用 deepagents、什么时候不用

`deepagents` 好用，但不是所有任务都该用它。从案例 1 到本案例，构建 Agent 实际上有三层抽象可选，自上而下分别是：开箱即用的 `create_deep_agent`、手动挑装 middleware 的 `create_agent`、以及完全自定义计算图的裸 LangGraph。用六个典型任务逐一分析该选哪层，能把这个取舍落成可操作的决策框架：

```bash
.venv/bin/python ext4_layer_decision_map.py
```

![拓展实验 4 三层取舍决策树终端输出：决策规则——长程多步骤（≥3步）+ 规划/委派/文件暂存 → create_deep_agent（三机制全自动）；需要完全自定义 graph 拓扑 → 裸 LangGraph（完全控制）；简单一次性工具调用 → create_agent（最轻量）；中等任务 → create_agent + 手选 middleware。六个任务案例：快速查天气→create_agent（无 middleware）；代码审查助手（3-5步）→create_deep_agent；多源市场调研（本案例）→create_deep_agent；限流+日志代理→create_agent+手选 middleware；论文写作助手→create_deep_agent；A/B 测试条件分支→裸 LangGraph。三层取舍速查表 + 判断口诀](https://ml2022.oss-cn-hangzhou.aliyuncs.com/img/langchain-course/case-8--shot--extension-4-layer-decision-map.png)

把六个案例的判断整理成一张速查表：

| 任务 | 推荐层 | 原因 |
| --- | --- | --- |
| 快速查天气 | `create_agent`（不挂 middleware） | 简单一次性工具调用，不需要额外机制 |
| 代码审查助手 | `create_deep_agent` | 3–5 步，需要规划 + 文件暂存 |
| 多源市场调研（本案例） | `create_deep_agent` | 7 步，需要三机制全套 |
| 限流 + 日志代理 | `create_agent` + 手选 middleware | 需要定制钩子，但不需要全套三机制 |
| 论文写作助手 | `create_deep_agent` | 8 步，规划 + 子 Agent + 文件 |
| A/B 测试条件分支 | 裸 LangGraph | 特殊计算图拓扑，需要条件跳转 |

决策的关键维度有两个：**步骤数**（是否 ≥ 3 步）和**是否需要规划 / 委派 / 文件暂存**。可以记一句口诀：**任务超 3 步 + 怕遗忘 + 怕上下文爆 → 用 `create_deep_agent`**；只调一两个工具的简单任务用 `create_agent` 最轻；需要条件分支、并行、循环等特殊计算图拓扑时，才下沉到裸 LangGraph 完全手控。而像限流、日志这种「只要部分中间件、不要全套」的中等任务，则用案例 3 那套 `create_agent` + 手选 middleware 最合适。值得一提的是，`create_deep_agent` 的适用范围比「深度调研」这个名字暗示的要宽——代码审查、论文写作、多源汇总，凡是需要三机制的任务都能套用。

---

### 九、自学迁移指南：把示例任务换成你自己的长程任务

本案例用「市场调研」「论文整理」两个示例跑通了 `deepagents` 三大机制，但这套机制与具体任务内容无关。要把它迁移到自己的长程任务（资料汇总、分章节写作、多步骤数据处理等），关键在于分清「哪些要换、哪些不动」。

#### 1、可替换的部分（换成你的任务）

需要改写的只有三个入参，三大机制的调用方式一律不动：

- **`tools`**：换成你的真实工具。本案例用的是 mock 检索工具 `search_market_info` / `fetch_paper`，真实业务里换成你的搜索 API、数据库查询、文件读取等工具即可；
- **`subagents`**：换成你的子 Agent。每个子 Agent 就是一个填好 `name` / `description` / `system_prompt` 三个字段的字典，按你的专项任务分工定义（如「翻译子 Agent」「数据清洗子 Agent」「校对子 Agent」）；
- **`system_prompt`**：换成你的任务描述，告诉主 Agent 它的统筹职责是什么、有哪些子 Agent 可以委派。

下面是「市场调研子 Agent → 你的翻译子 Agent」的最小改写骨架，对照着改即可：

```python
# 改之前（本案例的市场分析子 Agent）
company_analyst = {
    "name": "company_analyst",
    "description": "专门分析电池厂商的市场地位",
    "system_prompt": "你是电池行业公司分析专家……",
}

# 改之后（换成你的业务：英文论文翻译子 Agent）
translator = {
    "name": "translator",                                  # 换成你的子 Agent 名字
    "description": "把英文论文摘要翻译成中文并提炼关键术语",   # 换成它能干什么
    "system_prompt": "你是一名 AI 论文翻译专家……",          # 换成它怎么干
}

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),
    tools=[fetch_paper],            # 换成你的工具
    system_prompt="你是论文整理助手……",
    subagents=[translator],         # 换成你的子 Agent
)
```

可以看到，三个入参都换成了业务相关内容，但「`SubAgent` 填三字段 + 传入 `subagents` 参数即激活」这套规范一字未变。

#### 2、保持不变的部分（机制骨架）

下面这些不需要改动，它们是迁移后依然成立的骨架：

- **入口与返回**：`create_deep_agent(model, tools, system_prompt, subagents)` 的调用方式不变，返回的 `CompiledStateGraph` 用 `invoke` / `stream` 调用，与案例 1 一致；
- **三大机制自动挂载**：`write_todos`（规划）、`task`（委派）、`write_file` / `read_file` / `ls`（虚拟文件系统）都是 `create_deep_agent` 自动注入的，无需手动配置；
- **状态读取入口**：规划清单从 `state.todos`（流式下 `chunk["todos"]`）读取，三态机 `pending` / `in_progress` / `completed` 由 Agent 自主维护；
- **委派字段约定**：子 Agent 三必填字段 `name` / `description` / `system_prompt`，`task` 委派时用 `subagent_type` 指认（值匹配 `name`）。

#### 3、迁移后如何验证跑通

换完任务后，按本案例的方式自检，确认三大机制都被真实触发：

1. **规划验证**：跑一个 ≥ 3 步的任务，确认 Agent 调用了 `write_todos`、`state.todos` 里的清单从 `pending` 逐步走到 `completed`（日志里 `todos_used: true`）；
2. **委派验证**：确认 `task` 工具至少被调用一次、`subagent_type` 指向了你定义的子 Agent（日志里 `task_delegated: True`）；
3. **虚拟文件系统验证**：确认 Agent 用 `write_file` 写了中间结果、用 `ls` / `read_file` 能取回（日志里 `file_ops ≥ 1`）；
4. **隔离效果验证**（可选）：对照本案例拓展实验，比较子 Agent 处理的原始数据长度与主 Agent 收到的 `task` 结果长度，确认主 Agent 上下文里没有堆积原始数据。

三项核心机制都触发，就说明你的长程任务在 `deepagents` 上完整跑通了。

#### 4、迁移前置假设清单

迁移顺利的前提是具备以下条件，动手前先核对：

- **已掌握案例 1 的 `create_agent` 与案例 3 的 middleware**：`deepagents` 是「`create_agent` + 预装 middleware」，工具调用循环、middleware 钩子这些概念若还不熟，建议先回到案例 1、案例 3；理解了 middleware，才能真正看懂第三章 graph nodes 揭示的「三大机制 = 几个预装 middleware」；
- **理解「上下文膨胀」是什么**：长任务塞太多中间信息、模型记不过来——委派与虚拟文件系统两大机制都是冲着这个问题去的，不理解问题就体会不到机制的价值；
- **接受 pre-1.0 接口可能变动**：本手册基于 `deepagents` v0.6.7，pre-1.0 阶段工具名、参数名（如 `subagent_type`）后续可能调整。迁移时若遇到导入错误或参数报错，先对照当时的官方 reference（[reference.langchain.com/python/deepagents](https://reference.langchain.com/python/deepagents)）核对一遍，重点放在不会过期的设计理念上；
- **记得设大 `recursion_limit`**：长程任务的迭代步数远超默认值，务必显式设置 `config={"recursion_limit": 100}`（一般 50–100），否则长任务会直接抛 `GraphRecursionError`；
- **`create_deep_agent` 必须显式传模型**：`model=None` 默认值自 v0.5.3 起已弃用，不能依赖默认值；
- **基本运行条件**：本案例用 `ChatDeepSeek` 作模型，需要配好可用的模型 API Key（环境变量或显式传入）与可访问模型服务的网络环境——这是所有 Agent 案例的共同前提，迁移时按你选用的模型补齐对应凭证即可。

把这几点核对清楚，本案例的示例任务就能稳妥地迁移成你自己业务的长程智能体。

