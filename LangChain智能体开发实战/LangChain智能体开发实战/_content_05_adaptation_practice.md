# D 部分 · 适配指南（DeepSeek + CCR 网关）

教程全程在 macOS 上跑，模型走 DeepSeek 官方端点（`DEEPSEEK_API_KEY` + `deepseek:deepseek-chat`）。本部分把教程的接入路径**落到你现有的 CCR（Claude Code Router）网关环境**，让你在 Windows 本机、已经有了 CCR 网关 + DeepSeek 视觉模型的基础上，也能照教程做全部实验。核心差异只有「模型端点换成 CCR」这一处，其余代码、概念、章节目录全部复用。

## D.1 你的基线环境（已探明）

- 网关：CCR（Claude Code Router），核心网关地址 `http://127.0.0.1:3456`。
- 模型：DeepSeek 视觉模型 `DeepSeek/deepseek-v4-flash-vision-exp`（经 CCR 网关转发，模型解析规则见 `~/.claude/settings.json`）。
- `~/.claude/settings.json` 关键配置：
  ```json
  {
    "apiKeyHelper": "...\\ccr-claude-code-api-key-default-claude-code.cmd",
    "env": {
      "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456",
      "ANTHROPIC_API_BASE_URL": "http://127.0.0.1:3456",
      "CLAUDE_AGENT_API_BASE_URL": "http://127.0.0.1:3456",
      "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
    },
    "model": "DeepSeek/deepseek-v4-flash-vision-exp"
  }
  ```
- 记忆提示：CCR 网关重启后**核心 auth token 每次随机生成**（`service.json` 的 url 参数 `ccr_web_token`），旧 token 会导致 `502 Core gateway auth token is not initialized`。`ccr` 没有 `restart` 子命令，用 `ccr stop` 再 `ccr start --gateway --no-open`。

## D.2 教程「模型接入」替换为「CCR 网关」

教程第 1 章的模型接入段落，原样对应替换如下。**注意：教程全部用 `deepseek:deepseek-chat`，你要做的是保留这个「工具调用/并行调用都必须支持的对话模型」的语义，只是把「如何接入这个能走工具调用的 DeepSeek 对话模型」这条路换掉。**

### 替换点 1：凭证来源
教程用 `export DEEPSEEK_API_KEY=...`。你在 CCR 网关下**不需要**单独设 DEEPSEEK_API_KEY——API Key 由 CCR 的 `apiKeyHelper` 脚本统一注入（`ccr-claude-code-api-key-default-claude-code.cmd`）。`~/.claude/settings.json` 里已经配好了 `apiKeyHelper`，LangChain 侧无需再管凭证。

### 替换点 2：base_url 指向 CCR 网关
教程侧创建一个兼容 OpenAI 的客户端指向 CCR 网关即可。因为 CCR 复用了 Claude Code 的 `ANTHROPIC_*` 环境变量，LangChain 侧用 openai-compatible 访问更直接：

```python
# 教程原写法（macOS, DeepSeek 官方端点）
agent = create_agent(model="deepseek:deepseek-chat", tools=[...])

# 适配 CCR 网关的等价写法（Windows, 经 CCR 转发）
from langchain_openai import ChatOpenAI  # langchain-deepseek 已连带装 langchain-openai
import os

llm = ChatOpenAI(
    base_url="http://127.0.0.1:3456",      # CCR 核心网关
    api_key=os.environ.get("ANTHROPIC_API_KEY"),  # 由 apiKeyHelper 注入
    model="DeepSeek/deepseek-v4-flash-vision-exp",
)
# 用 ChatOpenAI 实例替代字符串模型名
agent = create_agent(model=llm, tools=[...])
```

### 替换点 3：`deepseek-reasoner` 的限制依然成立
教程指出 deepseek-reasoner 不支持工具调用与结构化输出。在 CCR 网关下同理——**必须选一个支持工具调用（tool calling）与并行调用（parallel function calling）的对话模型**，不能用纯推理模型。视觉模型是否能走工具调用取决于 CCR 转发的端点，稳妥起见用单独配置好的对话模型跑工具类实验。

### 替换点 4：结构化输出的 ProviderStrategy 兼容性
教程第 3 章明确：DeepSeek 官方端点下 ProviderStrategy 报 400（`This response_format type is unavailable now`），必须退回 ToolStrategy。CCR 网关作为代理，**原生结构化输出端点是否可用取决于 CCR 转发到的上游**，若也报 400，同样退回 ToolStrategy（`ToolStrategy(Schema)`）。这是兼容性边界，不是 bug。

## D.3 跨平台适配

| 项 | macOS（教程） | Windows（你） |
|----|---------------|---------------|
| venv 激活 | `source .venv/bin/activate` | `.venv\Scripts\activate` |
| 系统 Python | 常为 3.9 不达标，用 Homebrew python3.13 | 用 `py -3.13` 或明确指定解释器 |
| langgraph 版本获取 | `importlib.metadata.version("langgraph")` | 同上，**不要用 `langgraph.__version__`** |
| 模型接入 | `deepseek:deepseek-chat` 官方端点 | ChatOpenAI(base_url=CCR) + apiKeyHelper 注入 |
| 凭证 | `export DEEPSEEK_API_KEY=...` | 由 apiKeyHelper 统一注入，无需单独设 |

## D.4 适配后九个章节的改动量

