import hashlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main as main_module
from app.database import get_db
from app.main import app
from app.models import Base, Candidate, ProductSource, RedditContent, TrackingLink
from app.providers import MockLLMProvider


@pytest_asyncio.fixture
async def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "growthagent-smoke.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(main_module, "provider_for", lambda _settings: MockLLMProvider())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_guarded_workflow(api_client):
    client, session_factory = api_client
    assert (await client.get("/health")).status_code == 200

    created = await client.post(
        "/v1/products",
        json={
            "name": "Smoke Pilot",
            "website_url": "https://example.com",
            "daily_reply_limit": 2,
        },
    )
    assert created.status_code == 201
    assert created.json()["disclosure_template"] == "自家做的"
    assert created.json()["autopublish_enabled"] is True
    assert created.json()["daily_reply_limit"] == 2
    product_id = created.json()["id"]

    content = (
        "Smoke Pilot coordinates verified customer research workflows for small product teams. "
        "It finds relevant discussions, preserves source evidence, and records safety decisions. "
        "Teams use it to reduce irrelevant outreach and keep every recommendation auditable."
    )
    async with session_factory() as db:
        db.add(
            ProductSource(
                product_id=product_id,
                source_type="website",
                url="https://example.com",
                title="Smoke Pilot",
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
        )
        await db.commit()

    brain = await client.post(f"/v1/products/{product_id}/build-brain")
    assert brain.status_code == 200
    brain_body = brain.json()["brain"]
    assert brain_body["supported_claims"] and brain_body["query_graph"]["direct_terms"]
    assert (
        await client.patch(f"/v1/products/{product_id}/brain", json={"product_name": "bad"})
    ).status_code == 422
    assert (
        await client.patch(f"/v1/products/{product_id}/brain", json=brain_body)
    ).status_code == 200

    discovered = await client.post(f"/v1/products/{product_id}/discover-subreddits")
    assert discovered.status_code == 200 and discovered.json()
    subreddit_id = discovered.json()[0]["id"]
    assert (
        await client.patch(
            f"/v1/products/{product_id}/subreddits/{subreddit_id}",
            json={"status": "ALLOW_AUTOREPLY"},
        )
    ).status_code == 200
    assert (
        await client.post(f"/v1/products/{product_id}/subreddits/{subreddit_id}/refresh-rules")
    ).status_code == 200

    async with session_factory() as db:
        reddit = RedditContent(
            reddit_fullname="t3_smoke",
            content_type="submission",
            subreddit=discovered.json()[0]["name"],
            author_name="tester",
            title="Looking for a safer customer research workflow",
            body="Can anyone recommend a transparent tool with audit evidence?",
            permalink="https://reddit.com/r/test/comments/smoke",
            content_hash="smoke",
        )
        db.add(reddit)
        await db.flush()
        candidate = Candidate(
            product_id=product_id,
            reddit_content_id=reddit.id,
            recall_sources=["recommend", "audit evidence"],
            intent_label="SEEKING_RECOMMENDATION",
            intent_confidence=0.95,
            opportunity_score=0.82,
            risk_score=0.05,
        )
        db.add(candidate)
        await db.commit()
        candidate_id = candidate.id

    assert (await client.get(f"/v1/opportunities/{candidate_id}")).status_code == 200
    decision = await client.get(f"/v1/opportunities/{candidate_id}/decision")
    assert decision.status_code == 200
    reply = await client.get(f"/v1/opportunities/{candidate_id}/generated-reply")
    assert reply.status_code == 200 and reply.json()["body"]
    published = await client.post(f"/v1/opportunities/{candidate_id}/publish")
    assert published.status_code == 200 and published.json()["status"] == "SHADOW_RECORDED"
    assert (await client.post(f"/v1/opportunities/{candidate_id}/publish")).json()[
        "id"
    ] == published.json()["id"]

    conversations = await client.get(f"/v1/products/{product_id}/conversations")
    assert conversations.status_code == 200 and len(conversations.json()) == 1
    conversation_id = conversations.json()[0]["id"]
    followup = await client.post(
        f"/v1/conversations/{conversation_id}/followup",
        json={"body": "Can you send me the website link?"},
    )
    assert followup.status_code == 200 and followup.json()["state"] == "LINK_SHARED"

    async with session_factory() as db:
        tracking_link = await db.get(
            TrackingLink,
            (await db.scalar(select(TrackingLink.id).where(TrackingLink.product_id == product_id))),
        )
        short_code = tracking_link.short_code
    redirect = await client.get(f"/c/{short_code}", follow_redirects=False)
    assert (
        redirect.status_code in {302, 307} and "utm_source=reddit" in redirect.headers["location"]
    )

    for event in ("signup", "activated"):
        assert (
            await client.post(
                "/v1/events",
                json={"event": event, "product_id": product_id, "anonymous_id": "smoke-user"},
            )
        ).status_code == 200
    analytics = (await client.get(f"/v1/products/{product_id}/analytics/overview")).json()
    assert (
        analytics["signups"] == 1
        and analytics["activations"] == 1
        and analytics["conversations"] == 1
    )
    assert (await client.get(f"/v1/products/{product_id}/analytics/subreddits")).status_code == 200
    assert (await client.get(f"/v1/products/{product_id}/analytics/intents")).status_code == 200
    assert (
        await client.get(f"/v1/products/{product_id}/analytics/reply-strategies")
    ).status_code == 200
    assert (await client.get(f"/v1/products/{product_id}/audit-log")).json()
    assert (await client.get(f"/v1/products/{product_id}/risk-events")).status_code == 200

    account = await client.post("/v1/reddit/accounts", json={"username": "growthagent-smoke"})
    assert account.status_code == 201
    assert len((await client.get("/v1/reddit/accounts")).json()) == 1
    assert (await client.delete(f"/v1/reddit/accounts/{account.json()['id']}")).status_code == 200
    assert (await client.get("/v1/reddit/oauth/start")).status_code == 200
    assert (await client.get("/v1/tracking/sdk.js")).status_code == 200
    assert (await client.post(f"/v1/products/{product_id}/start")).json()[
        "status"
    ] == "SHADOW_RUNNING"
    assert (await client.post(f"/v1/products/{product_id}/pause")).json()["status"] == "PAUSED"
    assert (await client.post(f"/v1/products/{product_id}/autopublish/enable")).json()[
        "autopublish_enabled"
    ] is True
    assert (await client.post(f"/v1/products/{product_id}/autopublish/disable")).json()[
        "autopublish_enabled"
    ] is False
    assert (await client.post(f"/v1/conversations/{conversation_id}/stop")).json()[
        "status"
    ] == "CLOSED"
    assert (await client.post("/v1/admin/kill-switch/enable")).status_code == 200
    assert (await client.post("/v1/admin/kill-switch/disable")).status_code == 200
