# B 部分 · 课件逐节全量（第 1-5 章）

本部分按学习顺序精炼第 1-5 章课件，每章含「本质 / 关键知识点 / 关键命令与代码 / 关键坑」。

## 第1章 LangChain v1 从零到一跑通实操手册

### 本质
在一台机器上从零跑通 LangChain v1 的最小闭环：核对 Python 版本、建立隔离虚拟环境、安装分层生态包、配置大模型凭证，最后运行官方 create_agent 最小示例，亲眼看到一次完整的「工具调用循环」闭环。

### 关键知识点
- **LangChain 定位**：面向智能体工程（agent engineering）的开源框架，目标是让模型在一个循环中自主调用外部工具、读取结果、再决定下一步，直到完成任务。官方文档 docs.langchain.com，代码仓库 github.com/langchain-ai/langchain，当前版本基线 langchain-core 1.4.0。
- **Python 版本硬性要求**：官方 install 文档写明 Requires Python 3.10+，这是所有步骤前提。macOS 系统自带 /usr/bin/python3 往往是 3.9.6（不达标），需改用 Homebrew 等安装的更高版本解释器（python3.13、3.12、3.11 任选 ≥3.10 即可）。
- **虚拟环境作用**：把项目依赖与系统全局隔离，避免包版本互相污染。必须用满足版本要求的解释器创建，不能用不达标的默认 python3。
- **分层包结构**：主框架、编排运行时、各家模型提供方集成包是独立发布的 PyPI 包，按需安装、独立迭代。核心三件套 + DeepSeek 提供方包：langchain（主框架）、langgraph（编排运行时，负责状态与循环调度）、langchain-deepseek（DeepSeek 集成包）。
- **依赖连带**：装 langchain-deepseek 会连带拉入 langchain-openai 和 openai——DeepSeek 接口走 OpenAI 兼容协议，其集成包复用了 OpenAI 客户端底层实现。
- **凭证安全原则**：DeepSeek 通过环境变量 DEEPSEEK_API_KEY 读凭证；全程不在终端回显明文、不让 Key 出现在截图，验证时只打印前 3 个字符 + 长度脱敏。
- **工具调用循环**：四条消息流实证核心闭环——HumanMessage（用户问题）→ AIMessage 带 tool_calls（模型决定调工具，文本为空、关键信息在 tool_calls 字段）→ ToolMessage（工具返回结果）→ AIMessage（最终回答，复用工具措辞说明结果真实参与了生成）。
- **模型选型**：必须用支持 tool calling 的 deepseek-chat，不能用 deepseek-reasoner（DeepSeek 官方文档明确 deepseek-reasoner 不支持工具调用与结构化输出，误用则模型不会发出 tool_calls，循环走不通）。model 参数用「提供方:模型名」字符串格式（如 "deepseek:deepseek-chat"）。

### 关键命令与代码
环境基线检测：
```bash
echo "OS: $(sw_vers -productName) $(sw_vers -productVersion) ($(uname -m))"
echo "系统 python3 = $(python3 --version)"
echo "brew python3.13 = $(/opt/homebrew/bin/python3.13 --version)"
echo "uv = $(uv --version)"
```
创建并激活虚拟环境（必须指定 python3.13）：
```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --quiet --upgrade pip
```
一条命令装齐分层生态：
```bash
pip install -U langchain langgraph langchain-deepseek
```
核验六个包版本（统一用 importlib.metadata，不用 __version__）：
```bash
python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek','langchain-openai','openai']]"
```
配置 DeepSeek API Key（不回显明文）：
```bash
export DEEPSEEK_API_KEY=$(python -c "import yaml;print(yaml.safe_load(open('/path/to/credentials.yaml'))['api_keys']['deepseek']['key'])")
echo "DEEPSEEK_API_KEY = ${DEEPSEEK_API_KEY:0:3}***(长度 ${#DEEPSEEK_API_KEY},已脱敏)"
```
官方 create_agent 最小示例（get_weather 的 docstring 至关重要）：
```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
```
运行：python create_agent_demo.py

### 关键坑/注意
- **macOS 系统 Python 常偏旧**：建虚拟环境前务必核对版本，必要时显式指定高版本解释器，否则装包会因版本约束失败。
- **Ignoring invalid distribution -pip 警告**：外置 SSD 上先前安装中断留下的以 ~ 为前缀的临时残留目录，无害、不阻塞安装，可忽略或一行清理：`find ".venv/lib/python3.13/site-packages" -maxdepth 1 -name '~*' -exec rm -rf {} +`
- **查 langgraph 版本不能用 langgraph.__version__**：langgraph 顶层模块未定义 __version__ 属性，会报 AttributeError。必须用 importlib.metadata.version("langgraph")。
- **工具调用循环 Demo 必须用 deepseek-chat**：而非 deepseek-reasoner，否则循环走不通。
- 跨平台对照：若系统 Python ≥3.10 可直接 python3 -m venv .venv；Windows 激活命令为 .venv\Scripts\activate。
- 本章仅演示非流式 invoke，stream / checkpointer / Middleware / response_format / StateGraph 等内容后文展开。

