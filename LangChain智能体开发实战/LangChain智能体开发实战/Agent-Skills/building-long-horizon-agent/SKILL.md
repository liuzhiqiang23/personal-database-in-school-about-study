---
name: building-long-horizon-agent
description: 用 deepagents 的 create_deep_agent 搭一个能扛十几步以上长链路任务的智能体，自动获得待办清单规划、子智能体委派与虚拟文件暂存三大机制。Use when 任务超过三步、需要多源资料汇总或分章节写作或多步数据处理、要防止 Agent 走到后面忘了前面的计划、要防止中间数据把上下文撑爆、或排查「长任务抛 GraphRecursionError」「不传模型参数报弃用」这类问题时。涵盖安装与接口核对、最小示例、待办清单驱动、子智能体定义与委派、虚拟文件读写、换任务复用、三层抽象选型；不含单步工具调用 Agent（见 building-tool-calling-agent）与自定义中间件（见 writing-agent-middleware）。
allowed-tools: Bash(python:*), Bash(pip:*)
sources:
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、安装 deepagents 并确认版本
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、核对 v0.6.7 的 API 与内置工具
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、用 create_deep_agent 一行搭出长程 Agent
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、对照实验：create_deep_agent 与 create_agent + 手装 middleware 的差别
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、给长程任务挂上待办清单
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、定义 SubAgent 并交给主 Agent 委派
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、量化委派的隔离效果：子 Agent 的上下文压缩
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、把中间结果写进虚拟文件而非堆在对话里
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、换成自己的长程任务：论文整理 + 自定义翻译子 Agent
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、三层取舍：什么时候用 deepagents、什么时候不用
---

## 能力目标

用一个入口函数搭出能稳定跑完十几步以上任务的智能体：它会先写一份待办清单再开工并逐条更新状态、把耗上下文的子任务委派给独立子智能体只收回精炼结果、把中间数据写进虚拟文件而不是一直堆在对话里。换成你自己的长链路任务时，只换工具、子智能体、任务描述三样，机制本身一行不改。

## 前置

- Python ≥ 3.11。
- 已能用 `create_agent` 与中间件挂载（见 building-tool-calling-agent、writing-agent-middleware）——这套脚手架的本质就是 `create_agent` 加一组预装好的中间件，理解中间件才看得懂它自动装配了什么。
- 需要可用的模型凭证与可访问模型服务的网络。

## 实操流程

1. 安装并核对接口。这个包处于 pre-1.0 阶段，装完先把版本、入口、内置工具名、子智能体字段一次性打出来核对，再动手写代码：

   ```bash
   .venv/bin/pip install deepagents
   ```

   ```python
   import deepagents
   print('version:', deepagents.__version__)
   from deepagents import create_deep_agent, FilesystemMiddleware
   from deepagents.middleware.subagents import SubAgent
   from langchain.agents.middleware import TodoListMiddleware
   ```

   核对结果给出三个贯穿全流程的事实：规划用 `write_todos`、虚拟文件系统用 `ls` / `read_file` / `write_file` / `edit_file`、委派用 `task`；规划机制复用的就是框架内置的待办清单中间件；定义子智能体只需 `name`、`description`、`system_prompt` 三个字符串字段。

2. 搭最小可运行版本。入参与普通 Agent 高度一致，但**模型必须显式传**（不传的默认值已弃用）：

   ```python
   # step2_deep_agent_min.py
   from deepagents import create_deep_agent
   from langchain_deepseek import ChatDeepSeek

   agent = create_deep_agent(
       model=ChatDeepSeek(model="deepseek-chat"),
       tools=[search_market_info],
       system_prompt="你是一个市场研究助手。",
   )
   print(type(agent).__name__)
   print(agent.get_graph().nodes)
   ```

   ```bash
   .venv/bin/python step2_deep_agent_min.py
   ```

   返回类型仍是 `CompiledStateGraph`，`invoke` / `stream` 用法不变。打印图节点能直接看到自动挂上去的中间件节点——这是确认三大机制是否装配到位最快的方式。

3. 跑一个多步任务触发规划机制，并**把递归上限设大**：

   ```python
   # step3_write_todos.py
   task = ("请帮我调研新能源汽车电池市场 4 个维度：主要厂商及市占率、核心技术路线、"
           "市场规模预测、主要风险因素，最后整合成简报。")

   for chunk in agent.stream({"messages": [{"role": "user", "content": task}]},
                             config={"recursion_limit": 100}):
       if "todos" in chunk:
           print(chunk["todos"])
   ```

   ```bash
   .venv/bin/python step3_write_todos.py
   ```

   预期行为：Agent 拿到任务立刻调用 `write_todos` 拆出一份清单（首条置为进行中、其余待办），执行中动态细化并多次回调更新，每条走「待办 → 进行中 → 已完成」三态，最终全部完成。清单状态从 `chunk["todos"]` 直接读得到，不需要额外挂钩子。

