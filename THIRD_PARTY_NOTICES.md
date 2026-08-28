# Third-party notices

ThreadPilot 使用开源语言运行时、Python/Node/Go 依赖和容器镜像。各依赖继续受其自身许可证约束。

## Xiaohongshu MCP

- Project: <https://github.com/xpzouying/xiaohongshu-mcp>
- Image: `xpzouying/xiaohongshu-mcp:latest`
- Runtime platform: `linux/amd64`（ARM 主机通过 Docker 兼容层运行）
- Role: 本地浏览器登录、搜索和评论接口

该项目当前没有在本仓库中附带可确认的许可证文本，因此 ThreadPilot **不再分发其源码，也不声称其代码受 Apache-2.0 许可**。Docker Compose 仅引用上游发布的镜像。使用者应自行核对上游条款、小红书平台规则及所在地区法律。

如果上游镜像不可用或其条款不适合你的用途，请移除 `xiaohongshu-mcp` 服务并实现兼容的本地接口。
