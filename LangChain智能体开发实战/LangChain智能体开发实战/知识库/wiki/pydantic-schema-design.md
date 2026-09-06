---
concept: pydantic-schema-design
one_liner: 用 Pydantic 数据模型声明想要的结构，字段描述引导模型填值、类型校验兜底拦截，两层叠加才让结构化结果可信赖
stage_span: [stage-2]
prerequisites: [langchain-package-stack]
related: [structured-output-response-format, retrieval-grader]
applications: [structured-output-response-format, retrieval-grader, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#2、定义 Pydantic schema：ReviewAnalysis 与 OrderInfo
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#3、结构化为什么「可信赖」：校验机制的两层保护
  - experiments/langchain/stage-2-experiment/case-2-structured-output/handbook.md#1、可替换的部分（换成你的业务）
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 GradeDocuments + with_structured_output 创建 Grader
---

## 是什么

数据模型是结构化输出的"需求说明书"：继承 `BaseModel` 定义一个类，用类型注解声明每个字段是什么类型，用 `Field(description=...)` 说明每个字段该填什么。Pydantic 会在实例化时自动校验数据是否合规。

这里有一个容易被忽略的要点：`Field` 里的描述文字**不只是给人看的注释**，它会被框架传给模型，直接引导模型"这个字段该填什么"。也就是说，提示词工程的一部分被下沉到了数据模型层——字段描述写得越准确，抽取质量越高。

## 怎么用

定义模型（字段名、类型、描述三件套）：

```python
from pydantic import BaseModel, Field

class ReviewAnalysis(BaseModel):
    """客户评论分析结果"""
    sentiment: str = Field(description="情感极性：positive / negative / neutral")
    category: str = Field(description="问题类别：logistics / product_quality / refund 等")
    urgency: int = Field(description="紧急程度，1-5 的整数，5 最紧急")
```

模型可以很小——只承载一个二元判断也是合法且常用的形态：

```python
class GradeDocuments(BaseModel):
    """对检索到的文档与问题相关性的二元评分"""
    binary_score: str = Field(description="文档是否与问题相关，回答 'yes' 或 'no'")
```

换业务只换字段，规范不变：

```python
class ResumeInfo(BaseModel):
    """简历信息抽取结果"""
    name: str = Field(description="候选人姓名")
    skills: list[str] = Field(description="技能列表，如 ['Python', 'SQL']")
    years: int = Field(description="工作年限，整数")
```

## 关键细节与参数

- Pydantic 随主框架一并装好，无需额外安装；实测走的是 Pydantic v2 的字段校验。
- **两层保护机制**：
  - 第一层是字段描述引导——实测里评论明说"10 级紧急"，模型仍填入 `urgency=5`，因为描述写了"1-5 的整数"。好的字段描述能在源头引导模型输出合法值。
  - 第二层是强制校验——手动构造越界实例时 Pydantic 立刻抛 `ValidationError`，错误信息精确指出问题（`urgency: Value error, urgency 必须在 1-5 之间，收到 10`）。即便模型罕见地填了越界值，框架在提取参数后会立即校验、不合规就拦下。
- 字段类型可用 `str` / `int` / `float` / `bool`，也可用列表与嵌套子模型。
- 要严格锁死某字段的取值，在描述里明确列出可选项，或用字面量类型注解锁死——这是生产中提高一致性的常用手段。

## 常见陷阱

- **只写字段名不写描述**：模型缺少填值指引，抽取质量与一致性都会下降。
- **没加取值约束就期待固定枚举**：实测里未加枚举约束的分类字段，模型填进了中文值而非预期的英文枚举。要固定取值必须显式约束。
- **把校验通过等同于语义正确**：类型校验只保证格式合规，语义是否恰当仍取决于模型判断与字段描述质量。
