from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Product


async def purge_expired_products(db: AsyncSession, now_at: datetime | None = None) -> int:
    cutoff = now_at or datetime.now(timezone.utc)
    ids = list(
        await db.scalars(
            select(Product.id).where(
                Product.deleted_at.is_not(None),
                Product.purge_after.is_not(None),
                Product.purge_after <= cutoff,
            )
        )
    )
    if ids:
        await db.execute(delete(Product).where(Product.id.in_(ids)))
        await db.commit()
    return len(ids)
