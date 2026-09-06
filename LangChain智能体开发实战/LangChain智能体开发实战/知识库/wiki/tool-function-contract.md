---
concept: tool-function-contract
one_liner: 工具就是带类型注解与 docstring 的普通函数，docstring 是框架硬约束、也是模型判断何时调用它的唯一依据
stage_span: [stage-2]
prerequisites: [create-agent-entry]
related: [tool-calling-loop, agentic-rag-loop, business-decoupling-reuse-pattern]
applications: [tool-calling-loop, parallel-tool-calls, agentic-rag-loop, human-in-the-loop-interrupt]
sources:
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#2、定义业务工具集
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#3、docstring 为什么不是可选项
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#1、用 @tool 把检索器包成 search_docs 工具
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#docstring 决定工具调用：问知识库之外的问题，Agent 怎么反应
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、定义 mock 危险工具 refund_order（在工具内调 interrupt）
---

## 是什么

工具是智能体的能力单元。在 LangChain v1 里，一个工具就是一个满足三条规范的普通 Python 函数：**带类型注解、带 docstring、返回字符串**。函数体内可以是任意逻辑——查数据库、调 REST 接口、读文件、执行向量检索——只要最终返回字符串。

三条规范里 docstring 的地位特殊。很多 Python 教程把 docstring 描述成"良好习惯但非必须"，在智能体体系里这个判断不成立：框架会把所有工具的 docstring 拼成一份能力清单交给模型，模型据此判断"用户这个问题该调哪个工具"。docstring 不是写给人看的注释，而是直接参与模型推理的元数据——它的措辞就是智能体选工具的判断依据。

## 怎么用

普通函数写法（直接放进工具列表即可）：

```python
def query_order(order_id: str) -> str:
    """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
    mock = {"A1001": "已发货，预计明天到达"}
    return mock.get(order_id, "未找到该订单")

def calc_shipping_fee(origin: str, destination: str, weight_kg: float) -> str:
    """计算运费。origin 出发城市，destination 目的城市，weight_kg 包裹重量（公斤）。"""
    fee = round(10 + weight_kg * 3, 1)
    return f"从{origin}到{destination}，重量 {weight_kg} kg，预估运费 {fee} 元"
```

装饰器写法（需要工具对象特性时用，例如把检索器包成工具、或在工具内触发人工审批）：

```python
from langchain_core.tools import tool

@tool
def search_docs(query: str) -> str:
    """搜索电商平台知识库，获取关于订单、退款、物流、账号、支付、售后等问题的答案。"""
    docs = retriever.invoke(query)
    return "\n\n".join(f"[来源: {d.metadata['source']}]\n{d.page_content}" for d in docs)
```

装饰后的对象类型是 `langchain_core.tools.structured.StructuredTool`。

## 关键细节与参数

- **docstring 缺失是编译期错误**：无 docstring 的函数会让组装阶段直接抛 `ValueError: Function must have a docstring if description not provided.`，报错发生在 `create_agent()` 而不是 `agent.invoke()`——属于快速失败设计，问题在编码阶段就暴露。
- 报错信息点明两条出路：给函数写 docstring（最简洁），或在创建工具时显式传 `description` 参数，二者本质相同。
- **参数必须带类型注解**：类型注解决定模型填参数时的类型约束。
- **docstring 措辞直接改变行为**：写"查询订单状态"还是"订单查询工具"，会让模型在边界场景下做出不同的调用判断。实测里描述贴近领域的检索工具，对完全无关的问题（问天气、写诗）工具调用次数为 0，对沾边但界外的问题（问某公司市值）则会误触一次调用。
- 工具返回 mock 数据不影响机制：循环的教学与调试核心是模型如何自主决定调用，工具内部查真库还是返回固定字符串对循环没有影响。

## 常见陷阱

- **把 docstring 当可选注释**：漏写会让程序根本启动不了，这是最常见的入门障碍。
- **写模糊的 docstring**：描述越含糊，边界问题误触工具越多；描述越贴合实际领域，工具选择越精准。
- **指望"检索未命中"会报错**：工具返回不相关内容时智能体不会崩溃，它会退回到用模型自身知识兜底作答——这个兜底不可控，可能给出知识库里根本没有的内容。要把兜底变得可控，需要额外的质量门控（见 retrieval-grader）。
- **迁移业务时改错了地方**：换业务只需换函数名、参数、docstring 与函数体，"带类型注解 + 带 docstring + 返回字符串"这三条规范一字不动。
