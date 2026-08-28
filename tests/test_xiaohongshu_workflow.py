import pytest
from types import SimpleNamespace

from app.xiaohongshu_service import normalize_search_results, opportunity_records
from app.xiaohongshu_service import (
    ensure_daily_quota,
    import_search_opportunities,
    validate_xiaohongshu_draft,
    XiaohongshuTargetError,
    execute_xiaohongshu_action,
    generate_qualifying_drafts,
    manually_generate_and_publish_opportunity,
    publish_best_qualifying_opportunity,
)


def sample_search_payload():
    return {
        "feeds": [
            {
                "id": "note-1",
                "xsecToken": "xsec-1",
                "noteCard": {
                    "displayTitle": "怎样找到真正有需求的用户",
                    "user": {"userId": "user-1", "nickname": "产品小王"},
                    "interactInfo": {"likedCount": "12", "commentCount": "2"},
                },
            },
            {
                "id": "note-1",
                "xsecToken": "xsec-new",
                "noteCard": {"displayTitle": "重复结果"},
            },
            {
                "id": "recommendation-placeholder",
                "modelType": "rec_query",
                "xsecToken": "not-a-note-token",
                "noteCard": {"displayTitle": ""},
            },
        ]
    }


def test_search_normalization_keeps_xsec_token_and_suppresses_duplicates():
    rows = normalize_search_results(sample_search_payload(), keyword="用户研究")

    assert len(rows) == 1
    assert rows[0]["platform_content_id"] == "note-1"
    assert rows[0]["xsec_token"] == "xsec-1"
    assert rows[0]["title"] == "怎样找到真正有需求的用户"
    assert rows[0]["author_id"] == "user-1"
    assert rows[0]["source_keyword"] == "用户研究"


def test_detail_creates_note_and_comment_opportunities_with_stable_keys():
    detail = {
        "note": {
            "noteId": "note-1",
            "xsecToken": "xsec-1",
            "title": "有没有好用的用户研究工具",
            "desc": "团队访谈整理太慢了，求推荐。",
            "user": {"userId": "author-1", "nickname": "创业者"},
        },
        "comments": {
            "list": [
                {
                    "id": "comment-1",
                    "noteId": "note-1",
                    "content": "我也想知道，有没有能自动整理证据的？",
                    "userInfo": {"userId": "commenter-1", "nickname": "同问"},
                }
            ]
        },
    }

    rows = opportunity_records({"feed_id": "note-1", "data": detail}, source_keyword="用户研究")

    assert [row["target_type"] for row in rows] == ["NOTE", "COMMENT"]
    assert rows[0]["dedupe_key"] == "xiaohongshu:NOTE:note-1"
    assert rows[1]["dedupe_key"] == "xiaohongshu:COMMENT:note-1:comment-1"
    assert rows[1]["parent_content_id"] == "note-1"
    assert rows[1]["author_id"] == "commenter-1"


class FakeXiaohongshuClient:
    async def search_feeds(self, keyword, filters=None):
        return sample_search_payload()

    async def feed_detail(self, feed_id, xsec_token):
        return {
            "data": {
                "note": {
                    "noteId": feed_id,
                    "xsecToken": xsec_token,
                    "title": "寻找用户研究工具",
                    "desc": "有没有可以保留证据、整理访谈的工具？",
                    "user": {"userId": "author-1", "nickname": "创业者"},
                },
                "comments": {
                    "list": [
                        {
                            "id": "comment-1",
                            "content": "同问，最好能自动整理。",
                            "userInfo": {"userId": "commenter-1", "nickname": "同问"},
                        }
                    ]
                },
            }
        }


@pytest.mark.asyncio
async def test_search_import_persists_once_and_suppresses_duplicate_targets(tmp_path):
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import (
        Base,
        Product,
        XiaohongshuContent,
        XiaohongshuOpportunity,
    )

    from app.providers import MockLLMProvider
    provider = MockLLMProvider()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'xhs.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        product = Product(name="测试产品", website_url="https://example.com")
        db.add(product)
        await db.commit()
        await import_search_opportunities(db, product.id, FakeXiaohongshuClient(), "用户研究", provider)
        await import_search_opportunities(db, product.id, FakeXiaohongshuClient(), "用户研究", provider)
        assert await db.scalar(select(func.count(XiaohongshuContent.id))) == 2
        assert await db.scalar(select(func.count(XiaohongshuOpportunity.id))) == 2
    await engine.dispose()


