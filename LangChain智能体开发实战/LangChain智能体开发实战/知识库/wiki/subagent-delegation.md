---
concept: subagent-delegation
one_liner: 把耗上下文的子任务委派给独立子智能体，主智能体只收精炼结果，原始数据根本不进主上下文
stage_span: [stage-2]
prerequisites: [deepagents-harness, system-prompt-boundary]
related: [todo-planning-mechanism, virtual-filesystem-context-engineering, parallel-tool-calls]
applications: [business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#五、委派机制：定义子 Agent 并用 task 委派
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、定义 SubAgent 并交给主 Agent 委派
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#2、量化委派的隔离效果：子 Agent 的上下文压缩
  - experiments/langchain/stage-2-experiment/case-8-deepagents-harness/handbook.md#1、换成自己的长程任务：论文整理 + 自定义翻译子 Agent
---

## 是什么

委派机制解决的是"上下文越堆越满"。思路是分工：主智能体负责统筹，把具体的、耗上下文的子任务委派给独立的子智能体去做。子智能体有自己独立的上下文，干完活只把**最终结果**交回主智能体，中间过程不污染主上下文。

关键在于委派工具的返回值就是子智能体的最终回复，而不是它的整个工作过程——这才是防止上下文膨胀的根本。

## 怎么用

子智能体是一个带类型标注的字典，只需填三个必填字段：

```python
company_analyst = {
    "name": "company_analyst",                       # 名字，委派时用它指认
    "description": "专门分析电池厂商的市场地位",        # 描述，告诉主智能体它能干什么
    "system_prompt": "你是电池行业公司分析专家……",     # 系统提示词，决定它怎么干
}

agent = create_deep_agent(
    model=ChatDeepSeek(model="deepseek-chat"),
    tools=[search_market_info],
    system_prompt="你是市场研究总协调员，把专业子任务委派给对应的分析师。",
    subagents=[company_analyst, tech_analyst],       # 注册子智能体
)
```

换业务只换这三个字段的内容：

```python
translator = {
    "name": "translator",
    "description": "把英文论文摘要翻译成中文，并用无序列表提炼关键术语",
    "system_prompt": "你是一名 AI 论文翻译专家……",
}
```

## 关键细节与参数

- **委派工具的参数名是 `subagent_type`**，不是直觉上的名字字段名；它的值必须匹配定义子智能体时的 `name`。委派工具的参数结构有两个字段——任务描述（含上下文与预期输出格式）与委派目标类型。
- **委派描述要携带完整上下文**：实测里描述字段写满了具体任务（包括要读的文件路径），而不是甩一句模糊指令让子智能体自己猜。主智能体在委派时就把必要信息一次给足，子智能体不必回头要。
- **可用子智能体列表是动态注入的**：委派工具的描述里会带上当前注册的子智能体，主智能体运行时就"知道"自己手底下有谁可以差遣，因此才会主动发起委派。
- **隔离效果实测量化**：子智能体处理的原始数据 685 字符（两段数据 348 + 337），主智能体实际收到的委派结果只有 185 字符（三句话精炼摘要含关键数字），压缩比 3.7 倍。那 685 字符根本不会出现在主智能体的消息历史里。
- **压缩比越高，子智能体的信息提炼能力越关键**，而提炼能力直接由它的系统提示词质量决定。
- 实测委派触发：一次运行里委派 2 次（分别给两个分析师），另一次综合运行委派 1 次；换成论文整理任务后同样正常委派给自定义的翻译子智能体。
- 验收判据：委派工具至少被调用一次，且委派目标指向自己定义的子智能体。

## 常见陷阱

- **把委派目标字段写成名字字段名**：参数名与直觉不符，写错会导致委派失败。
- **委派时只给一句模糊指令**：子智能体上下文独立、看不到主智能体的历史，信息不给足它就只能猜。
- **给子智能体写敷衍的系统提示词**：提炼质量直接决定压缩效果，写得差就等于把原始数据换个形式又搬回主上下文。
- **用委派处理必须共享上下文的任务**：委派的价值恰恰在隔离，需要主智能体逐步看到中间过程的任务不适合委派。
