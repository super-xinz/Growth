# Third-party notices

GrowthAgent 使用开源语言运行时、Python/Node/Go 依赖和容器镜像。各依赖继续受其自身许可证约束。

## Xiaohongshu MCP

- Project: <https://github.com/xpzouying/xiaohongshu-mcp>
- Upstream version: `v2.5.0` (`6583124dfda92312b6bc19a042a6acfae63fe498`)
- Base image: `xpzouying/xiaohongshu-mcp@sha256:88e2603f324f567e0a254ed7a1e24d632a16eccc30e84ef3fb887e34a03d0fe3`
- GrowthAgent image: `ghcr.io/super-xinz/growthagent-xiaohongshu`
- Runtime platform: `linux/amd64`（ARM 主机通过 Docker 兼容层运行）
- Role: 本地浏览器登录、搜索和评论接口
- Upstream license: Apache License 2.0
- Source modification: `infra/xiaohongshu-mcp/login-session.patch`

镜像构建会从上述固定提交取得源码、应用扫码会话补丁，并把上游 `LICENSE` 与 GrowthAgent 的 `MODIFICATIONS.md` 写入 `/usr/share/doc/growthagent-xiaohongshu/`。补丁修复扫码等待阻塞、登录 Cookie 变化识别，以及页面结构变化导致的登录状态误判。GrowthAgent 的修改同样按 Apache-2.0 提供。

该组件不代表小红书官方授权。使用者仍须遵守小红书平台规则、账号授权边界及所在地区法律；如果这些条件不适合你的用途，请移除 `xiaohongshu-mcp` 服务。