def test_draft_quality_rejects_false_affiliation_and_links():
    with pytest.raises(ValueError, match="身份声明"):
        validate_xiaohongshu_draft("我是 DeepSeek 的开发者，可以帮你解决。")
    with pytest.raises(ValueError, match="链接"):
        validate_xiaohongshu_draft("可以先按步骤排查，详情见 https://example.com")
    with pytest.raises(ValueError, match="25"):
        validate_xiaohongshu_draft("可以先保存出错截图和复现步骤，再通过应用内反馈提交。")
    assert validate_xiaohongshu_draft("先把高频问题归类会省很多")


def test_daily_quota_blocks_at_limit():
    ensure_daily_quota(2, 3)
    with pytest.raises(RuntimeError, match="评论上限"):
        ensure_daily_quota(3, 3)


class RefreshingClient:
    def __init__(self, *, include_comment=True, reject_stale=True):
        self.include_comment = include_comment
        self.reject_stale = reject_stale
        self.reply_calls = []
        self.comment_calls = []

    async def search_feeds(self, keyword, filters=None):
        return {
            "feeds": [
                {
                    "id": "note-1",
                    "modelType": "note",
                    "xsecToken": "fresh-token",
                    "noteCard": {"displayTitle": "目标笔记"},
                }
            ]
        }

    async def feed_detail(self, feed_id, xsec_token):
        from app.xiaohongshu_client import XiaohongshuError
        if self.reject_stale and xsec_token == "stale-token":
            raise XiaohongshuError("token expired")
        comments = []
        if self.include_comment:
            comments = [{"id": "comment-1", "content": "目标评论", "subComments": []}]
        return {
            "data": {
                "note": {"noteId": feed_id, "xsecToken": xsec_token},
                "comments": {"list": comments},
            }
        }

    async def reply(self, feed_id, xsec_token, content, *, comment_id="", user_id=""):
        self.reply_calls.append((feed_id, xsec_token, comment_id, user_id, content))
        return {"success": True}

    async def comment(self, feed_id, xsec_token, content):
        self.comment_calls.append((feed_id, xsec_token, content))
        return {"success": True}

    async def login_status(self):
        return {"is_logged_in": True}


@pytest.mark.asyncio
async def test_execute_refreshes_stale_token_and_writes_reply_once():
    """When stored token is expired, falls back to search and uses fresh token."""
    client = RefreshingClient(reject_stale=True)
    content = SimpleNamespace(
        target_type="COMMENT",
        platform_content_id="comment-1",
        parent_content_id="note-1",
        xsec_token="stale-token",
        source_keyword="用户研究",
        author_id="commenter-1",
    )

    await execute_xiaohongshu_action(client, content, "这是一条确认后的回复")

    assert client.reply_calls == [
        ("note-1", "fresh-token", "comment-1", "commenter-1", "这是一条确认后的回复")
    ]
    assert client.comment_calls == []


@pytest.mark.asyncio
async def test_execute_uses_stored_token_when_still_valid():
    """When stored token is still valid, skips re-search and uses it directly."""
    client = RefreshingClient(reject_stale=False)
    content = SimpleNamespace(
        target_type="COMMENT",
        platform_content_id="comment-1",
        parent_content_id="note-1",
        xsec_token="stale-token",
        source_keyword="用户研究",
        author_id="commenter-1",
    )

    await execute_xiaohongshu_action(client, content, "直接使用旧 token")

    assert client.reply_calls == [
        ("note-1", "stale-token", "comment-1", "commenter-1", "直接使用旧 token")
    ]
    assert client.comment_calls == []


@pytest.mark.asyncio
async def test_execute_blocks_when_target_comment_disappeared():
    client = RefreshingClient(include_comment=False, reject_stale=True)
    content = SimpleNamespace(
        target_type="COMMENT",
        platform_content_id="comment-1",
        parent_content_id="note-1",
        xsec_token="stale-token",
        source_keyword="用户研究",
    )

    with pytest.raises(XiaohongshuTargetError, match="目标评论已不存在"):
        await execute_xiaohongshu_action(client, content, "不会发布")
    assert client.reply_calls == []


class DraftProvider:
    def __init__(self):
        self.prompts = []

    async def generate_text(self, prompt):
        self.prompts.append(prompt)
        return "自家做的GrowthAgent正好管这个"


