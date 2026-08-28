# Architecture

ThreadPilot 只有一条主链路：`Product → Discovery → Qualified reply → Guarded publish`。

- FastAPI：产品资料、Product Brain、机会评分与自动发布领域逻辑；
- Celery Beat：每 5 分钟检查到期产品；产品自己的搜索间隔默认为 3 小时；
- PostgreSQL：产品、来源、Brain、公开内容、机会与自动化状态；
- Redis：Celery broker / result backend；
- Next.js：工作台、账号、产品任务和发现结果；
- xiaohongshu-mcp：扫码登录、公开搜索、详情读取与单次评论/回复。
- 加密设置：浏览器只提交模型配置；API 使用 `ENCRYPTION_KEY` 加密后存入 PostgreSQL，worker 每次任务读取有效配置。

自动发布只接受模型评分，不接受启发式评分。评分模型异常时，候选最高 64 分。发布前再次验证登录、目标、冷却、日上限、机会分、风险分与全局停止开关。任何写请求异常都标记为 `PUBLISH_UNKNOWN`，不自动重试。