---

## 第2章 LangChain create_agent 智能体核心从零到一跑通实操手册

### 本质
用一个「订单运营助手」案例讲透 Agent 的工具调用循环：定义带 docstring 的业务工具 → 用 create_agent 组装 → invoke/stream 运行并逐条拆解消息流 → 验证多工具并行协作 → 换工具即换业务，并给出迁移到自己业务的指南。

### 关键知识点
- **Agent 与面向对象/过程的区别**：传统程序用 if/else 手写分发逻辑；Agent 中「调用哪个函数、何时调、调几次」由模型自己推理决定，开发者不写分发逻辑。
- **工具调用循环（四步）**：①推理（模型判断调哪个工具、传什么参数）→②调工具（框架执行函数）→③结果喂回（返回值重新交给模型）→④继续推理直到完成（要么再调工具，要么生成最终回答）。
- **三个关键对象**：工具函数 tool（带类型注解 + docstring 的普通 Python 函数，是能力单元）、create_agent（把「模型+工具+系统提示词」组装成可执行 Agent 的工厂函数）、消息流 messages（记录循环每一步痕迹，是观察原理的窗口）。
- **docstring 是硬约束而非可选项**：它是工具向模型暴露的「能力描述」，框架把所有工具的 docstring 拼成能力清单交给模型。漏写 docstring，create_agent 在组装阶段就报 ValueError: Function must have a docstring if description not provided.——这是快速失败设计，问题在编码阶段暴露而非线上运行。两条出路：给函数写 docstring，或创建工具时显式传 description 参数。
- **create_agent 返回 CompiledStateGraph**（来自 langgraph.graph.state）：它把「模型+工具+系统提示词」声明式配置编译成一张可执行的 LangGraph 图，因此天然拥有 invoke 和 stream 两种调用能力。
- **system_prompt 的职责边界**：控制模型「怎么说」，不控制「做什么」。决定调哪个工具的逻辑由工具 docstring + 用户问题共同决定，system_prompt 不参与这一层。
- **四种消息类型各司其职**：HumanMessage 输入，AIMessage 承载决策与最终回答，ToolMessage 承载工具结果。
- **AIMessage 可同时有 content 和 tool_calls**：模型能「边说话边行动」，两者不互斥。
- **结果路由机制**：ToolMessage 的 tool_call_id 等于 AIMessage 里 tool_calls[].id，当一个回合同时发起多个工具调用时靠它保证每条工具结果对应回正确的请求。
- **AIMessage.tool_calls 结构**：由字典组成的列表，每个字典含 name（工具名）、args（参数）、id（调用编号）三个字段。
- **Agent「信息驱动」本质**：参数不全时模型会追问而不瞎猜，遵循「不猜参数」原则。
- **并行工具调用（parallel function calling）**：deepseek-chat 支持。两个独立任务挂在同一条 AIMessage 里并行发起（消息总数 5 而非 6），而非顺序调用。
- **invoke vs stream**：invoke 返回 dict（result["messages"] 是跑完的完整消息列表），stream 返回生成器（每个 chunk 只含当前步骤的增量）。stream 的 chunk 数等于循环步数（3 个 chunk 对应 model→tools→model）。节点名是 model 不是 agent。
- **换工具即换业务**：只把新工具函数加进 tools=[] 列表，不改其他任何代码，create_agent 自动把新工具 docstring 注册进模型可调用范围。能力边界由工具列表定义。

