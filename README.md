<div align="center">

<img src="docs/assets/growthagent-logo.svg" alt="GrowthAgent logo" width="88" height="88" />

<h1>GrowthAgent</h1>

<p><strong>让每个好产品，都能找到它的第一批用户。</strong></p>

<p>本地优先、可自托管的 AI 获客工作台。理解产品、发现真实需求、判断机会并完成克制触达。</p>

<p>
  <a href="https://github.com/super-xinz/ThreadPilot/releases"><img src="https://img.shields.io/github/v/release/super-xinz/ThreadPilot?style=flat-square&amp;label=release" alt="Release" /></a>
  <a href="https://github.com/super-xinz/ThreadPilot/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/super-xinz/ThreadPilot/ci.yml?branch=main&amp;style=flat-square&amp;label=CI" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-EA0000?style=flat-square" alt="Apache 2.0 License" /></a>
  <a href="#快速开始"><img src="https://img.shields.io/badge/deployment-self--hosted-171717?style=flat-square" alt="Self-hosted" /></a>
</p>

<p>
  <a href="#快速开始">快速开始</a> ·
  <a href="#工作原理">工作原理</a> ·
  <a href="#核心能力">核心能力</a> ·
  <a href="#产品预览">产品预览</a> ·
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

### Windows 一键启动

需要预先安装并启动 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

1. 下载最新版 [ThreadPilot-Windows-x64.exe](https://github.com/super-xinz/ThreadPilot/releases/latest/download/ThreadPilot-Windows-x64.exe)；
2. 双击运行，启动器会自动生成本地密钥、拉取容器并等待服务就绪；
3. 浏览器将自动打开 `http://localhost:3000/dashboard`。

再次运行会更新并启动服务。停止服务：

```powershell
ThreadPilot-Windows-x64.exe --stop
```

> 当前启动器尚未进行商业代码签名，Windows SmartScreen 首次运行时可能提示来源未知。

### macOS、Linux 与开发者

需要 Git、Docker Desktop，或 Docker Engine + Compose v2。

```bash
git clone https://github.com/super-xinz/ThreadPilot.git
cd ThreadPilot
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
- **本地优先的数据边界**：模型密钥加密保存，小红书 Cookie 仅保存在本地数据卷。

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

启动后进入“设置 → 模型服务”，填写：

- OpenAI 兼容 API 地址；
- 模型名称；
- API Key；
- 可选的兼容接口思考模式。

API Key 通过本机 API 发送到后端，使用 `ENCRYPTION_KEY` 加密后存入数据库。读取设置时只返回“已配置”和末四位提示，明文不会返回浏览器，也不会进入 Next.js 构建产物或 Git。

未配置在线模型时默认使用 Mock，不会意外产生模型费用。

## 安全边界

GrowthAgent 当前面向本机或可信内网中的单用户部署。API 尚未提供多用户身份认证，**请勿将 3000、8000 或 18060 端口直接暴露到公网。**

- Docker 端口只绑定到 `127.0.0.1`，PostgreSQL 和 Redis 不映射到宿主机；
- 小红书 Cookie 保存在本地 Docker volume 或 `.xiaohongshu-data/`，并已被 Git 忽略；
- 发布、搜索和回复受分数阈值、风险阈值、冷却、日上限与全局停止开关约束；
- 外部写操作不自动重试，避免平台已接收但响应丢失时产生重复评论；
- `.env`、私钥、Cookie 和本地数据不会被提交到版本库。

完整说明见 [安全政策](SECURITY.md) 与 [运行手册](docs/runbook.md)。

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

推送 `v*` 标签后，GitHub Actions 会自动：

1. 构建 API 与 Web 的 `linux/amd64`、`linux/arm64` GHCR 镜像；
2. 交叉编译 Windows、macOS 与 Linux 启动器；
3. 生成 SHA-256 校验文件并创建 GitHub Release。

查看 [全部版本与下载](https://github.com/super-xinz/ThreadPilot/releases)。

## 第三方服务

小红书浏览器自动化由外部项目 [`xpzouying/xiaohongshu-mcp`](https://github.com/xpzouying/xiaohongshu-mcp) 的 Docker 镜像提供。其源码不内嵌在本仓库中，也不自动继承本项目许可证。使用前请自行检查上游条款和平台规则，详见 [第三方声明](THIRD_PARTY_NOTICES.md)。

上游镜像当前以 `linux/amd64` 运行；Apple Silicon 上由 Docker Desktop 兼容执行，首次启动和浏览器操作可能稍慢。

## 参与贡献

欢迎提交错误修复、文档改进和功能建议：

- 阅读 [贡献指南](CONTRIBUTING.md)；
- 提交 [Bug 报告](https://github.com/super-xinz/ThreadPilot/issues/new?template=bug_report.yml)；
- 提交 [功能建议](https://github.com/super-xinz/ThreadPilot/issues/new?template=feature_request.yml)；
- 在 Pull Request 中说明修改范围与验证结果。

## 许可与使用责任

本项目自有代码使用 [Apache License 2.0](LICENSE)，第三方项目不自动继承本项目许可证。

请仅使用你有权运营的账号，并遵守平台规则、当地法律与适用的隐私义务。本项目不提供规避风控、批量骚扰或隐藏推广关系的能力。
