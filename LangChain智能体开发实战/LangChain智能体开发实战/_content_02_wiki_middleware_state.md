# A 部分 · 知识库概念全量（第 3 组：中间件与横切 + 第 4 组：状态记忆审批）

## 第三组 中间件与横切（5 篇）

### middleware-hooks
- **关键点**：middleware 把「到处都要加的同一段代码」（横切关注点）从手写变成声明式挂载——create_agent(middleware=[...])。源码模块 langchain.agents.middleware。钩子（hook）机制是框架在 Agent 执行的固定时机预留挂载点。
- **6 个 hook 分两类**：
  - **节点 hook**（固定时刻、观察或修改状态）：before_agent（循环开始前，仅一次）、before_model（每次调模型前）、after_model（每次调模型后）、after_agent（循环结束后，仅一次）。
  - **包裹 hook**（把目标调用「包」在中间）：wrap_model_call（包住一次模型调用）、wrap_tool_call（包住一次工具调用）。
- **签名差异**：节点 hook 是 fn(state, runtime)；包裹 hook 是 fn(request, handler)。两者不同。
- **AgentMiddleware 基类**：路径 langchain.agents.middleware.types.AgentMiddleware。@before_model 装饰器是语法糖（动态创建只实现 before_model 的子类）。
- **关联**：middleware-execution-order、builtin-middleware-catalog、pii-redaction-middleware、middleware-flow-control。

### middleware-execution-order
- **关键点**：执行顺序铁律——before_* 系列按列表正序触发（M1→M2→M3），after_* 系列按列表逆序触发（M3→M2→M1）。栈式结构，先进后出，像穿脱衣服。列表顺序就是安排依赖关系的开关。
- **wrap_model_call 嵌套（俄罗斯套娃）**：进入正序一层层往里走，再逆序往外退。最内层最贴近真实 LLM 调用，可在真实调用最后一刻改写请求（ModelFallbackMiddleware 降级的实现基础）。
- **关联**：middleware-hooks、builtin-middleware-catalog。

### builtin-middleware-catalog
- **关键点**：LangChain v1 当前导出 14 个内置 middleware，开箱即用、一行声明：
  - 限流：ModelCallLimitMiddleware（thread_limit 会话累计上限 / run_limit 单次运行上限 / exit_behavior 超限行为，'end' 默认安静结束，'error' 抛异常）、ToolCallLimitMiddleware。
  - 脱敏：PIIMiddleware。
  - 重试：ModelRetryMiddleware、ToolRetryMiddleware。
  - 降级：ModelFallbackMiddleware（位置参数 (first_model, *additional_models)，不是 fallback_model= 关键字）。
  - 上下文：SummarizationMiddleware、ContextEditingMiddleware。
  - 人工审批：HumanInTheLoopMiddleware。
  - 其他：TodoListMiddleware、LLMToolSelectorMiddleware、LLMToolEmulator、ShellToolMiddleware、FilesystemFileSearchMiddleware。
- **参数风格不统一**：ModelCallLimitMiddleware 用关键字参数（run_limit=2），ModelFallbackMiddleware 用位置参数。
- **关联**：middleware-hooks、middleware-execution-order、pii-redaction-middleware。

### pii-redaction-middleware
- **关键点**：PIIMiddleware 把敏感信息在送进模型前脱敏（时机 in before_model）。两种策略：redact（整段替换成占位符）、mask（部分遮罩、保留尾部用于识别）。
- **内置脱敏类型只有 5 种**（email、credit_card、ip、mac_address、url），**不含中文手机号**——脱敏中文手机号需通过 detector 参数传正则（如 r"1[3-9]\d{9}"）。
- **关联**：builtin-middleware-catalog、middleware-hooks。

### middleware-flow-control
- **关键点**：hook 不只是观察者还能当拦截者。
  - **wrap_tool_call 捕获工具错误**：把工具抛出的异常改写成一条正常 ToolMessage 喂回模型，让 Agent 优雅继续不崩溃。返回的 ToolMessage 必须带 tool_call_id=request.tool_call["id"]，否则模型报 400。
  - **jump_to 提前退出**：让 Agent 在调模型前提前退出。必须先 @hook_config(can_jump_to=["end"]) 显式声明跳转权限，否则运行时报错（防误用安全设计）。
- **关联**：middleware-hooks、middleware-execution-order。

## 第四组 状态、记忆与审批（9 篇）

### checkpointer-persistence
- **关键点**：Agent 默认无状态。checkpointer 是「记事本」——每走一步把完整对话状态存档，下次调用自动读回接着跑。记忆是 LangGraph 提供的机制（底层图执行引擎）。
- **关键实现**：InMemorySaver（内存，随 langgraph 安装，import langgraph.checkpoint.memory，开发最常用）；SqliteSaver（SQLite 文件，需 pip install langgraph-checkpoint-sqlite，配合 SqliteSaver.from_conn_string + context manager）；PostgresSaver（PostgreSQL，pip install langgraph-checkpoint-postgres，生产/多实例）。
- **加 checkpointer 不改变 Agent 类型**：返回仍是 CompiledStateGraph，记忆是「叠加」能力。
- **关联**：thread-id-isolation、state-snapshot-inspection、time-travel-replay、checkpointer-backends。