### 关键命令与代码
```bash
source .venv/bin/activate
python -c "from importlib.metadata import version; [print(f'{p:20s} = {version(p)}') for p in ['langchain','langchain-core','langgraph','langchain-deepseek']]"
python --version
```
定义业务工具集（tools.py，每个函数带类型注解 + docstring + 返回字符串）：
```python
# tools.py
def query_order(order_id: str) -> str:
    """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
    mock = {"A1001": "已发货 · 预计明天到达"}
    return mock.get(order_id, "未找到该订单")

def track_shipping(order_id: str) -> str:
    """查询指定订单的最新物流轨迹。order_id 是订单编号。"""
    return "2026-05-30 08:00 上海转运中心 → 正在派送中"

def calc_shipping_fee(origin: str, destination: str, weight_kg: float) -> str:
    """计算运费。origin 出发城市，destination 目的城市，weight_kg 包裹重量（公斤）。"""
    fee = round(10 + weight_kg * 3, 1)  # mock：基础费 10 元 + 每公斤 3 元
    return f"从{origin}到{destination}，重量 {weight_kg} kg，预估运费 {fee} 元"

def query_inventory(product_id: str) -> str:
    """查询指定商品的库存数量。product_id 是商品编号，如 P001。"""
    return "库存充足 · 当前 358 件"
```
用 create_agent 组装（返回 CompiledStateGraph）：
```python
# agent_core.py
from langchain.agents import create_agent
from tools import query_order, track_shipping, calc_shipping_fee

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
)
print("agent 类型:", type(agent))
```
用 invoke 提问并遍历消息流：
```python
from langchain_core.messages import HumanMessage
result = agent.invoke({"messages": [HumanMessage(content="订单 A1001 是什么状态？")]})
for i, msg in enumerate(result["messages"]):
    print(f"  [{i}] {type(msg).__name__} → ...")
```
新增工具复用（只改 tools 列表）：
```python
from tools import query_order, track_shipping, calc_shipping_fee, query_inventory
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee, query_inventory],
    system_prompt="你是一个订单运营助手……",
)
```
迁移改写骨架（订单工具 → 天气工具）：
```python
# 改之前
def query_order(order_id: str) -> str:
    """查询指定订单的当前状态。order_id 是订单编号，如 A1001。"""
    mock = {"A1001": "已发货 · 预计明天到达"}
    return mock.get(order_id, "未找到该订单")

# 改之后
def query_weather(city: str) -> str:
    """查询指定城市的实时天气。city 是城市名，如 北京。"""
    resp = requests.get(f"https://your-weather-api/...?city={city}")  # 换成真实 API
    return resp.json()["summary"]  # 返回字符串
```

### 关键坑/注意
- **docstring 是硬约束**：漏写会在 create_agent() 组装阶段报 ValueError，程序根本启动不了。两条出路：写 docstring 或显式传 description。
- **参数必须给全**：否则模型遵循「不猜参数」原则会反追问，而非编造默认值。
- **节点名是 model 不是 agent**：解析 stream 事件时以此为准。
- **模型须支持工具调用**：换其他模型时需确认支持 function calling。
- 迁移自检三条：单工具验证、多工具串联验证（参数给全、工具调用总次数 ≥2）、换工具复用验证（加新工具不改其他代码）。

---

## 第3章 LangChain 结构化输出（structured-output）从零到一跑通实操手册

### 本质
让 Agent 不再返回自由文本，而是返回经过校验的结构化对象，下游程序可以直接 .字段名 取值。核心机制是给 create_agent 传入 response_format 参数，结果落在 result["structured_response"] key 里。用「客户评论分析」场景演示，并对比自由文本与结构化的差异、两种策略的选型。

### 关键知识点
- **问题背景**：自由文本回答对「人」友好、对「下游程序」不友好。结构化输出让 Agent 直接吐出校验过的对象，程序可立即用 .字段名 做计数、过滤、排序。
- **三个关键技术对象**：Pydantic schema（声明「结构化数据长什么样」）、response_format 参数（告诉框架按这个 schema 返回结构化结果）、structured_response（调用结果字典里的一个 key，校验过的结构化对象落在这里）。
- **Pydantic 基础用法**：继承 BaseModel 定义类、用类型注解声明字段，Pydantic 在实例化时自动校验数据合规。Field(description=...) 不只是给人看的注释，会被框架传给模型引导「这个字段该填什么」。
- **类型强制约束**：ReviewAnalysis.urgency 是 int、OrderInfo.amount 是 float——模型填进来的值会被强制转成声明的类型。
- **response_format 用策略类包装**：schema 不用裸传，主线用 ToolStrategy（工具调用策略），从 langchain.agents.structured_output 导入。
- **tools=[] 可为空**：结构化输出案例里 Agent 直接读评论文本按 schema 抽取，不需要额外工具。
- **返回结果的 key 设计**：开启结构化输出后 result 只有两个 key——messages 和 structured_response。结构化对象不混在消息里，单独放一个 key。
- **structured_response 是真正的 Python 对象**：类型是定义的 schema 类，可直接 .字段名 取值，IDE 能自动补全。
- **结构化可信赖的两层保护机制**：第一层 field description 引导（把提示词工程下沉到 schema 层）；第二层 Pydantic 强制校验（越界值被 ValidationError 拦截）。
- **自由文本 vs 结构化对比**：方案 A（不带 response_format）result keys 只有 messages、类型是 str、键名是模型自由发挥的中文「情感极性」、urgency 值是字符串「高」、需手动解析；方案 B（带 response_format）result keys 是 messages+structured_response、类型是 ReviewAnalysis、键名是 schema 锁定的 sentiment、urgency 是整数 5。结论：靠提示词让模型「输出 JSON」仍是类型不安全、键名不可控的字符串，LangChain v1 把「提示模型输出 JSON 再手动解析」的旧做法移除。
- **response_format 接受三种写法**：①直接传 schema 类（框架自动选策略）②显式传 ToolStrategy ③显式传 ProviderStrategy。写法 1 等价于写法 2（DeepSeek 下框架自动降级到 ToolStrategy）。
- **两种策略的本质区别**：ToolStrategy（工具调用兜底）把 schema 字段封装成「工具」的参数，让模型以「调用工具」方式「填写」字段，再从返回的工具调用内容提取参数做 Pydantic 校验——适用面广，任何支持工具调用的模型都能用；ProviderStrategy（provider 原生）直接调用 provider 自家的结构化输出 API（如 response_format=json_schema 端点）——约束更直接更可靠，但前提是该 provider 提供了这个端点。
- **兼容性矩阵**：DeepSeek deepseek-chat（ToolStrategy ✅ / ProviderStrategy ❌，必须用 ToolStrategy）；OpenAI GPT-4o（两者都可，ProviderStrategy 更稳）；Anthropic Claude 3.5（两者都可，ProviderStrategy 更稳）；本地 Ollama（ToolStrategy ✅ / ProviderStrategy 一般不支持）。DeepSeek 上 ProviderStrategy 报 BadRequestError 400: "This response_format type is unavailable now"，是预期内的兼容性边界而非 bug。
- **换 schema 即换业务**：只把 ReviewAnalysis 换成 OrderInfo，其余代码一字未改，Agent 就从「评论分析」切到「订单抽取」。
- **结构化数据的可计算性**：批量抽取后，「情感分布」「平均紧急度」「高紧急条数」全部用 Python 的 Counter/sum 直接算出来。
- **需要锁定字段取值时**：用 Literal 类型注解锁死，或字段描述明确列出可选项。

