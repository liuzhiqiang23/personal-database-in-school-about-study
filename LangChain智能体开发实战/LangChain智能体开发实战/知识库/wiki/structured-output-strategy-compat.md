---
concept: structured-output-strategy-compat
one_liner: 结构化输出有两条实现路线——工具调用兜底与服务商原生端点，服务商不支持原生端点时必须显式退回工具调用路线
stage_span: [stage-2]
prerequisites: [structured-output-response-format, deepseek-provider-integration]
related: [pydantic-schema-design, retrieval-grader]
applications: [retrieval-grader]
sources:
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、三种写法对比与 DeepSeek 实测
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、两种策略的底层机制与兼容性矩阵
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 GradeDocuments + with_structured_output 创建 Grader
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#4、迁移前置假设清单
---

## 是什么

"让模型输出符合数据模型的结果"有两种手段，框架把它们抽象成可插拔的策略：

- **工具调用兜底（ToolStrategy）**：把数据模型的字段封装成一个"工具"的参数，让模型以调用工具的方式"填写"这些字段，框架再从工具调用内容里提取参数并做校验。适用面最广——任何支持工具调用的模型都能用。
- **服务商原生（ProviderStrategy）**：直接调用服务商自家的结构化输出端点，让服务商在接口层面保证返回符合数据模型。约束更直接、更可靠，但前提是该服务商提供了这个端点。

这个差异不是实现细节，而是一条真实的兼容性边界：选错策略会直接报 400 错误。

## 怎么用

组装智能体时的三种写法：

```python
response_format=ReviewAnalysis                    # 写法 1：直接传数据模型，框架自动选策略
response_format=ToolStrategy(ReviewAnalysis)      # 写法 2：显式工具调用兜底
response_format=ProviderStrategy(ReviewAnalysis)  # 写法 3：显式服务商原生
```

在直接对模型使用结构化输出（不经智能体）的场景里，同一条边界表现为方法参数：

```python
# 默认走服务商原生模式；服务商不支持时必须显式指定工具调用
grader = llm.with_structured_output(GradeDocuments, method='function_calling')
```

## 关键细节与参数

- 实测结果：写法 1 与写法 2 结果完全一致——直接传数据模型时框架自动选策略，对该服务商自动降级到工具调用兜底。
- 写法 3 在该服务商上报 `BadRequestError 400: "This response_format type is unavailable now"`，因为它没有提供原生结构化输出端点。这是预期内的兼容性边界，不是代码 bug。
- 同一条边界的另一种表现：`with_structured_output` 默认走原生模式，该服务商上会报同样的 400 错误，解法是显式传 `method='function_calling'`。国产模型遇到 `with_structured_output` 报 400，统一用这个参数解决。
- 兼容性矩阵：

| Provider | ToolStrategy | ProviderStrategy | 选型建议 |
|----------|:-:|:-:|---------|
| DeepSeek deepseek-chat | 支持 | 不支持 | 必须用 ToolStrategy |
| OpenAI GPT-4o | 支持 | 支持 | 两者都可，ProviderStrategy 更稳 |
| Anthropic Claude 3.5 | 支持 | 支持 | 两者都可，ProviderStrategy 更稳 |
| 本地 Ollama 模型 | 支持 | 一般不支持 | 用 ToolStrategy |

- 策略差异被封装在模型节点内部，对调用方透明：三种写法编译出的图节点结构相同。

## 常见陷阱

- **为了用原生策略去换模型**：正确做法相反——遇到"某服务商不支持某策略"时退回到兼容面更广的工具调用兜底，而不是为了策略换模型。
- **把 400 报错当成代码写错**：错误信息 `This response_format type is unavailable now` 指的是服务商端点缺失，检查代码没有意义，改策略才有效。
- **换服务商后不复核策略**：策略是可插拔的，换服务商往往只需改一个参数，但**必须先核对该服务商支持哪条路线**，否则线上才暴露 400。
- **在评分器这类小模型调用上遗漏该参数**：检索质量门控里的评分器同样吃这条边界，漏掉 `method='function_calling'` 会让整条评分链路报 400。
