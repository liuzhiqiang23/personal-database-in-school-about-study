# LangChain 知识库

## 这是什么

本库覆盖用 LangChain v1 从零搭起一个能跑上生产的智能体所需的全部技术知识：环境与分层包生态、`create_agent` 与工具调用循环、结构化输出、中间件横切系统、持久化记忆与状态快照、危险动作的人工审批、调用链可观测、智能体化检索增强问答、长程任务脚手架，以及贯穿各层的业务解耦复用方式与本机环境陷阱。导入后，你的 Agent 既能讲清每个机制为什么这样设计，也能给出取自真实执行的关键代码与参数，直接照着实现。

## 学习路径

按前置依赖推荐的阅读顺序（前置概念在前）：

1. python-env-and-venv-setup（版本门槛与虚拟环境）
2. langchain-package-stack（分层包生态与版本核验，依赖 1）
3. deepseek-provider-integration（模型接入与型号能力边界，依赖 2）
4. create-agent-entry（智能体组装入口，依赖 2、3）
5. tool-function-contract（工具三规范与 docstring 硬约束，依赖 4）
6. tool-calling-loop（核心范式，依赖 4、5）
7. message-stream-anatomy（消息流字段与结果路由，依赖 6）
8. parallel-tool-calls（并行调用与不猜参数，依赖 6、7）
9. system-prompt-boundary（提示词的职责边界，依赖 4、5）
10. invoke-vs-stream（两种调用颗粒度，依赖 4、6）
11. pydantic-schema-design（数据模型与两层校验，依赖 2）
12. structured-output-response-format（结构化结果，依赖 4、11）
13. structured-output-strategy-compat（两条策略与兼容边界，依赖 12、3）
14. middleware-hooks（6 个钩子与两种写法，依赖 4、6）
15. middleware-execution-order（正序进、逆序出，依赖 14）
16. builtin-middleware-catalog（14 个内置中间件，依赖 14）
17. pii-redaction-middleware（脱敏挡在模型之前，依赖 14、16）
18. middleware-flow-control（工具兜底与提前退出，依赖 14、7）
19. checkpointer-persistence（记忆来自外部存档，依赖 4、6）
20. thread-id-isolation（会话命名空间，依赖 19）
21. state-snapshot-inspection（打开存档看状态，依赖 19、7）
22. time-travel-replay（从历史快照重放，依赖 21、19）
23. checkpointer-backends（三档存储升级路径，依赖 19）
24. human-in-the-loop-interrupt（危险动作前的审批闸门，依赖 19、5、20）
25. interrupt-resume-replay（续跑时节点从头重执行，依赖 24）
26. hitl-iron-rules（四条不能违反的纪律，依赖 24、25）
27. hitl-implementation-routes（两条实现路线与传参差异，依赖 24、14）
28. agent-tracing-model（调用链树与三类节点，依赖 6、7）
29. langfuse-selfhost-setup（自托管观测栈，依赖 28）
30. langfuse-langchain-integration（零侵入接入，依赖 28、29）
31. observability-platform-choice（按合规选路径，依赖 28）
32. document-chunking（切分与重叠，依赖 2）
33. embedding-and-vectorstore（向量化、向量库与检索器，依赖 32）
34. agentic-rag-loop（检索器变工具、自主改写重试，依赖 5、4、33）
35. retrieval-grader（二元评分门控与知识边界，依赖 34、11、13）
36. deepagents-harness（脚手架本质与三层取舍，依赖 4、14）
37. todo-planning-mechanism（待办清单防遗忘，依赖 36、10）
38. subagent-delegation（委派隔离上下文，依赖 36、9）
39. virtual-filesystem-context-engineering（中间结果外置暂存，依赖 36）
40. business-decoupling-reuse-pattern（各层换业务只动一处输入，依赖 4、5）
41. local-environment-traps（伪装成框架报错的环境坑，依赖 1）

## 概念总表