### 关键命令与代码
定义 Pydantic schema（schemas.py）：
```python
# schemas.py（节选）
from pydantic import BaseModel, Field

class ReviewAnalysis(BaseModel):
    """客户评论分析结果"""
    sentiment: str = Field(description="情感极性：positive / negative / neutral")
    category: str = Field(description="问题类别：logistics / product_quality / refund 等")
    urgency: int = Field(description="紧急程度，1-5 的整数，5 最紧急")

class OrderInfo(BaseModel):
    """订单信息抽取结果"""
    order_id: str = Field(description="订单编号，如 ORD-20240301-001")
    product_name: str = Field(description="商品名称")
    amount: float = Field(description="订单金额，单位元")
    status: str = Field(description="订单状态：shipped / delivered / disputed 等")
```
用 ToolStrategy 包装 schema 传给 response_format：
```python
# step3_create_agent_structured.py（节选）
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from schemas import ReviewAnalysis

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(ReviewAnalysis),  # 关键：开启结构化输出
)
print("Agent created:", type(agent).__name__)
```
invoke 一条评论并读 structured_response：
```python
# step4_invoke_structured.py（节选）
result = agent.invoke({"messages": [{"role": "user", "content": reviews[0]}]})
print("result keys:", list(result.keys()))
sr = result["structured_response"]
print("类型:", type(sr).__name__)
print("  .sentiment =", sr.sentiment)
print("  .category  =", sr.category)
print("  .urgency   =", sr.urgency)
```
换 schema 复用（只改 schema 类名）：
```python
# step7_reuse_order_schema.py（节选）
from schemas import OrderInfo  # 唯一改动：换 schema 类名
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(OrderInfo),
)
for text in order_texts:
    result = agent.invoke({"messages": [{"role": "user", "content": text}]})
    info = result["structured_response"]
    print(f"  .order_id={info.order_id} / .amount={info.amount} / .status={info.status}")
```
迁移改写骨架（评论分析 → 简历解析）：
```python
# 改之前
class ReviewAnalysis(BaseModel):
    sentiment: str = Field(description="情感极性：positive / negative / neutral")
    category: str = Field(description="问题类别：logistics / product_quality 等")
    urgency: int = Field(description="紧急程度，1-5 的整数")

# 改之后
class ResumeInfo(BaseModel):
    """简历信息抽取结果"""
    name: str = Field(description="候选人姓名")
    skills: list[str] = Field(description="技能列表，如 ['Python', 'SQL']")
    years: int = Field(description="工作年限，整数")
```

### 关键坑/注意
- **pydantic 无需额外 pip install**：随 langchain 1.3.2 一并装好（Pydantic v2）。
- **ProviderStrategy 在 DeepSeek 上报 400**：不是程序写错，是 DeepSeek 没有「原生结构化输出 API」端点。正确做法是退回兼容性更广的 ToolStrategy，而不是为用 ProviderStrategy 去换模型。
- **不要假设「让模型输出 JSON」就等于结构化**：靠提示词得到的 JSON 是类型不安全、键名不可控的字符串。
- **要锁定字段取值须在描述列出可选项或用 Literal 类型**：否则模型可能填中文而非预期英文值。
- **批量场景存在随机性**：同一文本多次调用分类可能不同，生产建议更明确指引或 Literal 锁定。

