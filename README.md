<div align="center">

<img src="docs/assets/growthagent-logo.svg" alt="GrowthAgent logo" width="88" height="88" />

<h1>GrowthAgent</h1>

<p><strong>让每个好产品，都能找到它的第一批用户。</strong></p>

<p>本地优先、可自托管的 AI 获客工作台。理解产品、发现真实需求、判断机会并完成克制触达。</p>

<p>
  <a href="https://github.com/super-xinz/Growth/releases"><img src="https://img.shields.io/github/v/release/super-xinz/Growth?style=flat-square&amp;label=release" alt="Release" /></a>
  <a href="https://github.com/super-xinz/Growth/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/super-xinz/Growth/ci.yml?branch=main&amp;style=flat-square&amp;label=CI" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-EA0000?style=flat-square" alt="Apache 2.0 License" /></a>
  <a href="https://growthagent-guikesong.zeabur.app/"><img src="https://img.shields.io/badge/demo-online-16A34A?style=flat-square" alt="Online demo" /></a>
</p>

<p>
  <a href="#快速开始">快速开始</a> ·
  <a href="#工作原理">工作原理</a> ·
  <a href="#核心能力">核心能力</a> ·
  <a href="#产品预览">产品预览</a> ·
  <a href="#技术栈与选型">技术栈</a> ·
  <a href="#安全边界">安全边界</a> ·
  <a href="#参与贡献">参与贡献</a>
</p>

</div>

<p align="center">
  <a href="产品截图/截屏2026-07-15%2003.43.12.png">
    <img src="产品截图/截屏2026-07-15%2003.43.12.png" alt="GrowthAgent 机会看板" width="100%" />
  </a>
</p>

<p align="center"><sub>从原始需求、判断依据到拟回复内容，在一个机会看板中完成决策。</sub></p>

## 为什么需要 GrowthAgent

AI 正在快速降低软件开发的门槛。当“把产品做出来”不再是最难的事，真正稀缺的能力就变成了：**让产品被看见，并持续获得用户。**

创始人本该专注于持续交付产品、理解客户和解决真实问题，而不是把时间耗在管理私信与邮件、分配广告预算，以及机械地维护社交媒体内容上。过去，他们往往只能每年花费约 20 万美元聘请增长负责人，或者自己拼凑一套昂贵、复杂且难以维护的增长工具栈。

**Cursor 为编程做了什么，GrowthAgent 就要为增长做什么。**

> 你负责把产品做出来，GrowthAgent 负责找到第一批用户。

## 快速开始

### 在线 Demo

直接访问：**<https://growthagent-guikesong.zeabur.app/>**

公开实例以只读模式运行，可查看工作台、产品流程与设置界面；为保护账号和数据，创建、删除、配置密钥、扫码登录和发布等写操作仅在本机自托管版本中开放。

### Windows 一键启动

需要预先安装并启动 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

