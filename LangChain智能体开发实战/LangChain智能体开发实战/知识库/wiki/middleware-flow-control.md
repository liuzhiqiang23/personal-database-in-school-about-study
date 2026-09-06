---
concept: middleware-flow-control
one_liner: 钩子不只是观察者——包裹工具调用可把异常转成正常结果避免崩溃，调模型前跳转可让智能体不调模型就提前结束
stage_span: [stage-2]
prerequisites: [middleware-hooks, message-stream-anatomy]
related: [middleware-execution-order, builtin-middleware-catalog, human-in-the-loop-interrupt]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#六、hook 不只是观察者：控制 Agent 执行流
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、wrap_tool_call：工具抛错时不让 Agent 崩溃
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、jump_to：让 Agent 在调模型前提前退出
---

## 是什么

打日志、统计、脱敏这类钩子是观察者——看完不改变执行路径。但钩子还能当拦截者，主动改变智能体的行为。两种典型的控制能力：

- **包裹工具调用**：把一次工具调用包在中间，捕获工具抛出的异常、转换成一条正常的工具结果喂回模型，让智能体优雅继续而不是崩溃。
- **调模型前跳转**：在调模型前的钩子里返回跳转指令，让智能体根本不调模型就直接结束，同时注入一条自定义回复。典型场景是合规拦截——命中违禁词时不必把消息送给模型，既合规又省一次模型调用成本。

这两者与按次数机械限流形成互补：限流是内置的自动次数闸门，跳转是基于业务逻辑的自定义退出，还能注入任意自定义回复。

## 怎么用

工具异常兜底：

```python
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

@wrap_tool_call
def handle_tool_error(request, handler):
    try:
        return handler(request)          # 注意：handler 要传 request，不是 handler()
    except Exception as e:
        return ToolMessage(
            content=f"工具执行失败：{e}，建议稍后重试",
            tool_call_id=request.tool_call["id"],   # 必须带，否则模型报 400
        )
```

内容拦截提前退出：

```python
from langchain.agents.middleware import before_model, hook_config
from langchain_core.messages import AIMessage

@before_model
@hook_config(can_jump_to=["end"])    # 必须显式声明跳转权限
def content_filter(state, runtime):
    last = state["messages"][-1].content
    if "退款" in last:
        return {
            "messages": [AIMessage(content="您的问题包含敏感词，已被自动拦截，请联系人工客服。")],
            "jump_to": "end",        # 直接跳到结束，模型不被调用
        }
    return None                      # 未命中 → 正常流程
```

## 关键细节与参数

- **包裹钩子的完整签名**：`fn(request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage]) -> ToolMessage`。它与节点钩子的 `fn(state, runtime)` 完全不同。
- **必须把 request 传回 handler**：把 handler 当零参数函数调会触发 `TypeError: execute() missing 1 required positional argument`。查中间件类型模块源码（约第 2047 行）确认的正确写法是 `handler(request)`。
- **回填的工具消息必须带 `tool_call_id`**：漏掉这个字段，模型会因"有工具调用却没有对应结果"而返回 400 错误。
- **跳转前必须声明权限**：不加 `@hook_config(can_jump_to=["end"])` 会在运行时报错，这是框架防止误用跳转的安全设计。
- 实测效果：工具正常时包裹钩子透明传递，消息数 4，与不挂中间件时一致；工具抛错时异常被转成一条工具消息喂回，模型据此优雅回答"建议稍后重试"，整个智能体没有崩溃。拦截场景下含违禁词的问题只产生 2 条消息（用户消息 + 拦截回复），模型从未被调用。
- 职责层次：工具执行错误归包裹工具调用管，模型层面的错误归包裹模型调用或调模型前的钩子管。

## 常见陷阱

- **凭装饰器式印象猜包裹钩子签名**：两类钩子签名完全不同，遇到类型错误时先回头确认真实签名（必要时查中间件类型模块源码），不要凭印象套用。
- **用宽泛的异常捕获包住会抛控制信号的调用**：在人工审批场景里，宽泛捕获会吞掉暂停信号导致审批被绕过（见 hitl-iron-rules）。工具兜底与审批中断的异常处理策略必须分开对待。
- **忘了返回值语义**：调模型前的钩子返回 `None` 表示继续正常流程，返回字典才修改状态；跳转必须同时返回跳转键。
