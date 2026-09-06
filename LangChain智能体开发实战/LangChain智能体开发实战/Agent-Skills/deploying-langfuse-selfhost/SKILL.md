---
name: deploying-langfuse-selfhost
description: 用 Docker Compose 在本机起一整套自托管的 Langfuse 可观测服务栈，并让它在首次启动就自动预置好组织、项目与 API Key。Use when 需要一个数据不出境的 LLM 追踪后端、要给 Agent 准备上报目标、或排查「postgres 端口绑定失败」「LANGFUSE_INIT 变量不生效没建出项目」「trace 到了后端却无法持久化」「浏览器访问 localhost:3000 返回 502」这类部署故障时。涵盖编排文件获取、端口冲突改法、初始化变量链、密码一致性、代理绕过、启动后验证与取 API Key；不含把 Agent 接上上报（见 tracing-langchain-agent）。
allowed-tools: Bash(docker:*), Bash(curl:*), Bash(mkdir:*)
sources:
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1、下载官方编排文件并启动
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.1 端口冲突：PostgreSQL 宿主端口改 5433
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.2 初始化变量：LANGFUSE_INIT 是一条链，缺一不可
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#1.3 密码一致性：S3 与 PostgreSQL 两处
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#2、启动后验证：登录、看到预置项目、拿到 API Key
  - experiments/langchain/stage-2-experiment/case-6-observability/handbook.md#3、本案例踩过的坑速查
---

## 能力目标

在本机起一套可用的自托管 Langfuse：六个容器全部健康、浏览器能登录、组织与项目已预置、拿到一对可直接写进接入代码的公私钥，所有追踪数据存在本地、不离开本机。

## 前置

- 本机装有 Docker 且 `docker compose` 可用。
- 自托管不是单容器，而是一整套服务：Web 前端、后台 worker、关系库、列式分析库（存追踪数据）、对象存储（存大字段）、缓存队列，官方把它们编排在一个 compose 文件里整体启动。
- 若本机设了系统 HTTP 代理，本地访问会被代理拦截，验证连通性时需显式绕过。

## 实操流程

1. 取官方编排文件：

   ```bash
   mkdir -p langfuse && cd langfuse
   curl -sL "https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml" -o docker-compose.yml
   ```

2. 启动前先改端口。默认编排把关系库的 5432 映射到宿主机，本机若已有别的实例占用该端口会绑定失败。只改宿主侧、容器内保持不变：

   ```yaml
   # docker-compose.yml 中 postgres 服务的 ports
   ports:
     - "127.0.0.1:5433:5432"
   ```

   Web 与 worker 容器走 Docker 内部网络连库，宿主端口只用于容器外直连调试，改它不影响内部通信。

3. 在同目录写 `.env`，把初始化变量**按顺序设齐**。这组变量是链式依赖，少设一个整条初始化就被跳过（日志里只留一条警告），结果是启动成功但没有组织、没有项目、没有 API Key：

   ```bash
   # .env
   LANGFUSE_INIT_ORG_ID=<一个 UUID>
   LANGFUSE_INIT_ORG_NAME=langchain-course
   LANGFUSE_INIT_PROJECT_ID=<一个 UUID>
   LANGFUSE_INIT_PROJECT_NAME=langchain-demo
   LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-course-demo-public
   LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-course-demo-secret
   LANGFUSE_INIT_USER_EMAIL=admin@langfuse.local
   LANGFUSE_INIT_USER_NAME=admin
   LANGFUSE_INIT_USER_PASSWORD=<登录密码>
   ```

   自定义公私钥的好处是接入代码可以直接写死这对钥匙，省掉去 Web 界面手动复制。

4. 对齐两处密码，否则容器之间认证失败：

   - 对象存储密码：`LANGFUSE_S3_*_SECRET_ACCESS_KEY` 必须与 `MINIO_ROOT_PASSWORD` **完全相同**。不一致的表现很隐蔽——追踪数据到了后端却无法持久化。
   - 关系库密码：若自定义了 `POSTGRES_PASSWORD`，`DATABASE_URL` 里的密码段要同步改。教学与本地环境最省事的做法是保留默认、不覆盖。

5. 启动并确认容器健康：

   ```bash
   docker compose up -d
   docker compose ps
   ```

   预期六个容器全部健康：web 在 3000、worker 在 3030、关系库在宿主 5433，另加列式分析库、对象存储、缓存队列。

6. 验证连通并登录取钥匙：

   ```bash
   curl --noproxy '*' -sw '\nHTTP: %{http_code}\n' http://localhost:3000
   ```

   浏览器打开 `http://localhost:3000`，用 `.env` 里预置的邮箱密码登录，应直接看到预置好的组织与项目（无需手动创建）。进项目后：Settings 的 General 页看服务地址，API Keys 页看预置的公私钥——这对钥匙就是接入代码要用的凭证。

## 校验回路

- `docker compose ps` 六个容器状态健康、无反复重启。
- `curl --noproxy '*' http://localhost:3000` 返回 200（走代理会得到 502，那是代理问题不是服务问题）。
- 登录后组织与项目已存在，说明初始化变量链完整生效。
- API Keys 页能看到你在 `.env` 里写的那对公私钥。
- 后续接入产生第一条追踪后，追踪列表里应出现记录且详情可展开——若列表始终为空但客户端不报错，回到第 4 步查对象存储密码。

## 常见陷阱

- **初始化变量少设一个**：整条初始化静默跳过，只在容器日志里留一条警告。表现为「服务起来了但要手动注册建项目」。按组织标识、组织名、项目标识、项目名、公钥、私钥、用户邮箱、用户名、密码的顺序设齐。
- **对象存储与关系库密码前后不一致**：追踪数据能到后端却持久化失败，界面上看不到完整记录。两处密码必须逐字一致。
- **本地访问被系统代理拦截**：浏览器或 curl 访问本机地址返回 502。curl 加 `--noproxy '*'`；浏览器自动化工具加不走代理的参数；Python 侧另有专门设置（见 tracing-langchain-agent）。
- **改端口时连容器内端口一起改**：只改宿主侧映射即可，把容器内端口也改掉会让内部通信断掉。