### thread-id-isolation
- **关键点**：thread_id 是会话线程标识。同一 thread_id 多次调用共享记忆，不同 thread_id 彼此隔离。触发记忆的开关在 invoke 的第二个参数 config：{"configurable": {"thread_id": ...}}。
- **光挂 checkpointer 不够**：真正触发记忆的是调用时传的 thread_id。生产标准写法 thread_id = str(user.id)。
- **关联**：checkpointer-persistence、state-snapshot-inspection。

### state-snapshot-inspection
- **关键点**：get_state(config) 返回 StateSnapshot（状态快照），8 个字段——values（核心是 values["messages"]）、next（下一步要执行的节点，() 表示已到 END 终态、("model",) 停在等模型、("tools",) 停在等工具执行）、config（含 thread_id 与 checkpoint_id 唯一 UUID）、metadata（含 source、step）、created_at、parent_config（快照间串成链）、tasks（待执行任务，HITL 才有值）、interrupts（中断点，HITL 才有值）。
- **metadata.ls_integration = 'langchain_create_agent'** 坐实底层事实：create_agent 底层就是 LangGraph。
- **checkpoint 存的是完整 messages 列表，不是对话摘要**：每条原样保留。
- **关联**：checkpointer-persistence、thread-id-isolation、time-travel-replay。

### time-travel-replay
- **关键点**：get_state_history(config) 看完整时间线，倒序返回——history[0] 是最新快照，history[-1] 是初始空快照。每个 super-step 对应一个 checkpoint_id（UUID，定位某历史时刻的锚点）。
- **时间旅行**：把某个历史快照的 checkpoint_id 填进 config 从那一刻重新出发。工程铁律：只能从 next=() 的「稳态快照」出发，从含未完成 tool_calls 的进行中快照重放会被模型 API 拒绝（400 An assistant message with tool_calls must be followed by tool messages）。修复用 filter：[h for h in get_state_history(config) if h.next == ()]。
- **关联**：state-snapshot-inspection、checkpointer-persistence。

### checkpointer-backends
- **关键点**：checkpointer 三档线性升级路径，接口一致、仅存储介质不同。InMemorySaver（进程内存、重启记忆全清、无额外安装、开发/调试/单元测试）；SqliteSaver（本地 SQLite 文件、重启记忆保留、pip install langgraph-checkpoint-sqlite、本地持久/单机演示）；PostgresSaver（PostgreSQL、重启记忆保留、pip install langgraph-checkpoint-postgres、生产/多实例/高并发）。
- **InMemorySaver 边界**：状态在进程内存，进程退出内存清空、所有记忆消失。
- **SqliteSaver 边界**：DB 文件必须放主盘（APFS），不要放 ExFAT 外置磁盘（不支持 POSIX 文件锁，WAL 模式失败）。
- **关联**：checkpointer-persistence。

### human-in-the-loop-interrupt
- **关键点**：HITL 用 LangGraph 中断机制让 Agent 执行到关键节点暂停，把状态和选项交给人审批，等人工给「继续/改参/拒绝」命令后再恢复。危险动作（转账、不可撤回邮件、删数据）必须先经人确认。
- **interrupt 函数**：from langgraph.types import interrupt。调用后图暂停执行，把 state 快照存进 checkpointer（这解释了 HITL 与记忆共用 checkpointer 基础设施）。**execution interrupt 只发生一次**，图停在那个节点等待人工。interrupt 的调用位置是「即将执行危险动作之前」。
- **关联**：interrupt-resume-replay、hitl-iron-rules、hitl-implementation-routes、thread-id-isolation、checkpointer-persistence。

### interrupt-resume-replay
- **关键点**：触发审批的运行时入口是 agent.aget_state()（在中断点上读走大状态快照，await 后快照里有 tasks 和 details 字典，details 里能看到「pending approve」的值、来源 state 值、下一步处理线程）。人工判断后通过 Command(resume=...) 恢复图执行，这个 resume 是人工裁决的代码化表达。
- **Command 格式**：Command(resume=Goto)，把 resume 从单值升级为多字段复杂对象就是「Command 里带 State 更新」：Command(resume={"approve": True, "note": "..."})——既能 resume 又能用 update 字段同时更新 state。
- **关联**：human-in-the-loop-interrupt、hitl-implementation-routes。

### hitl-iron-rules
- **关键点**：HITL 铁律——human in the loop 依赖 checkpointer 持久化，缺 thread_id 无法恢复会话；interrupt 是「暂停不是终止」，恢复必须走 Command(resume=...) 并显式给出裁决值；interrupt 逻辑必须在建图时声明，无法运行时临时插入。
- **关联**：hitl-implementation-routes、human-in-the-loop-interrupt。

### hitl-implementation-routes
- **关键点**：三种实现路径——①create_agent 里配 HumanInTheLoopMiddleware（内置，最省事）；②interrupt + Command(resume=...) 手动实现（最可控）；③core graph 手动建图（最底层）。core graph 与「哪里插 interrupt」可以完全分离。graph.add_command 的三种去向：回复终点 END、常驻 resume 节点 re_censor、本 batch 特有的 approved_node。
- **关联**：human-in-the-loop-interrupt、interrupt-resume-replay、hitl-iron-rules。
