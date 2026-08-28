from celery import Celery
import asyncio
from .config import get_settings
from .automation import run_due_automations
from .database import SessionLocal
from .providers import provider_for
from .product_lifecycle import purge_expired_products as purge_expired
from .runtime_settings import effective_settings

settings = get_settings()
celery_app = Celery(
    "growthagent", broker=settings.celery_broker_url, backend=settings.celery_result_backend
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    beat_schedule={
        "purge-expired-products-hourly": {
            "task": "purge_expired_products",
            "schedule": 3600.0,
        },
        "run-xiaohongshu-automation": {
            "task": "run_xiaohongshu_automation",
            "schedule": 300.0,
        },
    },
)


@celery_app.task(name="healthcheck")
def healthcheck():
    return {"status": "ok", "mode": "shadow"}


@celery_app.task(name="purge_expired_products")
def purge_expired_products_task():
    async def run():
        async with SessionLocal() as session:
            return await purge_expired(session)

    return {"purged": asyncio.run(run())}


@celery_app.task(name="run_xiaohongshu_automation")
def run_xiaohongshu_automation_task():
    async def run():
        async with SessionLocal() as session:
            runtime_settings = await effective_settings(session)
            return await run_due_automations(
                session,
                provider_for(runtime_settings),
                runtime_settings,
            )

    return {"products": asyncio.run(run())}
