---
name: writing-agent-middleware
description: 用 LangChain v1 的 middleware 钩子把日志、审计、错误兜底、合规拦截这类横切逻辑写成独立单元，声明式挂到任意 Agent 上而不改工具与主流程。Use when 需要给 Agent 加自定义日志或审计、在调模型前拦截违禁内容、让工具抛错时 Agent 不崩溃、或排查「hook 触发次数比预期多」「wrap_tool_call 报 execute() missing 1 required positional argument」「用了 jump_to 却运行时报错」这类问题时。涵盖装饰器式与类式写法、六个钩子的时机、执行顺序规律、工具错误接管、提前退出、跨 Agent 复用；不含开箱即用的内置 middleware（见 applying-builtin-middleware）。
allowed-tools: Bash(python:*)
sources:
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、6 个 hook 与基类 AgentMiddleware 总览
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、写装饰器式 middleware 并挂载
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、装饰器式 vs 类式：两种写法选型
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、3 个 middleware 同挂，看 before / after 触发顺序
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、wrap_model_call 嵌套：俄罗斯套娃式的包裹
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#1、wrap_tool_call：工具抛错时不让 Agent 崩溃
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、jump_to：让 Agent 在调模型前提前退出
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#七、换 agent 即复用：middleware 与业务解耦
---

## 能力目标

把与业务无关、却每处都要插一段的逻辑（日志、审计、限速配额、合规拦截、工具错误兜底）写成独立的 middleware 单元，通过 `create_agent(..., middleware=[...])` 声明挂载：工具函数与系统提示词一行不改，同一个 middleware 可原样挂到任意 Agent 上、实例状态互不干扰。

## 前置

- 已能用 `create_agent` 组装 Agent（见 building-tool-calling-agent）。
- 全部能力集中在 `langchain.agents.middleware` 一个模块，基类是 `AgentMiddleware`。
- 需要会写 Python 装饰器与类继承。

## 实操流程

1. 先按逻辑该发生的时机选钩子。六个钩子分两类：节点钩子（到点触发一下）与包裹钩子（把目标调用包在中间、前后都能插手）：

   | 钩子 | 类型 | 触发时机 | 典型用途 |
   | --- | --- | --- | --- |
   | `before_agent` | 节点 | 智能体循环开始前（仅一次） | 初始化审计上下文 |
   | `before_model` | 节点 | 每次调模型前 | 打日志、脱敏、前置检查、合规拦截 |
   | `after_model` | 节点 | 每次调模型后 | 统计消耗、记录模型决策 |
   | `after_agent` | 节点 | 智能体循环结束后（仅一次） | 收尾、汇总、上报 |
   | `wrap_model_call` | 包裹 | 包住一次模型调用 | 模型降级、最后一刻改写请求 |
   | `wrap_tool_call` | 包裹 | 包住一次工具调用 | 工具错误捕获、重试、结果改写 |

   注意「每次调模型」：含一次工具调用的问题需要两轮模型调用，`before_model` / `after_model` 会各触发两次，而 `before_agent` / `after_agent` 全程各一次。

2. 单钩子、无状态的逻辑用装饰器式写法，函数签名固定为 `fn(state, runtime)`，返回 `None` 表示只观察不改状态：

   ```python
   # step2_log_middleware.py
   from langchain.agents import create_agent
   from langchain.agents.middleware import before_model, after_model

   @before_model
   def log_before(state, runtime):
       print(f"[before_model] 消息数={len(state['messages'])}")
       return None

   @after_model
   def log_after(state, runtime):
       print("[after_model] 模型已返回")
       return None

   agent = create_agent(
       model="deepseek:deepseek-chat",
       tools=[query_order, track_shipping],
       system_prompt="你是一个订单运营助手。",
       middleware=[log_before, log_after],
   )
   ```

   ```bash
   python step2_log_middleware.py
   ```