1. 下载最新版 [GrowthAgent-Windows-x64.exe](https://github.com/super-xinz/Growth/releases/latest/download/GrowthAgent-Windows-x64.exe)；
2. 双击运行，启动器会自动生成本地密钥、配置 GrowthAgent 托管模型、拉取容器并等待服务就绪；
3. 浏览器将自动进入小红书扫码页；本人扫码后会直接进入工作台。模型、密钥和运行参数无需配置。

再次运行会更新并启动服务。停止服务：

```powershell
GrowthAgent-Windows-x64.exe --stop
```

> 当前启动器尚未进行商业代码签名，Windows SmartScreen 首次运行时可能提示来源未知。

### macOS、Linux 安装包

从 [最新 Release](https://github.com/super-xinz/Growth/releases/latest) 下载对应的 `.tar.gz`，解压后运行：

```bash
tar -xzf GrowthAgent-macOS-arm64.tar.gz   # 按平台替换文件名
./GrowthAgent-macOS-arm64
```

macOS 安装包尚未完成 Developer ID 签名与公证，首次运行可能被系统拦截；生产分发前应完成正式签名。Linux 需要 Docker Engine 与 Compose v2。

安装版首次启动会直接要求本人扫码登录小红书，登录成功后自动进入工作台。除提供自己的产品网站或 GitHub 地址外，不需要再配置模型或运行参数。

### 开发者

需要 Git、Docker Desktop，或 Docker Engine + Compose v2。

```bash
git clone https://github.com/super-xinz/Growth.git
cd Growth
cp .env.example .env
```

将 `.env` 中的 `SECRET_KEY`、`ENCRYPTION_KEY` 和 `POSTGRES_PASSWORD` 替换为三个独立随机值，然后启动：

```bash
make dev
```

| 入口 | 地址 |
| --- | --- |
| 工作台 | <http://localhost:3000/dashboard> |
| 设置 | <http://localhost:3000/account> |
| API 文档 | <http://localhost:8000/docs> |

## 工作原理

```text
产品网站 / GitHub 仓库
          ↓
带来源证据的 Product Brain
          ↓
发现需求 → 判断匹配度与风险 → 生成克制回复
          ↓
持续互动 → 记录访问、注册与激活
```

只需提供产品网站或 GitHub 仓库链接，GrowthAgent 就会持续运行：

1. **理解产品**：梳理产品定位、目标用户、核心能力与卖点；
2. **发现需求**：找到正在求推荐、寻找替代方案或讨论相关痛点的用户；
3. **判断机会**：结合匹配度、来源证据与发布风险筛选讨论；
4. **持续互动**：生成有价值且克制的回复，并跟进用户追问；
5. **衡量结果**：记录每次互动带来的访问、注册与激活。

当前版本聚焦小红书，未来可扩展至 X、抖音等更多内容与社交平台。

## 核心能力

- **有证据的产品理解**：Product Brain 不只生成结论，也保留支持能力判断的公开来源。
- **需求驱动的机会发现**：围绕目标用户、待完成任务、适合场景和搜索信号持续发现需求。
- **匹配与风险双重判断**：每个机会同时提供匹配分数、风险分数和可核对的判断依据。
- **低频、可控的自动化**：支持机会门槛、风险上限、搜索间隔、触达冷却、每日上限和全局停止开关。
- **对话与转化归因**：保留互动上下文，并记录访问、注册和激活事件。
- **清晰的数据边界**：小红书 Cookie 仅保存在本地数据卷；托管模型只接收完成任务所需的产品资料与提示词。

## 产品预览

<table>
  <tr>
    <td width="50%" valign="top">
      <strong>工作台</strong><br />
      <sub>产品状态、高意向机会、已完成触达和下次运行时间。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.44.05.png"><img src="产品截图/截屏2026-07-15%2003.44.05.png" alt="GrowthAgent 工作台" /></a>
    </td>
    <td width="50%" valign="top">
      <strong>添加产品</strong><br />
      <sub>提供产品网站或 GitHub 仓库，即可创建并分析产品。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.45.10.png"><img src="产品截图/截屏2026-07-15%2003.45.10.png" alt="添加产品" /></a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <strong>Product Brain 与自动化</strong><br />
      <sub>集中配置运行状态、机会门槛、频率和安全规则。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.45.40.png"><img src="产品截图/截屏2026-07-15%2003.45.40.png" alt="产品画像与自动化规则" /></a>
    </td>
    <td width="50%" valign="top">
      <strong>搜索信号与来源证据</strong><br />
      <sub>展示适合场景、排除场景、搜索信号和能力证据。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.45.53.png"><img src="产品截图/截屏2026-07-15%2003.45.53.png" alt="产品画像、搜索信号与来源证据" /></a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <strong>模型服务</strong><br />
      <sub>配置并测试 OpenAI 兼容模型，API Key 只显示脱敏提示。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.44.48.png"><img src="产品截图/截屏2026-07-15%2003.44.48.png" alt="模型服务与小红书账号设置" /></a>
    </td>
    <td width="50%" valign="top">
      <strong>本地账号连接</strong><br />
      <sub>检查小红书登录状态，Cookie 仅保存在本地。</sub><br /><br />
      <a href="产品截图/截屏2026-07-15%2003.44.58.png"><img src="产品截图/截屏2026-07-15%2003.44.58.png" alt="小红书账号连接检查" /></a>
    </td>
  </tr>
</table>

## 模型配置

正式发布的安装包默认连接 GrowthAgent 托管模型，用户无需填写 API 地址、模型名称或 API Key。DeepSeek 原始 Key 只存在于托管 API 的服务端环境变量中，不会进入前端、Git 或公开安装包。

安装包携带的是可轮换、受限流的网关凭证，并为每台安装生成独立标识。网关会固定模型、限制输入输出长度，并同时执行每分钟、每日和全局额度控制。

开发者需要使用自己的模型时，可设置 `LLM_SETTINGS_LOCKED=false`，然后在“设置 → 模型服务”中保存 OpenAI 兼容配置。该 Key 使用 `ENCRYPTION_KEY` 加密后存入数据库，读取时不会返回明文。

## 安全边界

GrowthAgent 当前面向本机或可信内网中的单用户部署。API 尚未提供多用户身份认证，**请勿将 3000、8000 或 18060 端口直接暴露到公网。**

官方在线 Demo 由后端强制限制为只读模式。需要配置模型密钥、连接小红书账号或执行发布操作时，请使用本机自托管版本，或在可信认证代理之后部署并显式开启公网写操作。

- Docker 端口只绑定到 `127.0.0.1`，PostgreSQL 和 Redis 不映射到宿主机；
- 小红书 Cookie 保存在本地 Docker volume 或 `.xiaohongshu-data/`，并已被 Git 忽略；
- 发布、搜索和回复受分数阈值、风险阈值、冷却、日上限与全局停止开关约束；
- 外部写操作不自动重试，避免平台已接收但响应丢失时产生重复评论；
- `.env`、私钥、Cookie 和本地数据不会被提交到版本库。
- 托管模型网关凭证可以从安装包中提取，因此它绝不能是 DeepSeek 原始 Key；上游 Key 必须只保存在服务端，并通过网关限流保护。

完整说明见 [安全政策](SECURITY.md) 与 [运行手册](docs/runbook.md)。

## 技术栈与选型

| 层级 | 技术与框架 | 选型用途 |
| --- | --- | --- |
| Web | Next.js 15、React 19、TypeScript、TanStack Query | 服务端渲染控制台、类型安全的数据请求与交互状态管理 |
| API | Python 3.12、FastAPI、Pydantic | 异步 API、请求校验和自动生成 OpenAPI 文档 |
| 数据 | PostgreSQL 16、SQLAlchemy、Alembic | 持久化产品、机会、对话、审计记录与可重复数据库迁移 |
| 任务队列 | Redis 7、Celery | 定时搜索、后台分析和低频自动化任务 |
| AI | OpenAI 兼容接口、Mock Provider | 生成 Product Brain、机会判断与回复；Mock 支持无密钥演示 |
| 平台连接 | 小红书 MCP | 本地浏览器登录、搜索、详情读取与受控回复 |
| 可视化 | Recharts | 展示机会和转化分析数据 |
| 交付 | Docker Compose、GitHub Actions、GHCR、Go 1.22 启动器 | 多架构镜像、自动测试、Release 与桌面一键启动 |
| 部署 | Zeabur | 托管公开只读演示实例 |

## 架构

```text
Next.js Web
    │
    ▼
FastAPI ───── PostgreSQL
    │             │
    ├──── Redis / Celery Worker
    ├──── OpenAI 兼容模型服务
    └──── 小红书 MCP 浏览器自动化
```

```text
apps/api          FastAPI、数据库迁移、自动化与模型提供器
apps/web          Next.js 本地控制台
cmd               GitHub Release 桌面启动器
infra/docker      开发与发布镜像
docs              架构、政策、部署和运行手册
tests             后端与安全工作流测试
.github           CI、Release、Issue 与依赖更新配置
```

详细设计见 [架构文档](docs/architecture.md)。

## 开发与验证

```bash
make test
make lint
make typecheck
make build
```

CI 会验证后端测试与 Ruff、前端测试与生产构建、Compose 配置、密钥泄露扫描，以及 Windows 启动器交叉编译。

## 发布

发布安装包前先配置 GitHub Actions：

| 类型 | 名称 | 值 |
| --- | --- | --- |
| Repository variable | `MANAGED_LLM_BASE_URL` | `https://growthagent-guikesong.zeabur.app/api/v1/managed-llm` |
| Repository variable | `MANAGED_LLM_MODEL` | `deepseek-v4-flash` |
| Repository secret | `MANAGED_LLM_GATEWAY_TOKEN` | 与托管 API 相同的随机网关 Token，不能使用 DeepSeek Key |

托管 API 需要设置 `LLM_API_KEY`、`LLM_SETTINGS_LOCKED=true`、`MANAGED_LLM_GATEWAY_ENABLED=true` 与同一个 `MANAGED_LLM_GATEWAY_TOKEN`。完整清单见 [运行手册](docs/runbook.md)。缺少上述发布变量时，Release 工作流会直接停止，避免再次发布只带 Mock 的安装包。

推送 `v*` 标签后，GitHub Actions 会自动：

1. 构建 API 与 Web 的 `linux/amd64`、`linux/arm64` GHCR 镜像；
2. 交叉编译 Windows、macOS 与 Linux 启动器；
3. 生成 SHA-256 校验文件并创建 GitHub Release。

| 平台 | 最新安装包 |
| --- | --- |
| Windows x64 | [GrowthAgent-Windows-x64.exe](https://github.com/super-xinz/Growth/releases/latest/download/GrowthAgent-Windows-x64.exe) |
| macOS Apple Silicon | [在最新版本中选择 arm64 包](https://github.com/super-xinz/Growth/releases/latest) |
| macOS Intel | [在最新版本中选择 x64 包](https://github.com/super-xinz/Growth/releases/latest) |
| Linux x64 | [在最新版本中选择 Linux x64 包](https://github.com/super-xinz/Growth/releases/latest) |
| 校验文件 | [SHA256SUMS.txt](https://github.com/super-xinz/Growth/releases/latest/download/SHA256SUMS.txt) |

查看 [全部版本与下载](https://github.com/super-xinz/Growth/releases)。

## 第三方服务

小红书浏览器自动化由外部项目 [`xpzouying/xiaohongshu-mcp`](https://github.com/xpzouying/xiaohongshu-mcp) 的 Docker 镜像提供。其源码不内嵌在本仓库中，也不自动继承本项目许可证。使用前请自行检查上游条款和平台规则，详见 [第三方声明](THIRD_PARTY_NOTICES.md)。

上游镜像当前以 `linux/amd64` 运行；Apple Silicon 上由 Docker Desktop 兼容执行，首次启动和浏览器操作可能稍慢。

## 参与贡献

欢迎提交错误修复、文档改进和功能建议：

- 阅读 [贡献指南](CONTRIBUTING.md)；
- 提交 [Bug 报告](https://github.com/super-xinz/Growth/issues/new?template=bug_report.yml)；
- 提交 [功能建议](https://github.com/super-xinz/Growth/issues/new?template=feature_request.yml)；
- 在 Pull Request 中说明修改范围与验证结果。

## 许可与使用责任

本项目自有代码使用 [Apache License 2.0](LICENSE)，第三方项目不自动继承本项目许可证。

请仅使用你有权运营的账号，并遵守平台规则、当地法律与适用的隐私义务。本项目不提供规避风控、批量骚扰或隐藏推广关系的能力。
