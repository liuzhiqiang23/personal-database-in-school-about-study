---
concept: hitl-implementation-routes
one_liner: 审批有手写中断与声明式中间件两条等价路线，续跑传参格式不同，实操二选一即可
stage_span: [stage-2]
prerequisites: [human-in-the-loop-interrupt, middleware-hooks]
related: [builtin-middleware-catalog, hitl-iron-rules]
applications: []
sources:
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#2、两种实现路线：手写 interrupt 与 HumanInTheLoopMiddleware
  - experiments/langchain/stage-2-experiment/case-3-middleware-system/handbook.md#2、其他常用内置 middleware 一览
---

## 是什么

框架提供两条等价的人在回路实现路线，跑出的审批效果相同，但代码形态与续跑格式不同：

- **手写中断**：在工具内部直接调用中断。控制最精细，审批界面要展示的数据完全由工具自定义；也更直观地暴露了中断的工作机制，适合用来理解原理。
- **声明式中间件**：用内置的人在回路中间件声明哪些工具需要审批，拦截逻辑由中间件统一处理，工具本体代码里看不到中断，更干净。

实操中二选一即可，不必都实现。

## 怎么用

两条路线的续跑传参格式不同，这是最容易踩的差异点：

```python
# 路线 A（手写 interrupt）：resume 传普通字符串
Command(resume="approve")

# 路线 B（HumanInTheLoopMiddleware）：resume 必须传 dict，含 decisions 列表
Command(resume={"decisions": [{"type": "approve"}]})
```

中间件路线的挂载走的是标准中间件声明方式（导入自中间件模块，放进中间件列表）。

## 关键细节与参数

- **抛出的待审批数据结构不同**：手写路线的中断值就是工具自定义的字典；中间件路线的中断值包含 `action_requests` 与 `review_configs` 两个字段。
- **中间件路线支持更丰富的决策类型**：`approve` / `edit` / `reject` / `respond` 四种，手写路线的决策语义完全由工具内的分支逻辑定义。
- 两条路线都依赖同一个硬前提：检查点存储器。
- 两条路线的审批效果实测一致——同一个退款审批，路线 A 用字符串续跑成功，路线 B 用决策字典续跑同样成功。

## 常见陷阱

- **把两条路线的续跑格式混用**：给中间件路线误传字符串会直接报 `TypeError: string indices must be integers`——根因是中间件内部按下标方式取决策值，要求续跑值必须是字典。
- **按手写路线的假设去读中间件路线的中断值**：字段结构不同，取 `action` / `amount` 这类自定义键会取空。
- **同时上两条路线**：没有必要，且两套暂停语义叠加会让审批链路难以推理。
