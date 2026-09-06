---
concept: deepseek-provider-integration
one_liner: 用「提供方:模型名」字符串接入模型，凭证走环境变量；能驱动智能体的前提是所选型号支持工具调用
stage_span: [stage-1, stage-2]
prerequisites: [langchain-package-stack]
related: [create-agent-entry, structured-output-strategy-compat]
applications: [tool-calling-loop, structured-output-strategy-compat, agentic-rag-loop]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#3、配置 DeepSeek API Key
  - experiments/langchain/stage-1-bootstrap/handbook.md#3、模型选型说明
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、确认运行环境
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、三种写法对比与 DeepSeek 实测
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、用 create_deep_agent 一行搭出长程 Agent
---

## 是什么

提供方（provider）集成包负责把某一家大模型服务商接进 LangChain。接入后有两种写法：一种是把模型写成 `提供方:模型名` 的字符串（如 `"deepseek:deepseek-chat"`），由集成包解析；另一种是直接实例化聊天模型类（如 `ChatDeepSeek(model="deepseek-chat")`），在需要显式传模型对象的入口使用。

选型号时有一条硬约束：智能体的本质是模型在循环中调用工具，因此**所选型号必须支持工具调用（tool calling）**。同一家服务商的不同型号在这一点上可能完全不同，选错型号时循环根本走不通——模型不会发出 `tool_calls`，也就没有工具执行与结果回填。

## 怎么用

凭证通过环境变量注入，全程不在终端回显明文：

```bash
# 从凭证文件注入环境变量(不回显明文)
export DEEPSEEK_API_KEY=$(python -c "import yaml;print(yaml.safe_load(open('/path/to/credentials.yaml'))['api_keys']['deepseek']['key'])")
# 验证已注入(只显示脱敏前缀与长度)
echo "DEEPSEEK_API_KEY = ${DEEPSEEK_API_KEY:0:3}***(长度 ${#DEEPSEEK_API_KEY},已脱敏)"
```

字符串写法（组装智能体时最常用）：

```python
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)
```

模型对象写法（长程脚手架入口要求显式传模型时用）：

```python
from langchain_deepseek import ChatDeepSeek
model = ChatDeepSeek(model="deepseek-chat")
```

## 关键细节与参数

- 凭证读取的环境变量名固定为 `DEEPSEEK_API_KEY`，注入成功后终端只显示脱敏前缀与长度（实测 `sk-***`、长度 35）。
- 型号能力对照：

| 维度 | deepseek-chat | deepseek-reasoner |
| --- | --- | --- |
| 工具调用 | 支持 | 不支持 |
| 结构化输出 | 支持 | 不支持 |

  型号名与型号能力随服务商演进（推理型号是否支持工具调用、型号名是否更替都可能变化），接入前以服务商当时的文档为准。不变的是判据本身：**先确认所选型号支持工具调用，再拿它驱动循环**。
- `deepseek-chat` 支持并行工具调用：模型可在同一条消息里同时发出多个互不依赖的工具请求。
- 该提供方**没有原生结构化输出 API 端点**，结构化输出只能走工具调用兜底路线，细节见 structured-output-strategy-compat。
- 使用前提是已装对应集成包并已设好环境变量，二者缺一都会在组装或调用阶段失败。

## 常见陷阱

- **选了不支持工具调用的推理型号**：智能体不会发出 `tool_calls`，工具调用循环直接走不通，表现为"模型自己编了个答案"。换其他服务商时同样要先确认该型号支持工具调用。
- **把 Key 写进代码或截图**：注入与验证要分两步做，注入步不留痕、验证步只打印前 3 个字符加长度，从源头杜绝泄漏。
- **以为换服务商要重写业务代码**：模型串是可替换的参数，工具定义、消息流读取方式、智能体组装结构都不随服务商变化；真正要重新核对的是该服务商的能力边界（工具调用、结构化输出策略）。
