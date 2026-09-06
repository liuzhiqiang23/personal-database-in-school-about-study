---
concept: python-env-and-venv-setup
one_liner: LangChain v1 要求 Python 3.10+，必须先核对解释器版本再用达标解释器建隔离虚拟环境
stage_span: [stage-1, stage-2]
prerequisites: []
related: [langchain-package-stack, local-environment-traps]
applications: [deepseek-provider-integration, create-agent-entry]
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#二、环境准备:从 Python 版本到虚拟环境
  - experiments/langchain/stage-1-bootstrap/handbook.md#1、环境基线检测
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、创建并激活虚拟环境
  - experiments/langchain/stage-2-experiment/case-1-create-agent-core/handbook.md#1、确认运行环境
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、确认环境与 InMemorySaver 就位
---

## 是什么

LangChain v1 是纯 Python 框架，不依赖 GPU、也没有大内存要求，普通笔记本或台式机本机即可运行。它唯一的硬性环境门槛写在官方 install 文档里：`Requires Python 3.10+`。因此搭环境的第一步不是装包，而是核对本机可用的解释器版本——版本不达标时先装包，只会在依赖解析阶段失败。

第二件必须做的事是隔离。虚拟环境把本项目的依赖与系统全局环境分开，避免包版本互相污染。此后所有实操（工具调用循环、中间件、记忆、检索增强、长程脚手架）都在这个虚拟环境里进行，每个新场景开工前只需重新激活它，不必重建。

## 怎么用

先打印操作系统、架构与各个候选解释器的版本，判断哪个达标：

```bash
echo "OS: $(sw_vers -productName) $(sw_vers -productVersion) ($(uname -m))"
echo "系统 python3 = $(python3 --version)"
echo "brew python3.13 = $(/opt/homebrew/bin/python3.13 --version)"
```

用达标的解释器（而不是默认的 `python3`）创建并激活虚拟环境，再升级环境内的 pip：

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --quiet --upgrade pip
```

后续每次开工只需一条命令回到这个环境：

```bash
source .venv/bin/activate
```

## 关键细节与参数

- 实测基线：macOS 26.4.1（arm64）上系统自带 `/usr/bin/python3` 为 **3.9.6**，低于要求；通过 Homebrew 安装的 `python3.13`（3.13.13）达标，激活后 `python --version` 显示 `Python 3.13.13`，pip 升级到 26.1.1。
- 只要解释器 ≥3.10 即可，本机同时装有 3.11、3.12、3.13，任选其一都行。
- 跨平台差异：多数 Linux 发行版与新装的 Windows 自带的 Python 通常已 ≥3.10，可直接 `python3 -m venv .venv`；Windows 的激活命令是 `.venv\Scripts\activate`。
- 长程智能体脚手架 `deepagents` 的 Python 要求更严：≥3.11、<4.0，选解释器时按最严的那一条取。

## 常见陷阱

- **拿系统 Python 建环境**：macOS 系统自带的 Python 往往偏旧（实测 3.9.6），直接 `python3 -m venv` 建出来的环境装 LangChain v1 会因版本约束失败。建环境时显式写高版本解释器的绝对路径。
- **误以为激活是一次性的**：`source .venv/bin/activate` 只对当前终端会话生效，换一个终端窗口或新脚本执行前都要重新激活，否则 `python` 又指回系统解释器。
- **把环境建在不合适的磁盘上**：外置磁盘上的虚拟环境会带来一串与 LangChain 无关的报错与噪音（安装警告、资源分叉文件解码失败、SQLite 文件锁失败），排查路线见 local-environment-traps。