---

## 第4章 LangChain 中间件系统（middleware-system）从零到一跑通实操手册

### 本质
把「每个地方都要加的同一段代码」（横切关注点 cross-cutting concern）从到处手写变成声明式挂载——通过 create_agent(middleware=[...]) 挂上 middleware，用 6 个钩子（hook）在固定时机自动回调，不必改动工具函数和主流程一行代码。

### 关键知识点
- **横切关注点定义**：用来描述「跨越多个模块、到处都要插一段相同代码」的逻辑（如日志、限流控成本、脱敏、工具抛错兜底），与具体业务无关却散落在每个调用点。
- **middleware 解法**：把横切逻辑写成独立单元，创建 Agent 时通过 middleware=[...] 声明挂载。源码模块 langchain.agents.middleware。
- **钩子（hook）机制**：框架在 Agent 执行的固定时机预留「挂载点」，middleware 把逻辑挂到这些点，到点自动回调。
- **6 个 hook 分两类**：
  - 节点 hook（固定时刻触发、观察或修改状态）：before_agent（智能体循环开始前，仅一次）、before_model（每次调模型前）、after_model（每次调模型后）、after_agent（智能体循环结束后，仅一次）。
  - 包裹 hook（把目标调用「包」在中间、调用前后都能插手）：wrap_model_call（包住一次模型调用）、wrap_tool_call（包住一次工具调用）。
- **「每次调模型」的措辞差异**：含工具调用的问题会多次调用模型。因此 before_model/after_model 在一次 invoke 里触发多次，而 before_agent/after_agent 只在整个循环头尾各触发一次（一个工具调用问题 = 两轮模型调用）。
- **AgentMiddleware 基类**：所有 middleware 不管装饰器式还是类式，底层都是它的子类。真实路径 langchain.agents.middleware.types.AgentMiddleware。@before_model 装饰器是语法糖——背后动态创建了一个继承 AgentMiddleware、只实现 before_model 方法的类。
- **装饰器式 vs 类式**：底层统一。装饰器式优势是简洁（单 hook、无状态的简单逻辑）；类式优势是完整（一个类可同时实现多个 hook，还能携带实例状态如 call_count 跨多次调用累积）。选型判断线：单 hook 无状态用装饰器，多 hook 或需状态用类。
- **内置 middleware**：LangChain v1 当前导出 14 个，开箱即用、一行声明。覆盖：模型/工具调用次数限流（ModelCallLimitMiddleware/ToolCallLimitMiddleware）、敏感信息脱敏（PIIMiddleware）、模型/工具失败自动重试（ModelRetryMiddleware/ToolRetryMiddleware）、主模型失败降级备用（ModelFallbackMiddleware）、上下文摘要/裁剪（SummarizationMiddleware/ContextEditingMiddleware）、关键操作前人工审批（HumanInTheLoopMiddleware）、任务清单/工具筛选/工具模拟（TodoListMiddleware/LLMToolSelectorMiddleware/LLMToolEmulator）、Shell 工具/文件搜索（ShellToolMiddleware/FilesystemFileSearchMiddleware）。
- **ModelCallLimitMiddleware 三参数**：thread_limit（整个会话线程累计模型调用上限）、run_limit（单次 invoke 运行内模型调用上限）、exit_behavior（超限后的行为，'end' 默认安静结束、返回已有结果，'error' 抛异常）。
- **PIIMiddleware 脱敏**：把敏感信息在送进模型前脱敏。两种策略：redact（整段替换成占位符）、mask（部分遮罩、保留尾部用于识别）。内置脱敏类型只有 5 种（email、credit_card、ip、mac_address、url），不含中文手机号，需通过 detector 参数传正则。脱敏时机在 before_model（消息送进模型之前）。
- **执行顺序铁律**：before_* 系列按列表正序触发（M1→M2→M3），after_* 系列按列表逆序触发（M3→M2→M1）。栈式结构——先进后出，像穿脱衣服。列表顺序就是你安排依赖关系的开关。
- **wrap_model_call 嵌套（俄罗斯套娃）**：M1 最外层包着 M2，M2 包着 M3，M3 最内层、最贴近真实 LLM 调用。进入时正序 M1→M2→M3 一层层往里走，再逆序往外退。最内层最接近模型，可在真实调用最后一刻改写请求（这是 ModelFallbackMiddleware 降级的实现基础）。
- **hook 不只是观察者还能当拦截者**：
  - wrap_tool_call 捕获工具抛出的异常、转换成一条正常工具结果喂回模型，让 Agent 优雅继续而不崩溃。返回的 ToolMessage 必须带 tool_call_id=request.tool_call["id"]，否则模型报 400。
  - jump_to 让 Agent 在调模型前提前退出。必须先用 @hook_config(can_jump_to=["end"]) 显式声明跳转权限，否则运行时报错（框架防误用的安全设计）。