4. 定义子智能体并交给主智能体委派，把耗上下文的专项活隔离出去：

   ```python
   # step4_task_delegate.py
   company_analyst = {
       "name": "company_analyst",
       "description": "专门分析电池厂商的市场地位",
       "system_prompt": "你是电池行业公司分析专家……",
   }

   agent = create_deep_agent(
       model=ChatDeepSeek(model="deepseek-chat"),
       tools=[search_market_info],
       system_prompt="你是市场研究总协调员，把专业子任务委派给对应的分析师。",
       subagents=[company_analyst, tech_analyst],
   )
   ```

   委派工具的参数字段是 `subagent_type`（不是直觉上的名字类字段），取值必须匹配定义时的 `name`；另一个字段是任务描述，主智能体会在委派时把上下文与预期输出格式一次给足，子智能体不必回头要信息。委派工具的描述会动态注入当前可用的子智能体列表，所以主智能体运行时就知道自己手底下有谁可以差遣。

5. 让 Agent 把中间结果写进虚拟文件而不是堆在对话里——任务描述里直接要求它这么做即可：

   ```python
   # step5_virtual_fs.py
   task = ("请分别调研三个话题，每个话题的调研结果分别写入一个 markdown 文件，"
           "最后列出目录并读取其中一个文件验证。")
   ```

   Agent 会自主决定何时写、写什么、何时读回，开发者不写任何文件调度逻辑。默认后端下虚拟文件随会话消亡，适合单次任务内暂存；需要跨会话持久保存要换持久化后端。

6. 换成你自己的长链路任务时只改三样——工具、子智能体、任务描述：

   ```python
   # step7_reuse_custom.py
   translator = {
       "name": "translator",
       "description": "把英文论文摘要翻译成中文，并用无序列表提炼关键术语",
       "system_prompt": "你是一名 AI 论文翻译专家……",
   }
   agent = create_deep_agent(
       model=ChatDeepSeek(model="deepseek-chat"),
       tools=[fetch_paper],
       system_prompt="你是论文整理助手……",
       subagents=[translator],
   )
   ```

7. 动手前先按两个维度选层——**步骤数是否 ≥3、是否需要规划或委派或文件暂存**：

   | 任务形态 | 选哪层 | 原因 |
   | --- | --- | --- |
   | 只调一两个工具的简单问答 | `create_agent`、不挂中间件 | 最轻，不需要额外机制 |
   | 只要限流、日志等部分横切能力 | `create_agent` + 手选中间件 | 要定制钩子但不要全套机制 |
   | 三步以上、怕遗忘怕上下文撑爆 | `create_deep_agent` | 三大机制全自动装配 |
   | 需要条件分支、并行、特殊拓扑 | 裸编排引擎手写计算图 | 只有它能完全控制图结构 |

   这套脚手架的适用面比「深度调研」这个印象要宽：代码审查、论文写作、多源汇总，凡是需要这三大机制的任务都能套。

## 校验回路

1. **规划**：跑一个 ≥3 步的任务，确认调用了 `write_todos`、清单从待办逐步走到全部已完成。
2. **委派**：确认委派工具至少被调用一次、且 `subagent_type` 指向你定义的子智能体名字。
3. **虚拟文件**：确认 Agent 用写文件工具存了中间结果、并能用列目录与读文件取回。
4. **隔离效果**（可选量化）：比较子智能体处理的原始数据字符数与主智能体收到的委派结果字符数。实测一次是 685 字符原始数据换回 185 字符摘要、压缩约 3.7 倍，且原始数据完全不进主智能体的消息历史——这才是委派防上下文膨胀的根本。

## 常见陷阱

- **不改递归上限就跑长任务**：编排引擎默认上限只有 25，而一个七步调研任务实测触发了五十多次图迭代，会直接抛 `GraphRecursionError`。长任务显式设 `config={"recursion_limit": 100}`，一般给 50 到 100。第一次跑必踩。
- **依赖模型参数的默认值**：不传模型的默认值已弃用，必须显式传入模型实例。
- **委派参数名按直觉写**：委派工具的子智能体字段是 `subagent_type`，写成名字类字段会匹配不上；取值必须与定义时的 `name` 完全一致。
- **以为它是一个全新运行时**：它没有引入新运行时，底层还是同一套计算图，等价于普通 Agent 加上待办清单、虚拟文件系统、子智能体委派、工具调用标准化这几个中间件的预装组合。代价是依赖包略大。想只要其中一两项能力时，手动挑装反而更合适。
- **指望内置的代码执行工具直接可用**：它只在沙箱后端下可用，默认后端调用会返回错误。
- **按接口名写死代码**：pre-1.0 阶段工具名与参数名可能调整。落地时以当时的官方接口参考核对一遍，把功夫下在三大机制的设计意图上而不是具体名字上。
