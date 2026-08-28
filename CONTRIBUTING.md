# Contributing

感谢改进 ThreadPilot。提交代码前请先搜索现有 Issue，并让每个 Pull Request 聚焦一个问题。

## Local setup

```bash
cp .env.example .env
make dev
```

不要在测试或截图中使用真实 API Key、Cookie、账号或用户内容。

## Required checks

```bash
make test
make lint
make typecheck
make build
```

新增数据库字段必须提供 Alembic migration；新增外部写操作必须说明幂等性、失败语义、频控与人工停止方式；新增依赖必须确认许可证兼容性。

## Pull requests

- 描述问题、方案、风险和验证结果；
- UI 修改附桌面与移动端截图，但不得包含私人数据；
- 安全问题使用私密漏洞报告，不要提交公开 Issue；
- 提交即表示你有权按 Apache-2.0 许可贡献代码。
