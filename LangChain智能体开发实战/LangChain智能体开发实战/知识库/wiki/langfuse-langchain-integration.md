---
concept: langfuse-langchain-integration
one_liner: 接入只是建一个回调处理器并挂到调用配置的 callbacks 上，业务侧零改动，但漏设上报端点会让 trace 静默丢失
stage_span: [stage-2]
prerequisites: [agent-tracing-model, langfuse-selfhost-setup]
related: [observability-platform-choice, local-environment-traps, business-decoupling-reuse-pattern]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、安装 langfuse 并核验接入入口
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、配置凭证与连接验证
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、接入只改两行：CallbackHandler + callbacks
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#七、换 Agent 不换接入：验证可复用性
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#3、本案例踩过的坑速查
---

## 是什么

把智能体接上观测平台，靠的是一个**回调处理器**：它实现了框架的标准回调接口，挂到执行配置上之后，会自动把每一步调用上报成 trace。因为走的是标准回调机制，它能无侵入地嵌进任何智能体的执行流。

整个接入只新增三样东西：几个环境变量、一个回调处理器实例、一处调用配置参数。智能体的工具定义、模型选择、图结构、检查点存储器一概不动——这就是"换智能体不换接入"的含义。

## 怎么用

装包与确认入口：

```bash
pip install langfuse
```

```python
from langfuse.langchain import CallbackHandler
```

配好凭证与上报端点（顺序有讲究，绕过代理要在客户端初始化之前设）：

```python
import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"   # 必须在客户端初始化前设
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-course-demo-public"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-course-demo-secret"
os.environ["LANGFUSE_HOST"]       = "http://localhost:3000"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:3000/api/public/otel"
```

接入本身只有两行：

```python
handler = CallbackHandler()                       # ① 建一个回调处理器
agent.invoke(
    {"messages": [{"role": "user", "content": "我的订单 A1001 发货了吗？麻烦帮我查一下物流情况"}]},
    config={"callbacks": [handler]},              # ② 挂到 callbacks 上
)
```

换一个业务完全不同的智能体时，这两行一字不改。

## 关键细节与参数

- **入口类的导入路径随版本变过**：老资料里的 `from langfuse.callback import CallbackHandler` 在新版已不适用。实测装到 4.7.1，正确路径是 `from langfuse.langchain import CallbackHandler`；只要是 v4 系列，这一路径都成立。装包无需任何额外的可选依赖参数。
- **自托管必须显式设主机地址**，否则客户端默认连云端。
- **v4 走的是通用可观测数据标准协议上报**，因此必须设导出端点变量；漏设时调用链虽在本地产生、却导不到后端——这是最容易漏的一步，且是**静默失败**。
- 初始化后可用连接自检确认 Python 侧连通。
- 复用实测：一个三个全新工具的退款咨询智能体，触发 3 次工具调用、7 条消息，接入代码与第一个智能体完全相同，trace 照样完整上报。
- 坑位速查：

| 现象 | 根因 | 解法 |
| --- | --- | --- |
| 访问本地端口返回 502 | 系统代理拦截本地请求 | 命令行绕过代理；Python 设免代理变量 |
| 连接自检超时 | Python 请求也被系统代理拦截 | 在客户端初始化前设好免代理变量 |
| trace 没上报到后端 | 漏设导出端点变量 | 设为后端地址加上报路径 |

## 常见陷阱

- **按旧资料写导入路径**：v4 系列改过入口模块，照旧写会直接导入失败。
- **免代理变量设晚了**：必须在客户端初始化**之前**设置，之后再设不生效，表现为连接自检超时。
- **以为 trace 没出现是网络慢**：漏设导出端点时是静默失败，等多久都不会出现，先查变量再查网络。
- **为了接入去改业务代码**：接入是零侵入的，任何需要改工具或图结构的做法都说明走偏了。
