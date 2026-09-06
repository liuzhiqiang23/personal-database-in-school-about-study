---
concept: langfuse-selfhost-setup
one_liner: 自托管观测平台是一整套容器编排，起栈前要处理端口冲突、初始化变量链与两处密码一致性
stage_span: [stage-2]
prerequisites: [agent-tracing-model]
related: [langfuse-langchain-integration, observability-platform-choice, local-environment-traps]
applications: [langfuse-langchain-integration]
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#三、用 Docker Compose 起一套 Langfuse self-host
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.1 端口冲突：PostgreSQL 宿主端口改 5433
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.2 初始化变量：LANGFUSE_INIT 是一条链，缺一不可
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.3 密码一致性：S3 与 PostgreSQL 两处
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、启动后验证：登录、看到预置项目、拿到 API Key
---

## 是什么

自托管的观测平台不是单个容器，而是一整套服务：Web 前端、后台 worker、关系库、列式分析库（存 trace）、S3 兼容对象存储（存大字段）、缓存队列。官方把这套编排好放在一个 compose 文件里整体启动。

选自托管的核心原因是数据归属：所有 trace 数据存在本地容器里，物理上不离开本机。对数据不能出境的场景，这是硬约束而非偏好。

## 怎么用

下载官方编排文件并启动：

```bash
mkdir -p langfuse && cd langfuse
curl -sL "https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml" -o docker-compose.yml
docker compose up -d
```

启动前按本机情况改三处。关系库宿主端口（容器内保持不变）：

```yaml
ports:
  - "127.0.0.1:5433:5432"   # 宿主改 5433，容器内仍 5432
```

初始化变量写在同目录的环境文件里，一次性预置好组织、项目与接入密钥：

```bash
# .env
LANGFUSE_INIT_ORG_ID=...            # 组织 ID（UUID，必须先设）
LANGFUSE_INIT_ORG_NAME=langchain-course
LANGFUSE_INIT_PROJECT_ID=...        # 项目 ID（UUID，必须设才能创建 API Key）
LANGFUSE_INIT_PROJECT_NAME=langchain-demo
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-course-demo-public
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-course-demo-secret
LANGFUSE_INIT_USER_EMAIL=admin@langfuse.local
LANGFUSE_INIT_USER_NAME=admin
LANGFUSE_INIT_USER_PASSWORD=...
```

验证连通性时绕过系统代理：

```bash
curl --noproxy '*' http://localhost:3000
```

## 关键细节与参数

- 实测起的是 v3.175.0 开源版，6 个容器全部健康：Web 在 3000、worker 在 3030、关系库在宿主 5433，外加列式库、对象存储、缓存。
- **宿主端口改动不影响内部通信**：Web 与 worker 连关系库走的是容器内部网络地址，宿主映射端口只用于容器外直连调试。
- **初始化变量是链式依赖**：少设一个，整条初始化会被跳过（日志里只留一条警告），必须按组织 ID、组织名、项目 ID、项目名、密钥、用户信息的顺序设齐。预置密钥的好处是接入代码可以直接使用这对公私钥，不必再去界面手动复制。
- **两处密码必须一致**：对象存储的访问密钥必须与其根密码完全相同——实测第一次 trace 数据到了后端却无法持久化，根因就是这两个密码没对上；若自定义了关系库密码，连接串里的密码段也要同步改（教学环境最省事的做法是保留默认密码不覆盖）。
- 登录后可在项目设置里看到对外主机名与预置的公私钥，页面还给出可直接复制的环境变量片段。

## 常见陷阱

- **本机有系统代理时直接访问本地端口**：浏览器或命令行访问会走代理返回 502。验证连通性要显式绕过代理，这个坑在 Python 接入侧还会再遇到一次。
- **端口默认值与本机已有服务冲突**：宿主机已有同类数据库占用默认端口时，容器端口绑定失败，只需改宿主侧端口。
- **只设了部分初始化变量**：结果是没有任何预置组织与项目，且日志只有一条不显眼的警告，容易误判为启动失败。