3. 需要多个钩子或需要跨调用累积状态（计数、配额、审计句柄）时改用类式，继承 `AgentMiddleware` 并实现对应方法：

   ```python
   from langchain.agents.middleware import AgentMiddleware

   class AuditMiddleware(AgentMiddleware):
       def __init__(self, name):
           self.name = name
           self.call_count = 0
       def before_model(self, state, runtime):
           self.call_count += 1
           print(f"[before_model] [{self.name}] 第 {self.call_count} 次")
       def after_model(self, state, runtime):
           print(f"[after_model] [{self.name}] 本轮工具:",
                 [c["name"] for c in getattr(state["messages"][-1], "tool_calls", [])])
   ```

   两种写法底层是同一套机制——装饰器只是动态创建 `AgentMiddleware` 子类的语法糖。判断线：单钩子无状态用装饰器，多钩子或要带状态用类。

4. 挂多个 middleware 时按依赖关系排列表顺序，规律是**正序进、逆序出**：`before_*` 按列表正序触发，`after_*` 按逆序触发，`wrap_*` 层层嵌套（入口正序、出口逆序，最内层最贴近真实调用）。未实现某钩子的 middleware 会被自动跳过、不报错。需要「先脱敏再记日志」，就把脱敏的排在日志前面。

5. 要让工具抛错时 Agent 不崩溃，用 `wrap_tool_call` 接管。它的签名与节点钩子完全不同，是 `fn(request, handler)`，且 `handler` **必须把 request 传回去**：

   ```python
   # step6_wrap_tool_call.py
   from langchain.agents.middleware import wrap_tool_call
   from langchain_core.messages import ToolMessage

   @wrap_tool_call
   def handle_tool_error(request, handler):
       try:
           return handler(request)          # 传 request，不是 handler()
       except Exception as e:
           return ToolMessage(
               content=f"工具执行失败：{e}，建议稍后重试",
               tool_call_id=request.tool_call["id"],   # 必须带，否则模型报 400
           )
   ```

   工具正常时透明传递；抛错时异常被转成一条正常的工具结果喂回模型，模型据此优雅作答。

6. 要在调模型前直接结束循环（合规拦截、省一次模型调用），用 `before_model` 返回带 `jump_to` 的 dict，并**显式声明跳转权限**：

   ```python
   # ext4_jump_to_early_exit.py
   from langchain.agents.middleware import before_model, hook_config
   from langchain_core.messages import AIMessage

   @before_model
   @hook_config(can_jump_to=["end"])
   def content_filter(state, runtime):
       last = state["messages"][-1].content
       if "退款" in last:
           return {
               "messages": [AIMessage(content="您的问题包含敏感词，已被自动拦截，请联系人工客服。")],
               "jump_to": "end",
           }
       return None
   ```

## 校验回路

1. **触发验证**：挂上 middleware 跑一个含工具调用的问题，确认钩子按预期触发——含一次工具调用时 `before_model` / `after_model` 各触发两次是正常的，不是重复触发。
2. **顺序验证**：同时挂三个各自打印标识的 middleware，确认 `before_*` 是正序、`after_*` 是逆序，且两轮模型调用都遵守。
3. **接管验证**：故意让工具抛异常，确认返回消息里出现你构造的失败提示 ToolMessage、Agent 跑完没崩；触发 `jump_to` 的问题只产生两条消息（用户消息 + 拦截回复），模型未被调用。
4. **复用验证**：把同一个 middleware 类分别实例化挂到两个工具集不同的 Agent，确认都正常触发且两个实例的计数互相独立。

## 常见陷阱

- **拿节点钩子的签名去写包裹钩子**：节点钩子是 `fn(state, runtime)`，包裹钩子是 `fn(request, handler)`。把 `handler` 当零参数函数调会报 `TypeError: execute() missing 1 required positional argument`，正确写法是 `handler(request)`。
- **构造 ToolMessage 时漏掉 `tool_call_id`**：模型会因为「有工具调用却没有对应结果」返回 400。一律带上 `request.tool_call["id"]`。
- **直接返回 `jump_to` 而不声明权限**：必须先加 `@hook_config(can_jump_to=["end"])`，否则运行时报错——这是框架防止误用跳转的安全设计。
- **误以为列表顺序无关紧要**：有依赖关系的 middleware 顺序错了，效果会静默偏差（例如日志记到的是未脱敏的消息）。列表顺序就是安排依赖关系的开关。
- **装饰器式硬扛状态需求**：装饰器式拿不到跨调用累积的实例状态，计数、配额一类需求换类式写法。
