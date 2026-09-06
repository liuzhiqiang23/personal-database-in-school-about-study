---
concept: human-in-the-loop-interrupt
one_liner: 在危险工具执行真正动作之前调用中断，图就地暂停并抛出待审批信息，人工用续跑指令把决定传回工具
stage_span: [stage-2]
prerequisites: [checkpointer-persistence, tool-function-contract, thread-id-isolation]
related: [interrupt-resume-replay, hitl-iron-rules, hitl-implementation-routes, middleware-flow-control]
applications: [interrupt-resume-replay, hitl-iron-rules, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#一、开篇：从「Agent 自作主张」到「危险动作前先让人点头」
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、定义 mock 危险工具 refund_order（在工具内调 interrupt）
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、invoke 返回含 __interrupt__，而不是把异常抛给调用方
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、两种视角提取待审批信息
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、两路径对比：唯一的变量是 resume 的值
---

## 是什么

智能体自主执行工具，"自主"有时正是风险所在：退款、转账、删除数据、对外发邮件，这类动作执行了就收不回来。把不可逆的决定权完全交给模型，在生产系统里不可接受。

人在回路的机制是在危险动作**之前**让图停下来，把"我打算做这件事，批不批"抛给人工，等人点头再继续；人若否决，动作不执行。三个核心对象：

- **中断（`interrupt`）**：在工具内部调用，让图执行到此处暂停，并把需要人工过目的信息抛出来。它是闸门本身。
- **续跑指令（`Command(resume=...)`）**：人工做完决定后，把审批结果回传给暂停的图，让它从断点继续。它是钥匙。
- **检查点存储器**：图暂停时状态必须有地方存档，否则审批期间状态就丢了。**没有它，中断无法暂停**——这是硬前提。

中断是一个函数对象（来自图执行引擎的类型模块），不是异常类；虽然它内部靠抛异常实现暂停，写工具代码时当普通函数调用即可。

## 怎么用

危险工具里，把中断放在真正动作之前：

```python
from langgraph.types import interrupt
from langchain.tools import tool

@tool
def refund_order(order_id: str, amount: float) -> str:
    """给指定订单退款。order_id 为订单号，amount 为退款金额（元）。"""
    approval = interrupt({
        "action": "refund_order",
        "order_id": order_id,
        "amount": amount,
    })
    # 下面这段只有人工续跑之后才会真正跑到
    if approval == "approve":
        return f"退款已执行：{order_id} ¥{amount} 成功"
    else:
        return f"退款已拒绝：{order_id} ¥{amount} 被驳回"
```

触发暂停并读待审批信息：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "立即给订单 A1001 退款 299 元"}]},
    config={"configurable": {"thread_id": "refund-001"}},
)
# result 形如：
# {'messages': [...],
#  '__interrupt__': [Interrupt(value={'action': 'refund_order', 'order_id': 'A1001', 'amount': 299.0}, ...)]}
```

续跑（两条路径唯一的差别就是这个值）：

```python
from langgraph.types import Command

agent.invoke(Command(resume="approve"), config={"configurable": {"thread_id": "refund-001"}})
agent.invoke(Command(resume="reject"),  config={"configurable": {"thread_id": "refund-002"}})
```

## 关键细节与参数

- **调用本身正常返回，不把异常抛给调用方**：判断是否停在审批点，看返回字典里有没有 `__interrupt__` 键即可。
- **中断抛出的内容完全由开发者自定义**：审批界面要展示什么，就往那个字典里塞什么（实测里还携带了风险等级这类业务字段）。
- **中断的返回值就是续跑时传入的值**，工具内据此判断走批准还是拒绝分支。这条"人工决定 → 续跑值 → 中断返回值 → 工具分支"的传递链，是信息回传的全部机制。
- **续跑值不限于批准/拒绝两个字符串**：可以是任意值，包括携带审批意见的对象、条件参数，全看工具内怎么消费它。
- 暂停状态可从两处查：返回值的 `__interrupt__`，以及状态快照的 `tasks[0].interrupts`，两者内容一致；此时状态快照的 `next` 为 `('tools',)`。
- 待审批信息有两个提取视角：中断抛出的自定义字典（精炼结论，最常用），以及模型消息里的工具调用链（模型完整决策上下文，可追溯它为什么要这么做）。
- **暂停与续跑必须在同一个会话标识下**，续跑靠它找回暂停点存档。
- 两条路径对比：图结构、工具定义、存储器完全相同，唯一变量是续跑传的值。
- 机制与业务动作无关：把危险工具从退款换成转账，三件套一行没改，实测 5000 元转账批准执行、20000 元高额转账被驳回。

## 常见陷阱

- **系统提示词没写死执行顺序**：实测中模型有时会自作主张先查一遍订单再思考，迟迟不调危险工具，导致中断压根没触发。稳妥做法是提示词写清"用户要求退款时必须立即调用退款工具，不需要先查询"，用户消息也用明确措辞而非含糊说法。
- **把真正的动作写在中断之前**：续跑时中断之前的代码会重跑一遍（见 interrupt-resume-replay），不可逆动作必须放在中断之后。
- **忘了挂检查点存储器**：没有存档，中断无法暂停，整套审批形同虚设。