| 概念 | 一句话 | 能力域 | 前置 | 相关 | 应用于 |
|------|--------|--------|------|------|--------|
| python-env-and-venv-setup | 要求 Python 3.10+，先核对解释器再用达标版本建虚拟环境 | 环境与生态 | | langchain-package-stack、local-environment-traps | deepseek-provider-integration、create-agent-entry |
| langchain-package-stack | 分层发布的多包生态，按需安装、版本核验统一用安装元数据 | 环境与生态 | python-env-and-venv-setup | deepseek-provider-integration、create-agent-entry、local-environment-traps | create-agent-entry、deepagents-harness、embedding-and-vectorstore |
| deepseek-provider-integration | 提供方冒号模型名接入，凭证走环境变量，型号必须支持工具调用 | 环境与生态 | langchain-package-stack | create-agent-entry、structured-output-strategy-compat | tool-calling-loop、structured-output-strategy-compat、agentic-rag-loop |
| local-environment-traps | 四类本机环境坑伪装成框架报错：残留、资源分叉、文件锁、代理 | 环境与生态 | python-env-and-venv-setup | checkpointer-backends、embedding-and-vectorstore、langfuse-langchain-integration、langfuse-selfhost-setup | |
| create-agent-entry | 把声明式配置编译成可执行图，返回类型恒为编译后的状态图 | 智能体核心与输出契约 | langchain-package-stack、deepseek-provider-integration | tool-function-contract、system-prompt-boundary、invoke-vs-stream | tool-calling-loop、structured-output-response-format、middleware-hooks、checkpointer-persistence、agentic-rag-loop、deepagents-harness |
| tool-function-contract | 带类型注解与 docstring 的普通函数即工具，docstring 是硬约束 | 智能体核心与输出契约 | create-agent-entry | tool-calling-loop、agentic-rag-loop、business-decoupling-reuse-pattern | tool-calling-loop、parallel-tool-calls、agentic-rag-loop、human-in-the-loop-interrupt |
| tool-calling-loop | 模型在循环里自主调工具、读结果、再决定下一步直到完成 | 智能体核心与输出契约 | create-agent-entry、tool-function-contract | message-stream-anatomy、parallel-tool-calls、invoke-vs-stream | middleware-hooks、checkpointer-persistence、agentic-rag-loop、agent-tracing-model |
| message-stream-anatomy | 四类消息各司其职，工具结果靠调用编号路由回对应请求 | 智能体核心与输出契约 | tool-calling-loop | parallel-tool-calls、state-snapshot-inspection、agent-tracing-model | middleware-flow-control、state-snapshot-inspection、human-in-the-loop-interrupt |
| parallel-tool-calls | 互不依赖的多任务在同一条消息里并行发起，参数不全则追问 | 智能体核心与输出契约 | tool-calling-loop、message-stream-anatomy | deepseek-provider-integration、subagent-delegation | business-decoupling-reuse-pattern |
| system-prompt-boundary | 提示词控制怎么说、不控制做什么，选工具由工具描述决定 | 智能体核心与输出契约 | create-agent-entry、tool-function-contract | tool-calling-loop、subagent-delegation | human-in-the-loop-interrupt、business-decoupling-reuse-pattern |
| invoke-vs-stream | 一次性返回完整消息与逐步吐出增量，是同一循环的两种颗粒度 | 智能体核心与输出契约 | create-agent-entry、tool-calling-loop | message-stream-anatomy、todo-planning-mechanism | todo-planning-mechanism、virtual-filesystem-context-engineering |
| pydantic-schema-design | 字段描述引导模型填值、类型校验兜底拦截，两层叠加才可信赖 | 智能体核心与输出契约 | langchain-package-stack | structured-output-response-format、retrieval-grader | structured-output-response-format、retrieval-grader、business-decoupling-reuse-pattern |
| structured-output-response-format | 结果里多出一个经校验的对象，下游按字段取值而非解析文本 | 智能体核心与输出契约 | create-agent-entry、pydantic-schema-design | structured-output-strategy-compat、retrieval-grader | retrieval-grader、business-decoupling-reuse-pattern |
| structured-output-strategy-compat | 工具调用兜底与服务商原生两条路线，不支持原生时必须显式退回 | 智能体核心与输出契约 | structured-output-response-format、deepseek-provider-integration | pydantic-schema-design、retrieval-grader | retrieval-grader |
| middleware-hooks | 横切逻辑写成独立单元，挂到 6 个固定时机，声明式注册 | 中间件与横切 | create-agent-entry、tool-calling-loop | middleware-execution-order、builtin-middleware-catalog、middleware-flow-control | middleware-execution-order、builtin-middleware-catalog、middleware-flow-control、pii-redaction-middleware、deepagents-harness |
| middleware-execution-order | 正序进、逆序出、包裹嵌套，列表顺序即依赖关系配置 | 中间件与横切 | middleware-hooks | builtin-middleware-catalog、pii-redaction-middleware | pii-redaction-middleware、middleware-flow-control |
| builtin-middleware-catalog | 14 个开箱即用中间件，一行声明启用，参数风格不统一须先核签名 | 中间件与横切 | middleware-hooks | middleware-execution-order、pii-redaction-middleware、hitl-implementation-routes、todo-planning-mechanism | deepagents-harness、hitl-implementation-routes |
| pii-redaction-middleware | 敏感信息在送进模型前被替换，内置类型仅 5 种、其余靠正则 | 中间件与横切 | middleware-hooks、builtin-middleware-catalog | middleware-execution-order、observability-platform-choice | |
| middleware-flow-control | 钩子可当拦截者：工具异常兜底不崩溃、调模型前跳转提前结束 | 中间件与横切 | middleware-hooks、message-stream-anatomy | middleware-execution-order、builtin-middleware-catalog、human-in-the-loop-interrupt | |
| checkpointer-persistence | 模型无状态，记忆来自每步存档、每轮调用前自动回填 | 状态、记忆与审批 | create-agent-entry、tool-calling-loop | thread-id-isolation、state-snapshot-inspection、checkpointer-backends | thread-id-isolation、state-snapshot-inspection、time-travel-replay、checkpointer-backends、human-in-the-loop-interrupt |
| thread-id-isolation | 会话标识是存档命名空间，一个实例承载无限互不串台的会话 | 状态、记忆与审批 | checkpointer-persistence | state-snapshot-inspection、human-in-the-loop-interrupt | human-in-the-loop-interrupt、time-travel-replay、business-decoupling-reuse-pattern |
| state-snapshot-inspection | 看当前快照与完整时间线，是调试记忆与定位暂停点的主要手段 | 状态、记忆与审批 | checkpointer-persistence、message-stream-anatomy | thread-id-isolation、time-travel-replay、human-in-the-loop-interrupt | time-travel-replay、human-in-the-loop-interrupt |
| time-travel-replay | 填入历史快照编号从那一刻重新出发，只能从稳态快照重放 | 状态、记忆与审批 | state-snapshot-inspection、checkpointer-persistence | thread-id-isolation、interrupt-resume-replay | |
| checkpointer-backends | 三档存储构成开发到生产的升级路径，切换只改一个参数 | 状态、记忆与审批 | checkpointer-persistence | thread-id-isolation、local-environment-traps、virtual-filesystem-context-engineering | business-decoupling-reuse-pattern |
| human-in-the-loop-interrupt | 危险动作前就地暂停抛出审批信息，人工用续跑指令回传决定 | 状态、记忆与审批 | checkpointer-persistence、tool-function-contract、thread-id-isolation | interrupt-resume-replay、hitl-iron-rules、hitl-implementation-routes、middleware-flow-control | interrupt-resume-replay、hitl-iron-rules、business-decoupling-reuse-pattern |
| interrupt-resume-replay | 续跑时节点从第一行重跑，中断之前的副作用会再发生一次 | 状态、记忆与审批 | human-in-the-loop-interrupt | hitl-iron-rules、time-travel-replay | hitl-iron-rules |
| hitl-iron-rules | 四条纪律，其中宽泛异常捕获会吞掉暂停信号让审批被静默绕过 | 状态、记忆与审批 | human-in-the-loop-interrupt、interrupt-resume-replay | middleware-flow-control、hitl-implementation-routes | |
| hitl-implementation-routes | 手写中断与声明式中间件两条等价路线，续跑传参格式不同 | 状态、记忆与审批 | human-in-the-loop-interrupt、middleware-hooks | builtin-middleware-catalog、hitl-iron-rules | |
| agent-tracing-model | 一次请求的多次内部调用被记成一棵树，三类节点各带耗时与消耗 | 可观测 | tool-calling-loop、message-stream-anatomy | langfuse-langchain-integration、observability-platform-choice | langfuse-langchain-integration、observability-platform-choice |
| langfuse-selfhost-setup | 自托管是一整套容器编排，端口、初始化变量链、密码一致性三处要改 | 可观测 | agent-tracing-model | langfuse-langchain-integration、observability-platform-choice、local-environment-traps | langfuse-langchain-integration |
| langfuse-langchain-integration | 建回调处理器挂到调用配置即接入，漏设上报端点会静默丢 trace | 可观测 | agent-tracing-model、langfuse-selfhost-setup | observability-platform-choice、local-environment-traps、business-decoupling-reuse-pattern | business-decoupling-reuse-pattern |
| observability-platform-choice | 自托管与托管服务的决定因素不是技术而是数据能否出境 | 可观测 | agent-tracing-model | langfuse-selfhost-setup、langfuse-langchain-integration、pii-redaction-middleware | |
| document-chunking | 递归切分器在自然语义边界下刀，重叠字符防关键信息被切断 | 检索增强 | langchain-package-stack | embedding-and-vectorstore、agentic-rag-loop | embedding-and-vectorstore、agentic-rag-loop |
| embedding-and-vectorstore | 向量化入库再包成检索器，向量模型的语言匹配度决定检索准不准 | 检索增强 | document-chunking | agentic-rag-loop、retrieval-grader、local-environment-traps | agentic-rag-loop、retrieval-grader |
| agentic-rag-loop | 检索器变工具后由模型自主决定何时检索，还会自己改写查询重试 | 检索增强 | tool-function-contract、create-agent-entry、embedding-and-vectorstore | retrieval-grader、tool-calling-loop、document-chunking | retrieval-grader、business-decoupling-reuse-pattern |
| retrieval-grader | 二元相关性评分门控改写循环，守住知识边界不编造答案 | 检索增强 | agentic-rag-loop、pydantic-schema-design、structured-output-strategy-compat | embedding-and-vectorstore、structured-output-response-format | business-decoupling-reuse-pattern |
| deepagents-harness | 长程脚手架不是新运行时，而是智能体工厂加一组预装中间件 | 长程脚手架与复用 | create-agent-entry、middleware-hooks | todo-planning-mechanism、subagent-delegation、virtual-filesystem-context-engineering、builtin-middleware-catalog | todo-planning-mechanism、subagent-delegation、virtual-filesystem-context-engineering |
| todo-planning-mechanism | 开工前写待办清单并持续更新三态，让长链路不遗漏不重复 | 长程脚手架与复用 | deepagents-harness、invoke-vs-stream | subagent-delegation、virtual-filesystem-context-engineering、builtin-middleware-catalog | business-decoupling-reuse-pattern |
| subagent-delegation | 耗上下文的子任务交给独立子智能体，主体只收精炼结果 | 长程脚手架与复用 | deepagents-harness、system-prompt-boundary | todo-planning-mechanism、virtual-filesystem-context-engineering、parallel-tool-calls | business-decoupling-reuse-pattern |
| virtual-filesystem-context-engineering | 中间结果写进虚拟文件而非堆在对话里，主动管理上下文放什么 | 长程脚手架与复用 | deepagents-harness | subagent-delegation、todo-planning-mechanism、checkpointer-backends | business-decoupling-reuse-pattern |
| business-decoupling-reuse-pattern | 每层换业务只动一处输入，框架骨架一行不改 | 长程脚手架与复用 | create-agent-entry、tool-function-contract | tool-function-contract、pydantic-schema-design、middleware-hooks、thread-id-isolation、agentic-rag-loop | |