- **第 1 章**：环境搭建步骤完全一致；仅「配置 DeepSeek API Key」一步改为「确认 CCR 网关在跑 + apiKeyHelper 已配置」。
- **第 2~9 章**：**代码零改动**——所有 create_agent、工具定义、middleware、checkpointer、response_format、Langfuse callback、RAG、DeepAgents 用法与教程完全一致，唯一变化是第 2~9 章创建 agent 时把字符串模型名换成 CCR 的 ChatOpenAI 实例（见 D.2 替换点 2）。
- **第 7 章 Langfuse**：callback 接入与 LANGFUSE_* 环境变量配置不变；只需确认 CCR 网关转发的请求能被 Langfuse 识别到 provider/model 名称以便 token 计数。
- **第 9 章 DeepAgents**：Python ≥3.11 且 <4.0 的版本要求不变；subagent 与主 agent 共享 checkpointer/thread 体系，务必带 thread_id。

---

# E 部分 · 可动手练习清单

围绕每个核心能力设计一个可独立动手的小实验，全部基于 CCR 网关 + ChatOpenAI(base_url=...)。每个实验给出「目标 / 步骤 / 验证点 / 对应章节」。

## 练习 1 工具调用循环（第 1、2 章）
- **目标**：实现一个带查询工具的 Agent，验证一次完整工具调用闭环。
- **步骤**：定义 `get_weather(city: str) -> str`（带 docstring）→ create_agent(model=llm, tools=[get_weather]) → invoke 问「旧金山的天气」→ 遍历 result["messages"]。
- **验证**：看到四条消息流（human → ai(tool_calls) → tool → ai 最终回答）；若漏写 docstring 应报 ValueError。
- **进阶**：加第二个独立工具，验证并行 tool_calls 挂在同一条 AIMessage。

## 练习 2 结构化输出（第 3 章）
- **目标**：让 Agent 返回校验过的对象。
- **步骤**：定义 `class ReviewAnalysis(BaseModel)` 含 sentiment/category/urgency → response_format=ToolStrategy(ReviewAnalysis) → invoke 一条评论文本 → 读 result["structured_response"]。
- **验证**：.sentiment/.category/.urgency 可直接取值；换个 schema 类（OrderInfo）代码零改动即换业务。
- **进阶**：用 Counter/sum 批量统计「情感分布」「平均紧急度」。

## 练习 3 中间件与执行顺序（第 4 章）
- **目标**：挂多个 middleware 观察执行顺序铁律。
- **步骤**：写 `class OrderM(AgentMiddleware)`（before_model 打印、after_model 打印）→ middleware=[OrderM("M1"), OrderM("M2"), OrderM("M3")] → invoke 一次含工具调用的问题。
- **验证**：before 正序 M1→M2→M3，after 逆序 M3→M2→M1；含工具调用的问题触发两轮 before_model/after_model。
- **进阶**：加 ModelCallLimitMiddleware(run_limit=2) 限流；用 PIIMiddleware 脱敏中文手机号（detector=r"1[3-9]\d{9}"）。

## 练习 4 持久化记忆与隔离（第 5 章）
- **目标**：验证同 thread_id 记住前文、不同 thread_id 隔离。
- **步骤**：create_agent(..., checkpointer=InMemorySaver()) → config_u1 问「我的订单号是 A1001 请记住」→ 同 config_u1 问「我刚才说的订单号是什么」→ 换 config_u2 再问。
- **验证**：u1 能答出 A1001，u2 答不出；get_state 看 next=() 与消息数。
- **进阶**：换 SqliteSaver.from_conn_string，跨进程重开验证记忆仍在。

## 练习 5 HITL 人机审批（第 6 章）
- **目标**：给危险动作加人工闸门。
- **步骤**：在危险动作前 interrupt(...) → 调 agent 触发中断 → get_state 看 tasks/details → Command(resume="approve") 恢复。或直接用 HumanInTheLoopMiddleware。
- **验证**：中断点停下、resume 后继续、不 resume 则一直停。

## 练习 6 可观测性（第 7 章）
- **目标**：接入 Langfuse 看 trace。
- **步骤**：配 LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST → CallbackHandler 传入 callbacks → invoke 带 config={"metadata": {"user_id": "u1"}} → 打开 Langfuse UI 看 trace。
- **验证**：UI 里看到完整调用链与 token 用量；忘配 SECRET_KEY 则追踪不上。

## 练习 7 Agentic RAG（第 8 章）
- **目标**：让 Agent 决定何时检索。
- **步骤**：定义 knowledge_retrieval 工具（向量库）→ Grade(BaseModel) 作 grader → create_agent(tools=[knowledge_retrieval]) → 分别问「需要检索的问题」和「常识问题」。
- **验证**：常识问题不触发检索、需资料的问题走 query→retrieve→grade→生成。

## 练习 8 长程任务（第 9 章）
- **目标**：用 deepagents 跑一个多步任务。
- **步骤**：pip install deepagents → deepagents harness 包装 create_agent → 给一个 ≥10 步任务 → 观察 todo 规划与子代理委派。
- **验证**：Agent 迭代更新 todo、独立子任务被下放隔离。
- **进阶**：用虚拟文件系统承载中间产物，观察上下文是否被控制。

> 练习全部做完即覆盖九章核心能力。每个练习都以 CCR 网关 + ChatOpenAI 打底，与教程主题一一对应，可当作自学检查清单。
