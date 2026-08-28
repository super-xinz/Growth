from typing import Any

import httpx

from .config import get_settings


class XiaohongshuError(RuntimeError):
    pass


class XiaohongshuClient:
    def __init__(self, base_url: str | None = None, *, transport=None):
        self._client = httpx.AsyncClient(
            base_url=(base_url or get_settings().xiaohongshu_mcp_url).rstrip("/"),
            timeout=httpx.Timeout(
                get_settings().xiaohongshu_search_timeout_seconds,
                connect=5.0,
            ),
            transport=transport,
        )

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, json: dict | None = None) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, json=json)
        except httpx.TimeoutException as error:
            if path == "/api/v1/login/status":
                message = "小红书登录状态检查超时；账号仍可能在线，请稍后重试"
            elif path == "/api/v1/search/notes":
                message = "小红书搜索页面响应超时；账号仍可能在线，请稍后重试"
            else:
                message = "小红书页面响应超时；本次操作未确认成功，请稍后检查"
            raise XiaohongshuError(
                f"{message}（{path}）"
            ) from error
        except httpx.ConnectError as error:
            raise XiaohongshuError(
                "小红书服务暂时无法连接，请确认 xiaohongshu-mcp 服务是否正在运行"
            ) from error
        except httpx.RequestError as error:
            raise XiaohongshuError(f"小红书服务请求失败：{error}") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise XiaohongshuError(
                f"小红书服务返回了无效响应（HTTP {response.status_code}，路径 {path}）"
            ) from error

        # MCP errors have a short public message in ``error`` and the actionable
        # browser failure in ``details``. Keep both; dropping details made every
        # reply failure look like the same generic 500 to the UI.
        if payload.get("success") is False or payload.get("error"):
            error_msg = self._error_message(payload, response.status_code)
            raise XiaohongshuError(self._friendly_error(error_msg, path))

        # Non-success HTTP status with no explicit error field
        if not response.is_success:
            error_msg = self._error_message(payload, response.status_code)
            raise XiaohongshuError(self._friendly_error(error_msg, path))

        return payload.get("data", payload)

    @staticmethod
    def _error_message(payload: dict[str, Any], status_code: int) -> str:
        primary = str(
            payload.get("error")
            or payload.get("message")
            or payload.get("detail")
            or f"HTTP {status_code}"
        )
        details = payload.get("details")
        if details is None:
            return primary
        detail_text = str(details).strip()
        if not detail_text or detail_text == primary:
            return primary
        return f"{primary}：{detail_text}"

    @staticmethod
    def _friendly_error(raw: str, path: str) -> str:
        """Translate common MCP errors into user-friendly Chinese messages."""
        lower = raw.lower()
        if "rate" in lower or "频" in lower or "too many" in lower or "limit" in lower:
            return "操作过于频繁，请稍后再试"
        if "login" in lower or "cookie" in lower or "登录" in lower or "auth" in lower:
            return "小红书登录状态已失效，请重新扫码登录"
        if "not found" in lower or "404" in lower:
            return f"目标内容不存在或已被删除（{path}）"
        if "forbidden" in lower or "403" in lower or "权限" in lower:
            return "账号可能被限制，请检查小红书账号状态"
        return f"{raw}（{path}）"

    async def health(self):
        return await self._request("GET", "/health")

    async def login_status(self):
        return await self._request("GET", "/api/v1/login/status")

    async def login_qrcode(self):
        return await self._request("GET", "/api/v1/login/qrcode")

    async def reset_login(self):
        return await self._request("DELETE", "/api/v1/login/cookies")

    async def me(self):
        return await self._request("GET", "/api/v1/user/me")

    async def search_feeds(self, keyword: str, filters: dict | None = None):
        return await self._request(
            "POST", "/api/v1/feeds/search", json={"keyword": keyword, "filters": filters or {}}
        )

    async def feed_detail(self, feed_id: str, xsec_token: str):
        return await self._request(
            "POST",
            "/api/v1/feeds/detail",
            json={"feed_id": feed_id, "xsec_token": xsec_token, "load_all_comments": False},
        )

    async def comment(self, feed_id: str, xsec_token: str, content: str):
        return await self._request(
            "POST",
            "/api/v1/feeds/comment",
            json={"feed_id": feed_id, "xsec_token": xsec_token, "content": content},
        )

    async def reply(
        self,
        feed_id: str,
        xsec_token: str,
        content: str,
        *,
        comment_id: str = "",
        user_id: str = "",
    ):
        return await self._request(
            "POST",
            "/api/v1/feeds/comment/reply",
            json={
                "feed_id": feed_id,
                "xsec_token": xsec_token,
                "content": content,
                "comment_id": comment_id,
                "user_id": user_id,
            },
        )
