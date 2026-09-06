---
concept: local-environment-traps
one_liner: 本机环境四类坑会伪装成框架报错——外置磁盘残留、资源分叉文件、文件系统不支持锁、系统代理拦本地请求
stage_span: [stage-1, stage-2]
prerequisites: [python-env-and-venv-setup]
related: [checkpointer-backends, embedding-and-vectorstore, langfuse-langchain-integration, langfuse-selfhost-setup]
applications: []
sources:
  - experiments/langchain/stage-1-bootstrap/handbook.md#2、创建并激活虚拟环境
  - experiments/langchain/stage-2-experiment/case-4-persistent-memory/handbook.md#1、SqliteSaver：跨进程持久化
  - experiments/langchain/stage-2-experiment/case-7-agentic-rag/handbook.md#2、安装依赖并用 RecursiveCharacterTextSplitter 切分
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、配置凭证与连接验证
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#3、本案例踩过的坑速查
---

## 是什么

有一类故障与框架本身完全无关，却会以框架报错的形式出现——根因在本机环境：工作目录所在的磁盘格式、遗留文件、系统代理配置。它们的共同特征是**报错信息指向框架内部**，照着报错查框架永远查不出结果。

四类坑与它们的伪装形态：

| 现象 | 根因 | 解法 |
| --- | --- | --- |
| 安装时刷 `WARNING: Ignoring invalid distribution -pip ...` | 先前安装中断，站点包目录里留下临时残留目录 | 无害噪音，可忽略或清理 |
| 导入向量化相关库报 `UnicodeDecodeError` | 外置磁盘上生成的资源分叉文件被当作源码用 UTF-8 解码 | 删除这些文件 |
| SQLite 存储器落盘失败、报锁相关错误 | 文件系统不支持 POSIX 文件锁，SQLite 的 WAL 模式失败 | 数据库文件放主盘 |
| 访问本地端口 502、连接自检超时 | 系统代理拦截了对本地地址的请求 | 各通道分别绕过代理 |

## 怎么用

清理安装中断的残留目录：

```bash
find ".venv/lib/python3.13/site-packages" -maxdepth 1 -name '~*' -exec rm -rf {} +
```

清理外置磁盘上的资源分叉文件：

```bash
find .venv/lib/python3.13/site-packages/transformers -name "._*" -type f -delete
find docs/ -name "._*" -type f -delete
```

绕过系统代理（三个通道各自处理）：

```bash
curl --noproxy '*' http://localhost:3000
```

```python
import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"   # 必须在客户端初始化前设
```

数据库文件放主盘：

```python
db_path = "/tmp/langchain_checkpoint.db"
```

## 关键细节与参数

- **安装警告是非阻塞的**：残留目录以特定前缀命名，包管理器每次都会报告"忽略无效分发"并跳过它们，然后照常完成工作。所有包都能正确装上、示例也能正常跑通，仅仅是输出噪音。
- **资源分叉文件的杀伤力更大**：macOS 在外置磁盘上会生成大量以特定前缀开头的文件，某些库在扫描模型目录时会读到这些二进制文件并尝试用 UTF-8 解码而报错。实测一条删除命令清掉了 5726 个这类文件，之后相关库全部恢复正常导入。
- **文件锁问题只在特定文件系统上出现**：ExFAT 格式的外置磁盘不支持 POSIX 文件锁，实测因此把数据库路径改到了主盘。
- **代理问题在三处各出现一次**：命令行、无头浏览器、Python 客户端都要各自绕过；Python 侧的免代理变量必须在客户端初始化**之前**设置。
- 判别口诀：报错信息指向框架内部、但换一台机器或换个目录就消失的，先怀疑环境而不是框架。

## 常见陷阱

- **照着报错去查框架**：解码错误、锁错误、超时错误的信息都指向库内部，按它排查会一路走偏。
- **把安装警告当成安装失败**：它不阻塞安装，看到它就重装反而浪费时间。
- **只在一个通道绕过代理**：命令行通了不代表 Python 通，实测两处都需要单独处理。
- **把工作目录放在外置磁盘上却不预期这些坑**：外置磁盘是这几类问题的共同放大器，条件允许时把虚拟环境与数据文件放主盘最省事。