- **middleware 换 agent 即复用**：同一 middleware 类挂到两个工具集完全不同的 Agent 都正常触发；实例状态互相独立；after_model 里能看到模型这轮决定调哪些工具。

### 关键命令与代码
确认 middleware 模块就位：
```python
# step1_middleware_base.py（节选）
from langchain.agents.middleware import (
    before_agent, before_model, after_model, after_agent,  # 4 个节点 hook
    wrap_model_call, wrap_tool_call,                        # 2 个包裹 hook
    AgentMiddleware,                                        # 基类
    ModelCallLimitMiddleware, PIIMiddleware, SummarizationMiddleware,  # 内置
)
from langchain.agents import create_agent
```
装饰器式 middleware（签名固定为 fn(state, runtime)，返回 None=不修改 state，返回 dict=可修改状态）：
```python
# step2_log_middleware.py（节选）
from langchain.agents.middleware import before_model, after_model

@before_model
def log_before(state, runtime):
    msgs = state["messages"]
    print(f"[before_model] 消息数={len(msgs)}")
    return None  # 返回 None = 不修改 state，继续正常流程

@after_model
def log_after(state, runtime):
    print("[after_model] 模型已返回")
    return None

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    system_prompt="你是一个订单运营助手。",
    middleware=[log_before, log_after],
)
```
类式 middleware（可携带实例状态、实现多个 hook）：
```python
# ext2_decorator_vs_class.py（节选）
class CountingMiddleware(AgentMiddleware):
    def __init__(self, tag):
        self.tag = tag
        self.call_count = 0
    def before_model(self, state, runtime):
        self.call_count += 1
        print(f"[类式 before_model] [{self.tag}] 第{self.call_count}次 · 消息数={len(state['messages'])}")
        return None
```
ModelCallLimitMiddleware 限流：
```python
# step3_call_limit.py（节选）
from langchain.agents.middleware import ModelCallLimitMiddleware
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[log_before, ModelCallLimitMiddleware(run_limit=2)],
)
```
PII 脱敏（内置 email + 自定义中文手机号正则）：
```python
# step4_pii_middleware.py（节选）
from langchain.agents.middleware import PIIMiddleware
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order],
    middleware=[
        PIIMiddleware("email", strategy="redact"),
        PIIMiddleware("phone", detector=r"1[3-9]\d{9}", strategy="mask"),
        log_pii_before,
    ],
)
```
执行顺序铁律演示（3 个 middleware 同挂）：
```python
# step5_hook_order.py（节选）
class OrderM(AgentMiddleware):
    def __init__(self, tag): self.tag = tag
    def before_model(self, state, runtime):
        print(f"→ [before_model] {self.tag}  (消息数={len(state['messages'])})")
    def after_model(self, state, runtime):
        print(f"← [after_model]  {self.tag}")
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping],
    middleware=[OrderM("M1"), OrderM("M2"), OrderM("M3")],
)
```
wrap_tool_call 捕获工具错误（注意 handler 要传 request）：
```python
# step6_wrap_tool_call.py（节选）
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

@wrap_tool_call
def handle_tool_error(request, handler):
    try:
        return handler(request)          # 注意：handler 要传 request，不是 handler()
    except Exception as e:
        return ToolMessage(
            content=f"工具执行失败：{e}，建议稍后重试",
            tool_call_id=request.tool_call["id"],
        )
```
jump_to 提前退出（须先声明跳转权限）：
```python
# ext4_jump_to_early_exit.py（节选）
from langchain.agents.middleware import before_model, hook_config
from langchain_core.messages import AIMessage

@before_model
@hook_config(can_jump_to=["end"])
def content_filter(state, runtime):
    last = state["messages"][-1].content
    if "退款" in last:
        print("[ContentFilter] 检测到违禁词「退款」→ jump_to=end")
        return {
            "messages": [AIMessage(content="您的问题包含敏感词「退款」，已被自动拦截，请联系人工客服。")],
            "jump_to": "end",
        }
    return None
```

