import httpx
import pytest

from app.xiaohongshu_client import XiaohongshuClient, XiaohongshuError


def transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_login_search_and_detail_contract():
    def handler(request: httpx.Request):
        if request.url.path == "/api/v1/login/status":
            return httpx.Response(
                200, json={"success": True, "data": {"is_logged_in": True, "username": "测试号"}}
            )
        if request.url.path == "/api/v1/login/qrcode":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "timeout": "300",
                        "is_logged_in": False,
                        "img": "data:image/png;base64,abc",
                    },
                },
            )
        if request.url.path == "/api/v1/feeds/search":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"feeds": [{"id": "feed-1", "xsec_token": "token-1"}]},
                },
            )
        if request.url.path == "/api/v1/feeds/detail":
            return httpx.Response(200, json={"success": True, "data": {"feed": {"id": "feed-1"}}})
        return httpx.Response(404)

    client = XiaohongshuClient(transport=transport(handler))
    assert (await client.login_status())["is_logged_in"] is True
    assert (await client.login_qrcode())["img"].startswith("data:image/png")
    assert (await client.search_feeds("客户研究"))["feeds"][0]["id"] == "feed-1"
    assert (await client.feed_detail("feed-1", "token-1"))["feed"]["id"] == "feed-1"
    await client.close()


@pytest.mark.asyncio
async def test_write_contract_and_remote_error():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path == "/api/v1/feeds/comment":
            return httpx.Response(200, json={"success": True, "data": {"feed_id": "feed-1"}})
        if request.url.path == "/api/v1/feeds/comment/reply":
            return httpx.Response(500, json={"error": "页面结构变化", "code": "XHS_FAILED"})
        return httpx.Response(404)

    client = XiaohongshuClient(transport=transport(handler))
    assert (await client.comment("feed-1", "token", "测试评论"))["feed_id"] == "feed-1"
    with pytest.raises(XiaohongshuError, match="页面结构变化"):
        await client.reply("feed-1", "token", "测试回复", comment_id="comment-1")
    assert calls.count("/api/v1/feeds/comment/reply") == 1
    await client.close()


@pytest.mark.asyncio
async def test_remote_error_includes_actionable_mcp_details():
    def handler(request: httpx.Request):
        return httpx.Response(
            500,
            json={
                "error": "回复评论失败",
                "code": "REPLY_COMMENT_FAILED",
                "details": "提交按钮一直不可用",
            },
        )

    client = XiaohongshuClient(transport=transport(handler))
    with pytest.raises(XiaohongshuError, match="提交按钮一直不可用"):
        await client.reply("feed-1", "token", "测试回复", comment_id="comment-1")
    await client.close()
