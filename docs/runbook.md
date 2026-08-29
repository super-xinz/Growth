# Runbook

- 产品分析超时：系统会把网页证据压缩到 16,000 字符并给模型 150 秒。在“设置 → 模型服务”检查 API 地址、模型名称和额度。
- 产品分析 401/403/404/429：界面会分别显示密钥、模型名或频率错误，不再统一显示“模型不可用”。
- 智能搜索超时：账号不一定掉线。先看 `/account`；搜索浏览器 55 秒熔断，API 75 秒返回，不会再卡 5 分钟。
- 自动任务显示 `ATTENTION`：保留具体错误；连续三次会转为 `PAUSED_SAFETY`。
- 机会显示“发布状态待确认”：外部请求响应不确定，系统不会重试。到小红书原文人工核对是否已发布。
- 紧急停止：设置 `GLOBAL_KILL_SWITCH=true` 并重启 API 与 worker。
- 公网 Demo：设置 `PUBLIC_DEMO_MODE=true`，后端会拒绝所有写请求以及账号、OAuth 和二维码等敏感读取请求。
- 只有部署在可信认证代理之后时，才可设置 `ALLOW_PUBLIC_MUTATIONS=true`；不要在无认证公网实例中启用。
- 前端保存的模型密钥无法读取：确认 `ENCRYPTION_KEY` 没有变化。如密钥已丢失，需在设置页重新填写 API Key。
- Apple Silicon 上小红书服务启动较慢：上游镜像以 `linux/amd64` 兼容模式运行，确保 Docker Desktop 已启用 x86/amd64 仿真。

## 托管模型上线配置

托管 API 与 Worker 设置以下服务端环境变量；`LLM_API_KEY` 只能放在 Zeabur/部署平台的 Secret 中：

```dotenv
LLM_PROVIDER=openai
LLM_API_KEY=<DeepSeek 服务端 Key>
LLM_BASE_URL=https://api.deepseek.com
LLM_STRONG_MODEL=deepseek-v4-flash
LLM_ENABLE_THINKING=false
LLM_SETTINGS_LOCKED=true
LLM_DISPLAY_NAME="GrowthAgent AI"
MANAGED_LLM_GATEWAY_ENABLED=true
MANAGED_LLM_GATEWAY_TOKEN=<独立随机网关 Token>
MANAGED_LLM_REQUESTS_PER_MINUTE=12
MANAGED_LLM_REQUESTS_PER_DAY=200
MANAGED_LLM_GLOBAL_REQUESTS_PER_DAY=10000
MANAGED_LLM_MAX_INPUT_CHARS=80000
MANAGED_LLM_MAX_OUTPUT_TOKENS=5000
```

GitHub Actions 同时设置：

- Variable `MANAGED_LLM_BASE_URL=https://growthagent-guikesong.zeabur.app/api/v1/managed-llm`
- Variable `MANAGED_LLM_MODEL=deepseek-v4-flash`
- Secret `MANAGED_LLM_GATEWAY_TOKEN=<与托管 API 相同的网关 Token>`

网关 Token 会进入公开安装包，作用仅是撤销、版本隔离和基础访问控制；真正的费用保护依赖服务端限流。它不能与 DeepSeek Key 相同。轮换时先更新托管 API，再更新 GitHub Secret 并发布新版本；新启动器会更新此前由系统托管的本机配置，但不会覆盖用户自己的模型配置。

## 小红书登录边界

- 本机安装版：用户在“设置 → 小红书账号”中本人扫码，Cookie 只进入本机 Docker volume。
- 公开 Demo：不显示二维码、不读取访问者 Cookie，只提供本地版下载入口。
- 当前 API 和小红书浏览器服务是单用户架构。若要让公网网页同时服务多个用户，必须先增加用户认证、数据库租户隔离，并为每个租户隔离小红书浏览器会话；在此之前不要开启 `ALLOW_PUBLIC_MUTATIONS=true`。

## 安装包签名

- macOS 正式分发需要 Developer ID Application 证书、Apple Team ID 和公证凭证；签名与 `notarytool` 公证应在 Release 工作流中完成。
- Windows 正式分发需要受信任的代码签名证书或 Azure Trusted Signing；当前未签名版本会触发 SmartScreen。
- 在证书配置完成前，Release 只能作为测试版分发，并保留 `SHA256SUMS.txt` 供下载后校验。