### 关键坑/注意
- **hook 签名差异**：节点 hook 是 fn(state, runtime)，包裹 hook 是 fn(request, handler)，两者完全不同。wrap_tool_call 的完整签名是 fn(request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage]) -> ToolMessage——handler 需把 request 传回去（handler(request)），不能当零参数函数 handler() 调，否则报 TypeError: execute() missing 1 required positional argument。
- **返回的 ToolMessage 必须带 tool_call_id**：漏掉则模型报 400。
- **jump_to 必须先用 @hook_config(can_jump_to=["end"]) 声明权限**：否则运行时报错。
- **内置 middleware 参数风格不统一**：ModelCallLimitMiddleware 用关键字参数（run_limit=2），而 ModelFallbackMiddleware 真实签名是 (first_model, *additional_models)——位置参数，不是 fallback_model= 关键字参数。正确用法 ModelFallbackMiddleware("deepseek:deepseek-chat", "openai:gpt-4o")。
- **PIIMiddleware 内置脱敏类型只有 5 种，不含中文手机号**：脱敏中文手机号需通过 detector 参数传正则（如 r"1[3-9]\d{9}"）。
- **含一次工具调用的问题会触发两轮 before_model/after_model**：别误以为触发了多余的次数。
- 迁移自检三条：触发验证、顺序验证、复用验证。

---

## 第5章 LangChain 持久化记忆：让 Agent 记住多轮对话从零到一跑通实操手册

### 本质
给默认无状态的 create_agent Agent 装上「记事本」——靠 checkpointer（检查点存储器 + 存档）+ thread_id（会话线程标识 + 隔离）让它在同一个会话里记住前文，把「一问一答」升级成「连续对话」，同时保证不同用户记忆互不串台。改动只有一处：给 create_agent 多传一个 checkpointer 参数。

### 关键知识点
- **Agent 默认无状态**：每一次 invoke 调用都是独立的一问一答，模型不记得上一轮。
- **两个核心对象**：checkpointer（Agent 每走完一步就把当前完整对话状态存一份档，下次调用自动读回接着跑）；thread_id（每个独立会话用一个标识区分，同一 thread_id 多次调用共享记忆、不同 thread_id 彼此隔离）。
- **记忆机制是 LangGraph 提供的**：LangGraph 是 LangChain 的底层图执行引擎，create_agent 底层就是 LangGraph。
- **InMemorySaver**：内存检查点存储器，随 langgraph 一并安装无需额外装包，开发阶段最常用。import 路径 langgraph.checkpoint.memory。
- **加 checkpointer 不改变 Agent 对象类型**：create_agent 加 checkpointer 后返回类型仍是 CompiledStateGraph。记忆是「叠加」上去的能力。
- **触发记忆的开关在 invoke 第二个参数 config**：config 是嵌套字典，会话标识放在 configurable.thread_id 下。光挂 checkpointer 还不够，真正触发记忆的是调用时传入的 thread_id。
- **记忆原理（核心拆解）**：①checkpointer 在每个 super-step 边界存档（super-step 是图执行的最小推进单位）；②thread_id 是会话主键（InMemorySaver 内部以 thread_id 为键存储不同会话状态）；③第二轮自动加载历史。一句话：记忆不是模型「记住」的，是 checkpointer 把历史存下来、每轮调用前自动回填给模型。模型本身依然无状态，有状态的是 checkpointer 这个外部存储。
- **get_state(config) 返回 StateSnapshot（状态快照）**，共 8 个字段：values（当前对话状态，核心是 values["messages"]）、next（下一步要执行的图节点，() 表示已到 END 终态、("model",) 停在等待模型、("tools",) 停在等待工具执行）、config（含 thread_id 与 checkpoint_id 唯一 UUID）、metadata（含 source、step）、created_at、parent_config（快照间串成链）、tasks（待执行任务，HITL 场景才有值）、interrupts（中断点，HITL 场景才有值）。
- **metadata.ls_integration = 'langchain_create_agent'** 坐实底层事实：create_agent 不是独立实现，底层就是 LangGraph。
- **checkpoint 存的是完整 messages 列表，不是「对话摘要」**：每条消息原样保留。messages 有四种 type：human、ai、tool、ai。一次工具调用在 messages 里占 3 条（ai + tool + ai）。
- **get_state_history(config) 看完整时间线，倒序返回**：history[0] 是最新快照，history[-1] 是 step=-1 的初始空快照。每个 super-step 对应一个 checkpoint_id（UUID，是定位某一历史时刻的锚点）。
- **时间旅行（time travel）**：把某个历史快照的 checkpoint_id 填进 config，从那一刻重新出发继续对话。工程铁律：时间旅行只能从 next=() 的「稳态快照」出发——从含未完成 tool_calls 的进行中快照重放会被模型 API 拒绝（返回 400 An assistant message with tool_calls must be followed by tool messages）。修复用 filter：[h for h in get_state_history(config) if h.next == ()]。
- **thread_id 隔离**：同一个 agent 实例，只把 config 里的 thread_id 从 u1 换成 u2，记忆就完全隔离。①thread_id 是命名空间；②一个 agent 实例承载无限会话；③生产标准写法 thread_id = str(user.id)。
- **InMemorySaver 的边界**：状态存在进程内存，进程一退出内存清空、所有 thread_id 记忆全部消失。
- **SqliteSaver**：把状态写进 SQLite 数据库文件，进程退出文件还在、重开就能恢复。不随 langgraph 默认安装，需单独装 langgraph-checkpoint-sqlite。配合 SqliteSaver.from_conn_string(db_path) 且推荐用 context manager 管理 DB 连接。DB 文件必须放 APFS 主盘，不要放 ExFAT 外置磁盘（不支持 POSIX 文件锁，WAL 模式会失败）。
- **跨进程持久化验证**：阶段 1 用 SqliteSaver 建立对话落盘；阶段 2 新建 agent 实例、重新打开同一个 DB 再问，Agent 能答出之前的信息。迁移成本只改 checkpointer= 一个参数。
- **checkpointer 三档差异（线性升级路径，接口一致、仅存储介质不同）**：InMemorySaver（进程内存、重启记忆全清、无额外安装、开发/调试/单元测试）；SqliteSaver（本地 SQLite 文件、重启记忆保留、pip install langgraph-checkpoint-sqlite、本地持久/单机演示）；PostgresSaver（PostgreSQL 数据库、重启记忆保留、pip install langgraph-checkpoint-postgres、生产/多实例/高并发）。

