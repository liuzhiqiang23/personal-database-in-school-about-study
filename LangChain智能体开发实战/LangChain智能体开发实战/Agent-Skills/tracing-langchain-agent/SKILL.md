---
name: tracing-langchain-agent
description: 给已有的 LangChain / LangGraph Agent 挂上追踪回调，把一次请求背后的模型与工具调用链完整上报，并在面板上逐节点读出输入、输出、消耗与错误。Use when 需要看清 Agent 内部到底调了什么、定位某次工具调用为什么失败、评估一次请求的 token 与延迟、或排查「追踪没上报到后端」「连接校验超时」「导入 CallbackHandler 报错」这类接入故障时。涵盖 SDK 安装与导入路径、四个环境变量、回调挂载、调用树三类节点解读、失败链路定位、自托管与云服务两条路径选型；不含追踪后端的部署（见 deploying-langfuse-selfhost）。
allowed-tools: Bash(python:*), Bash(pip:*)
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、安装 langfuse 并核验接入入口
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、配置凭证与连接验证
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、接入只改两行：CallbackHandler + callbacks
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、trace 树的整体结构
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、三类节点：CHAIN / GENERATION / TOOL
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#六、可观测的反面价值：用 trace 定位一次工具失败
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#七、换 Agent 不换接入：验证可复用性
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#八、路径选型：Langfuse self-host 与 LangSmith SaaS 的取舍
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#3、本案例踩过的坑速查
---

## 能力目标

用一个回调对象把任意 LangChain Agent 的执行链路接进追踪平台：每次运行自动上报一棵可展开的调用树，树上每个模型调用与工具调用都带着自己的输入、输出、token 与延迟，无需在业务代码里加任何打印或埋点。业务侧零改动——同一段接入代码换到别的 Agent 上照样生效。

## 前置

- 已有一个能跑通的 Agent，且至少有一次工具调用——只调一次模型的问答会让调用树退化成单节点、看不出价值。
- 需要一个可达的追踪后端。自托管的起法见 deploying-langfuse-selfhost；也可走云服务路径（见最后一节选型）。
- 术语：一条完整调用链叫一条追踪记录，链上每个节点叫一个观测项。

## 实操流程

1. 装 SDK 并核对接入类的导入路径。这个路径随 SDK 大版本变过，v4 系列的正确写法是从 `langfuse.langchain` 导入：

   ```bash
   source .venv/bin/activate
   pip install langfuse
   python -c "from langfuse.langchain import CallbackHandler; print('OK')"
   ```

   无需任何额外 extra 参数。

2. 设四个环境变量并绕过代理。**四条缺一不可**，其中上报端点漏设会让追踪静默失败（本地产生了但导不出去），代理未绕过会让连接校验超时：

   ```bash
   source scripts/langfuse-env.sh http://localhost:3000
   ```

   等价的 Python 写法（代理绕过必须在客户端初始化**之前**设好）：

   ```python
   import os
   os.environ["NO_PROXY"] = "localhost,127.0.0.1"
   os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-course-demo-public"
   os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-course-demo-secret"
   os.environ["LANGFUSE_HOST"] = "http://localhost:3000"
   os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:3000/api/public/otel"
   ```

3. 先验连接再接 Agent，把接入故障与业务故障分开：

   ```python
   # step3_obs_config.py
   from langfuse.langchain import CallbackHandler
   handler = CallbackHandler()
   ```

   ```bash
   python step3_obs_config.py
   ```

   连接校验通过说明 Python 侧已能连上后端。

4. 接入本身只有两行——建一个回调处理器、在调用时挂到 `callbacks` 上：

   ```python
   # step4_obs_invoke.py
   from langfuse.langchain import CallbackHandler

   handler = CallbackHandler()
   agent.invoke(
       {"messages": [{"role": "user", "content": "我的订单 A1001 发货了吗？麻烦帮我查一下物流情况"}]},
       config={"callbacks": [handler]},
   )
   ```

   ```bash
   python step4_obs_invoke.py
   ```

   工具、模型、图结构一概不动。回调是框架的标准机制，所以能无侵入地嵌进任何执行流；换一个业务完全不同的 Agent，这两行一字不用改。

5. 打开追踪列表点进那条记录，按三类节点读调用树：

   | 节点类型 | 含义 | 携带的关键信息 |
   | --- | --- | --- |
   | CHAIN | 框架内部调度节点 | 只有延迟，无 token |
   | GENERATION | 一次模型调用 | 模型名、输入与输出 token、延迟 |
   | TOOL | 一次工具调用 | 工具名、输入参数、输出结果 |

   点中任一节点，右侧展开它的输入、输出、消耗。一次「查订单加查物流」的请求实测展开出 9 个嵌套观测项。工具节点完整保存了实际传进去的参数与返回值——不用在工具里加任何打印就能看到 Agent 到底传了什么。

6. 用它定位失败：让工具在非法输入下抛错、跑一次，回到列表点开那条失败记录，展开工具节点即可直接读到输入参数与抛出的错误信息。这是追踪相对翻日志加打印复现的核心价值。

7. 选路径。接入方式与合规约束是一组权衡：

   - **默认走自托管**：数据存在本地，金融、医疗、政务这类不能出境的场景只有这一条路；代价是要自己起并维护服务栈。
   - **逃生舱：云服务路径**：个人项目、学习、内部原型可用官方云服务，业务代码零改动、只设三个环境变量（追踪开关、API Key、项目名），连回调对象都不用建；代价是调用的输入输出会上报到境外服务器，且免费额度有上限。

## 校验回路

- 导入核验打印 OK，连接校验通过。
- 跑一次带工具调用的请求后，追踪列表出现新记录，且观测项数量明显大于 1（多步链路的标志）。
- 点开记录能在树里找到某个工具节点，并看到它的**输入参数与输出结果**——能定位到「某次工具调用传了什么、返回了什么」，就说明追踪真正接通了。
- 换一个工具集完全不同的 Agent、接入代码一字不改再跑一次，新记录照样完整上报。

## 常见陷阱

| 现象 | 根因 | 解法 |
| --- | --- | --- |
| 追踪没上报到后端，代码却不报错 | 漏设上报端点变量 | 设 `OTEL_EXPORTER_OTLP_ENDPOINT` 为服务地址加 `/api/public/otel` |
| 连接校验超时 | Python 请求被系统代理拦截 | 在客户端初始化前设 `NO_PROXY=localhost,127.0.0.1` |
| 浏览器或 curl 访问本地服务返回 502 | 同样是系统代理拦截 | curl 加 `--noproxy '*'`，浏览器自动化工具加不走代理的参数 |
| 导入接入类报错 | 沿用了旧版导入路径 | v4 系列一律 `from langfuse.langchain import CallbackHandler` |
| 调用树只有一根光杆 | 观测对象只调了一次模型 | 换一个至少含一次工具调用的 Agent 再观察 |

另外两点常被忽略：自托管场景必须显式把服务地址设成本机地址，不设时 SDK 会默认连云端；以及看 token 时会发现同一次请求里模型调用的输入 token 逐次递增——每一步决策的输入都包含此前所有工具结果，这是多步 Agent 消耗高于单次问答的直接原因，可用它做成本分析。