@pytest.mark.asyncio
async def test_high_score_owned_product_gets_durable_promotional_draft(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import (
        Base,
        Product,
        ProductBrainVersion,
        XiaohongshuContent,
        XiaohongshuOpportunity,
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'drafts.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        product = Product(
            name="GrowthAgent",
            website_url="https://example.com",
            is_owned=True,
            disclosure_template="我是产品团队成员",
        )
        content = XiaohongshuContent(
            dedupe_key="xiaohongshu:COMMENT:note:auto",
            target_type="COMMENT",
            platform_content_id="comment-auto",
            parent_content_id="note-auto",
            xsec_token="token",
            title="如何整理用户访谈",
            body="有没有能自动整理访谈证据的工具？",
        )
        db.add_all([product, content])
        await db.flush()
        db.add(
            ProductBrainVersion(
                product_id=product.id,
                version=1,
                is_current=True,
                brain_json={
                    "supported_claims": [
                        {"claim": "GrowthAgent 可以保存带来源的用户研究证据"}
                    ]
                },
            )
        )
        high = XiaohongshuOpportunity(
            product_id=product.id, content_id=content.id, opportunity_score=0.70
        )
        db.add(high)
        await db.commit()
        provider = DraftProvider()

        generated = await generate_qualifying_drafts(db, [high.id], provider, threshold=0.70)

        await db.refresh(high)
        assert generated == 1
        assert high.draft_status == "READY"
        assert "GrowthAgent" in high.draft_body
        assert "长度 6-25 个字符" in provider.prompts[0]
    await engine.dispose()


@pytest.mark.asyncio
async def test_auto_publish_sends_one_then_respects_cooldown(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import Base, Product, XiaohongshuContent, XiaohongshuOpportunity

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auto-publish.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        product = Product(
            name="GrowthAgent",
            website_url="https://example.com",
            autopublish_enabled=True,
            daily_reply_limit=2,
            auto_score_threshold=0.75,
            auto_risk_threshold=0.35,
            min_publish_interval_hours=4,
        )
        content = XiaohongshuContent(
            dedupe_key="xiaohongshu:COMMENT:note-1:comment-1",
            target_type="COMMENT",
            platform_content_id="comment-1",
            parent_content_id="note-1",
            xsec_token="stale-token",
            source_keyword="用户研究",
            author_id="user-1",
            body="有没有好用的工具？",
        )
        db.add_all([product, content])
        await db.flush()
        opportunity = XiaohongshuOpportunity(
            product_id=product.id,
            content_id=content.id,
            opportunity_score=0.86,
            risk_score=0.12,
            draft_body="自家做的GrowthAgent正好管这个",
            draft_status="READY",
        )
        db.add(opportunity)
        await db.commit()
        client = RefreshingClient(reject_stale=False)

        # An automation cycle with no freshly evaluated candidates must not drain
        # drafts left behind by an older prompt version.
        assert (
            await publish_best_qualifying_opportunity(
                db, product, client, opportunity_ids=[]
            )
            is None
        )
        published = await publish_best_qualifying_opportunity(
            db, product, client, opportunity_ids=[opportunity.id]
        )
        assert published and published.status == "COMMENTED"
        assert len(client.reply_calls) == 1

        # A second call inside the four-hour window is a no-op.
        assert await publish_best_qualifying_opportunity(db, product, client) is None
        assert len(client.reply_calls) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_manual_click_can_generate_and_publish_low_score_opportunity(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import (
        Base,
        Product,
        ProductBrainVersion,
        XiaohongshuContent,
        XiaohongshuOpportunity,
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'manual-publish.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        product = Product(
            name="GrowthAgent",
            website_url="https://example.com",
            is_owned=True,
            disclosure_template="自家做的",
        )
        content = XiaohongshuContent(
            dedupe_key="xiaohongshu:COMMENT:manual-note:manual-comment",
            target_type="COMMENT",
            platform_content_id="comment-1",
            parent_content_id="note-1",
            xsec_token="stale-token",
            source_keyword="用户研究",
            author_id="user-1",
            body="这个怎么整理？",
        )
        db.add_all([product, content])
        await db.flush()
        db.add(
            ProductBrainVersion(
                product_id=product.id,
                version=1,
                is_current=True,
                brain_json={
                    "supported_claims": [
                        {"claim": "GrowthAgent 可以整理带来源的用户反馈"}
                    ]
                },
            )
        )
        opportunity = XiaohongshuOpportunity(
            product_id=product.id,
            content_id=content.id,
            opportunity_score=0.20,
            risk_score=0.10,
        )
        db.add(opportunity)
        await db.commit()

        client = RefreshingClient(reject_stale=False)
        published = await manually_generate_and_publish_opportunity(
            db, opportunity.id, DraftProvider(), client
        )

        assert published.status == "COMMENTED"
        assert len(client.reply_calls) == 1
        assert client.reply_calls[0][-1] == "自家做的GrowthAgent正好管这个"
    await engine.dispose()