### 关键命令与代码
给 create_agent 传 checkpointer 参数（唯一改动）：
```python
# step1_checkpointer_agent.py
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import query_order, track_shipping, calc_shipping_fee

checkpointer = InMemorySaver()
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[query_order, track_shipping, calc_shipping_fee],
    system_prompt="你是一个订单运营助手，可以帮用户查询订单、物流和运费。",
    checkpointer=checkpointer,
)
print("agent 类型:", type(agent).__name__)
print("agent.checkpointer:", type(agent.checkpointer).__name__)
```
多轮记忆（同一 thread_id 记住前文，config 放 thread_id）：
```python
config_u1 = {"configurable": {"thread_id": "u1"}}
# Round 1：用户告知订单号
result = agent.invoke(
    {"messages": [{"role": "user", "content": "你好，我的订单号是 A1001，请帮我记住。"}]},
    config_u1,
)
# Round 2：复用同一个 config_u1，问一个依赖前文的问题
result = agent.invoke(
    {"messages": [{"role": "user", "content": "我刚才说的订单号是什么？"}]},
    config_u1,
)
```
get_state 看快照：
```python
snapshot = agent.get_state(config_u1)
print("StateSnapshot 字段:", list(snapshot._fields))
print("messages 总数:", len(snapshot.values["messages"]))
print("next =", snapshot.next)
```
get_state_history 看完整时间线：
```python
for h in agent.get_state_history(config):
    print(f"step={h.metadata['step']}  checkpoint_id={h.config['configurable']['checkpoint_id']}")
```
时间旅行（从历史快照重放，须选 next=() 稳态快照）：
```python
stable = [h for h in agent.get_state_history(config) if h.next == ()]
target = stable[-1]
replay_config = {
    "configurable": {
        "thread_id": "xxx",
        "checkpoint_id": target.config["configurable"]["checkpoint_id"],
    }
}
agent.invoke({"messages": [{"role": "user", "content": "我们聊了什么？我的订单号是多少？"}]}, replay_config)
```
安装并配置 SqliteSaver：
```bash
pip install langgraph-checkpoint-sqlite
```
```python
from langgraph.checkpoint.sqlite import SqliteSaver
db_path = "/tmp/langchain_case4_checkpoint.db"
with SqliteSaver.from_conn_string(db_path) as checkpointer:
    agent = create_agent(model=..., tools=..., checkpointer=checkpointer)
```

### 关键坑/注意
- **不要默认「模型自己会记住上一句」**：模型本身无状态，记忆来自外部 checkpointer。Agent 若「忘了」前文，先确认两点——是不是漏传了 checkpointer，或两次调用的 thread_id 是不是同一个。
- **光挂 checkpointer 不够**：真正触发记忆的是调用时传的 thread_id，须在 invoke 的 config 里带上 {"configurable": {"thread_id": ...}}。
- **时间旅行只能从 next=() 的稳态快照出发**：从含未完成 tool_calls 的进行中快照（如 next=('tools',)）重放会被模型 API 拒绝。
- **SqliteSaver 需装额外包**：pip install langgraph-checkpoint-sqlite 不能省。
- **SqliteSaver DB 文件必须放主盘**：不要放 ExFAT 外置磁盘。
- 迁移自检三条：多轮记忆验证、thread 隔离验证、持久化验证。
