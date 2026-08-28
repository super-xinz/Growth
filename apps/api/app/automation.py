"""Guarded, low-frequency Xiaohongshu discovery and publishing loop."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .models import Product, XiaohongshuOpportunity, now
from .xiaohongshu_client import XiaohongshuClient, XiaohongshuError
from .xiaohongshu_service import (
    auto_search_keywords,
    generate_qualifying_drafts,
    import_search_opportunities,
    publish_best_qualifying_opportunity,
)

logger = logging.getLogger(__name__)


class AutomationError(RuntimeError):
    pass


async def run_product_automation(
    db: AsyncSession,
    product_id: str,
    provider,
    settings: Settings,
    *,
    force: bool = False,
) -> dict:
    """Run one product cycle: 3 keywords, 2 details each, at most 1 comment."""
    product = await db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise AutomationError("产品不存在或已删除")
    if not product.autopublish_enabled and not force:
        return {"status": "PAUSED", "searched": 0, "imported": 0, "published": None}
    if settings.global_kill_switch:
        raise AutomationError("全局停止开关已开启")

    current = now()
    product.automation_status = "RUNNING"
    product.automation_error = None
    # Claim the next slot before doing slow external work. This prevents the beat
    # scheduler from launching the same product twice.
    product.next_auto_search_at = current + timedelta(hours=product.search_interval_hours)
    await db.commit()

    client = XiaohongshuClient()
    imported: list[XiaohongshuOpportunity] = []
    keywords: list[str] = []
    try:
        login = await client.login_status()
        if not login.get("is_logged_in"):
            raise XiaohongshuError("小红书登录状态已失效，请重新扫码登录")

        keywords = await auto_search_keywords(
            db,
            product.id,
            provider,
            limit=product.keywords_per_run,
        )
        if not keywords:
            raise AutomationError("Product Brain 中没有可用的中文需求关键词，请重新分析产品")

        search_errors: list[str] = []
        for keyword in keywords:
            try:
                imported.extend(
                    await import_search_opportunities(
                        db,
                        product.id,
                        client,
                        keyword,
                        provider,
                        detail_limit=product.details_per_keyword,
                    )
                )
            except XiaohongshuError as error:
                search_errors.append(f"{keyword}：{error}")
                logger.warning("Auto search failed for %s: %s", keyword, error)
                # A browser timeout usually poisons the current browser session;
                # stop this cycle instead of hammering two more queries.
                if "超时" in str(error) or "无法连接" in str(error):
                    break

        if not imported and search_errors:
            raise AutomationError(search_errors[0])

        unique_ids = list(dict.fromkeys(row.id for row in imported))
        generated = await generate_qualifying_drafts(
            db,
            unique_ids,
            provider,
            threshold=product.auto_score_threshold,
            risk_threshold=product.auto_risk_threshold,
        )
        published = await publish_best_qualifying_opportunity(
            db,
            product,
            client,
            kill_switch=settings.global_kill_switch,
            opportunity_ids=unique_ids,
        )

        product.last_auto_search_at = current
        product.automation_status = "HEALTHY"
        product.automation_error = None
        product.automation_failures = 0
        await db.commit()
        return {
            "status": "HEALTHY",
            "keywords": keywords,
            "searched": len(keywords),
            "imported": len(unique_ids),
            "drafted": generated,
            "published": published.id if published else None,
            "next_run_at": product.next_auto_search_at,
        }
    except Exception as error:
        await db.rollback()
        product = await db.get(Product, product_id)
        if product:
            product.automation_failures += 1
            product.automation_error = str(error)[:2000]
            if product.automation_failures >= 3:
                product.automation_status = "PAUSED_SAFETY"
                product.autopublish_enabled = False
            else:
                product.automation_status = "ATTENTION"
            await db.commit()
        if isinstance(error, AutomationError):
            raise
        raise AutomationError(str(error)) from error
    finally:
        await client.close()


async def run_due_automations(db: AsyncSession, provider, settings: Settings) -> list[dict]:
    current = now()
    products = list(
        (
            await db.scalars(
                select(Product)
                .where(
                    Product.deleted_at.is_(None),
                    Product.autopublish_enabled.is_(True),
                    (
                        Product.next_auto_search_at.is_(None)
                        | (Product.next_auto_search_at <= current)
                    ),
                )
                .order_by(Product.next_auto_search_at)
            )
        ).all()
    )
    results = []
    for product in products:
        try:
            results.append(
                await run_product_automation(db, product.id, provider, settings)
            )
        except AutomationError as error:
            results.append({"status": "ATTENTION", "product_id": product.id, "error": str(error)})
    return results
