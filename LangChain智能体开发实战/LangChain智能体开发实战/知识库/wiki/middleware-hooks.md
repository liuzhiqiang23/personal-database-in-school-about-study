---
concept: middleware-hooks
one_liner: 中间件把横切逻辑写成独立单元、挂到智能体执行的 6 个固定时机上，声明式注册而不改动工具与主流程
stage_span: [stage-2]
prerequisites: [create-agent-entry, tool-calling-loop]
related: [middleware-execution-order, builtin-middleware-catalog, middleware-flow-control]
applications: [middleware-execution-order, builtin-middleware-catalog, middleware-flow-control, pii-redaction-middleware, deepagents-harness]
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#一、开篇：把横切逻辑从「到处手写」变成「声明式挂载」
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、6 个 hook 与基类 AgentMiddleware 总览
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、写装饰器式 middleware 并挂载
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、装饰器式 vs 类式：两种写法选型
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、对照实验：create_deep_agent 与 create_agent + 手装 middleware 的差别
---

## 是什么

智能体上线后要承担很多与业务问答无关却躲不掉的事：调模型前记日志、限制调用次数控成本、把敏感信息脱敏后再送给模型、工具抛错时不让整个智能体崩溃。这类逻辑与具体业务无关却散落在每个调用点上，软件工程称之为横切关注点。

中间件的解法是把这些逻辑写成独立单元，在组装智能体时通过 `middleware=[...]` 参数声明挂上去，不改动工具函数与主流程一行代码。核心机制是**钩子**：框架在执行的若干固定时机预留挂载点，中间件把逻辑挂到这些点上，到点了框架自动回调。

v1 提供 6 个钩子，分两类：

| 钩子 | 类型 | 触发时机 | 典型用途 |
| --- | --- | --- | --- |
| `before_agent` | 节点 | 智能体循环开始前（仅一次） | 初始化审计上下文、注入全局信息 |
| `before_model` | 节点 | 每次调模型前 | 打日志、脱敏、限流前置检查 |
| `after_model` | 节点 | 每次调模型后 | 统计 token、记录模型决策 |
| `after_agent` | 节点 | 智能体循环结束后（仅一次） | 收尾、汇总、上报 |
| `wrap_model_call` | 包裹 | 包住一次模型调用 | 模型降级、最后一刻改写请求 |
| `wrap_tool_call` | 包裹 | 包住一次工具调用 | 工具错误捕获、重试、结果改写 |

## 怎么用

装饰器式（最轻量）：写一个普通函数，用钩子名装饰它：

```python
from langchain.agents.middleware import before_model, after_model

@before_model
def log_before(state, runtime):
    msgs = state["messages"]
    print(f"[before_model] 消息数={len(msgs)}")
    return None          # 返回 None = 不修改 state，继续正常流程

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[log_before],       # 声明挂载，不改动工具和主流程
)
```

类式（可同时实现多个钩子、可携带实例状态）：

```python
from langchain.agents.middleware import AgentMiddleware

class CountingMiddleware(AgentMiddleware):
    def __init__(self, tag):
        self.tag = tag
        self.call_count = 0          # 实例状态，跨多次调用累积

    def before_model(self, state, runtime):
        self.call_count += 1
        print(f"[类式 before_model] [{self.tag}] 第{self.call_count}次")
        return None
```

## 关键细节与参数

- **导入集中**：6 个钩子、基类与内置中间件全部可从 `langchain.agents.middleware` 一处导入；基类真实路径是 `langchain.agents.middleware.types.AgentMiddleware`。
- **装饰器是语法糖**：被装饰的函数打印类型会显示为基类的子类、类名就是函数名——装饰器背后动态创建了一个只实现该钩子的子类。两种写法底层是同一套机制。
- **节点钩子签名是 `fn(state, runtime)`**：`state["messages"]` 拿到当前消息流，返回 `None` 表示只观察不修改，返回字典可修改状态。
- **包裹钩子签名完全不同**：`fn(request, handler)`，与节点钩子不可混用（见 middleware-flow-control）。
- **每次调模型都触发一次 `before_model`**：含一次工具调用的问题需要两轮模型调用，实测 `before_model` 触发 2 次、消息数从 1 变到 3；而 `before_agent` / `after_agent` 只在循环头尾各触发一次。
- **未实现的钩子自动跳过**，不报错。
- 选型判断线：单钩子、无状态用装饰器；多钩子或需要跨调用累积状态用类式。
- 中间件与业务完全解耦：同一个中间件类可挂到工具集完全不同的智能体上，实例状态各自独立（实测两个实例各自计数、互不干扰）。

## 常见陷阱

- **把两轮触发当成重复触发**：含工具调用的问题必然触发两轮模型调用，日志里出现两次不是 bug。
- **凭装饰器式的印象去猜包裹钩子的签名**：两类钩子签名不同，混用会直接抛类型错误。
- **需要状态却用了装饰器式**：装饰器式无法跨调用累积状态（如计数、配额），这类需求必须用类式。
