# Security Policy

## Supported versions

只对最新 GitHub Release 和 `main` 分支提供安全修复。

## Reporting a vulnerability

请使用 GitHub 仓库的 **Security → Report a vulnerability** 私密报告功能。不要在公开 Issue 中提交 API Key、Cookie、数据库备份、完整日志或可直接利用的漏洞细节。

报告请包含影响范围、复现条件、受影响版本和建议修复方式。维护者确认前，请不要公开披露。

## Deployment boundary

ThreadPilot 当前是单用户、本地优先应用：

- 只应绑定 `127.0.0.1` 或置于可信反向代理和认证层之后；
- API 本身不提供多用户身份认证，不应直接暴露到公网；
- `.env`、数据库、Docker volumes 和小红书 Cookie 必须视为敏感数据；
- `ENCRYPTION_KEY` 丢失后，前端保存的模型密钥无法恢复；泄露后应立即轮换所有已保存密钥。

## Secret handling

- 不要提交 `.env`、`.env~`、密钥文件或 Cookie 数据；
- 前端只提供配置表单，模型密钥由后端加密保存；
- API 响应、日志和错误信息不得包含完整密钥；
- 生产部署必须替换示例中的 `SECRET_KEY`、`ENCRYPTION_KEY` 和数据库密码。
