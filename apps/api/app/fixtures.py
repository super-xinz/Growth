import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from sqlalchemy import select
from .config import get_settings
from .database import SessionLocal, engine
from .models import Base, Candidate, Product, ProductSubreddit, QueryTerm, RedditContent, Subreddit
from .services import generate_reply, run_policy

INTENTS = [
    ("alternative", "ASKING_FOR_ALTERNATIVE"),
    ("recommend", "SEEKING_RECOMMENDATION"),
    ("looking for", "SEEKING_RECOMMENDATION"),
    ("how do", "ASKING_HOW_TO_SOLVE"),
]


async def load(path: str, product_id: str | None = None):
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    data = json.load(open(path, encoding="utf-8"))
    async with SessionLocal() as db:
        product = (
            await db.get(Product, product_id)
            if product_id
            else await db.scalar(select(Product).order_by(Product.created_at))
        )
        if not product:
            raise RuntimeError("Create a product before importing fixtures")
        terms = [
            x.lower()
            for x in (
                await db.scalars(
                    select(QueryTerm.term).where(
                        QueryTerm.product_id == product.id, QueryTerm.status == "ACTIVE"
                    )
                )
            ).all()
        ]
        for item in data:
            text = f"{item.get('title', '')} {item.get('body', '')}".lower()
            digest = hashlib.sha256(text.encode()).hexdigest()
            content = await db.scalar(
                select(RedditContent).where(
                    RedditContent.reddit_fullname == item["reddit_fullname"]
                )
            )
            if not content:
                content_data = dict(item)
                created_utc = content_data.pop("created_utc", None)
                content = RedditContent(
                    **content_data,
                    content_hash=digest,
                    created_utc=datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
                    if created_utc
                    else datetime.now(timezone.utc),
                )
                db.add(content)
                await db.flush()
            hits = [t for t in terms if t and t in text]
            intent = next(
                (label for phrase, label in INTENTS if phrase in text), "GENERAL_DISCUSSION"
            )
            intent_score = 1 if intent != "GENERAL_DISCUSSION" else 0
            fit = min(1, len(hits) / 3)
            opportunity = (
                0.25 * fit
                + 0.2 * intent_score
                + 0.1 * min(1, item.get("score", 0) / 20)
                + 0.1 * min(1, item.get("num_comments", 0) / 15)
            )
            if not await db.scalar(
                select(Candidate).where(
                    Candidate.product_id == product.id, Candidate.reddit_content_id == content.id
                )
            ):
                sub = await db.scalar(select(Subreddit).where(Subreddit.name == item["subreddit"]))
                if not sub:
                    sub = Subreddit(
                        name=item["subreddit"],
                        title=f"r/{item['subreddit']}",
                        rules_json={"promotion": "fixture unknown"},
                    )
                    db.add(sub)
                    await db.flush()
                if not await db.scalar(
                    select(ProductSubreddit).where(
                        ProductSubreddit.product_id == product.id,
                        ProductSubreddit.subreddit_id == sub.id,
                    )
                ):
                    db.add(
                        ProductSubreddit(
                            product_id=product.id,
                            subreddit_id=sub.id,
                            status="ALLOW_AUTOREPLY",
                            community_score=0.7,
                            promotion_tolerance=0.35,
                        )
                    )
                db.add(
                    Candidate(
                        product_id=product.id,
                        reddit_content_id=content.id,
                        recall_sources=hits or ["fixture"],
                        bm25_score=fit,
                        intent_label=intent,
                        intent_confidence=0.9 if intent_score else 0.6,
                        opportunity_score=round(opportunity, 3),
                        risk_score=0,
                    )
                )
        await db.commit()
        candidates = (
            await db.scalars(select(Candidate).where(Candidate.product_id == product.id))
        ).all()
        for candidate in candidates:
            decision = await run_policy(db, candidate, get_settings())
            await generate_reply(db, candidate, decision)
    print(f"Imported {len(data)} Reddit fixtures for {product.id}")


if __name__ == "__main__":
    asyncio.run(load(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
