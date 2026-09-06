---
concept: thread-id-isolation
one_liner: 会话标识是存档的命名空间，同一个智能体实例配不同标识即不同用户的独立记忆，互不串台
stage_span: [stage-2]
prerequisites: [checkpointer-persistence]
related: [state-snapshot-inspection, human-in-the-loop-interrupt]
applications: [human-in-the-loop-interrupt, time-travel-replay, business-decoupling-reuse-pattern]
sources:
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#五、thread_id 隔离：多用户记忆互不串台
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、换 thread_id=u2，验证不记得 A1001
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#2、交叉提问验证不串台
  - experiments/langchain/stage-2-experiment/case-5-human-in-the-loop/handbook.md#1、invoke 返回含 __interrupt__，而不是把异常抛给调用方
---

## 是什么

真实产品同时服务成千上万用户，必须保证 A 用户的记忆绝不串到 B 用户。承担这件事的是会话标识（`thread_id`）：它是存档的**命名空间**——存储器内部以它为键存储各自独立的消息列表，键不同则存储空间完全隔离。

它同时也是"暂停—续跑"的定位锚：人工审批场景里，续跑必须在同一个会话标识下进行，框架靠它找回暂停点的存档。

## 怎么用

同一个智能体实例，靠调用配置里的标识区分会话：

```python
config_u1 = {"configurable": {"thread_id": "u1"}}    # 已经知道 A1001
config_u2 = {"configurable": {"thread_id": "u2"}}    # 全新会话

agent.invoke({"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]}, config_u2)
```

实测输出：

```
=== 换 thread_id=u2，全新会话，隔离验证 ===
用户(u2): 我刚才说的订单号是什么？
Agent(u2): 您刚才没有提供订单号哦，请问您的订单号是多少？
[PASS] 隔离验证通过：u2 不知道 A1001，两会话记忆互不串台
```

生产里的标准写法是直接用用户标识：

```python
config = {"configurable": {"thread_id": str(user.id)}}
```

## 关键细节与参数

- **一个智能体实例承载无限会话**：不需要为每个用户创建一个实例，同一个实例配不同标识就是不同用户的独立会话。
- 标识可以是任意字符串——用户 ID、邮箱、会话令牌都行，只要保证"同一个会话用同一个值、不同会话用不同值"。
- 交叉验证实测：两个会话分别存入不同城市与订单号后交叉提问，各自准确答出自己的信息，谁也不知道对方的；两个会话存档各 6 条消息、会话数为 2。
- 隔离语义与业务领域无关：把对话场景整体换掉（从查订单换成多轮订票），隔离行为原样成立。
- 审批场景下，暂停与续跑必须使用同一个标识；换标识重跑等于开一条全新的审批链路。

## 常见陷阱

- **为每个用户新建智能体实例**：没有必要，且浪费资源；隔离由标识提供，不由实例提供。
- **用固定标识服务多用户**：所有用户会共享同一份存档、记忆互相串台，这是最危险的误用。
- **续跑时换了标识**：审批续跑找不到暂停点的存档，等同于开了一条新链路，原来的暂停永远悬着。
