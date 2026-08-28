from datetime import datetime, timedelta, timezone

import pytest

from app.models import Product
from app.product_lifecycle import purge_expired_products

pytest_plugins = ["test_api_workflow"]


async def create_product(client, name):
    response = await client.post(
        "/v1/products",
        json={"name": name, "website_url": f"https://{name.lower()}.example.com"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_products_can_be_reordered_deleted_and_restored(api_client):
    client, _ = api_client
    first = await create_product(client, "First")
    second = await create_product(client, "Second")
    assert first["sort_order"] < second["sort_order"]
    assert first["deleted_at"] is None and first["purge_after"] is None

    reordered = await client.put(
        "/v1/products/order", json={"product_ids": [second["id"], first["id"]]}
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in (await client.get("/v1/products")).json()] == [
        second["id"],
        first["id"],
    ]
    assert (
        await client.put("/v1/products/order", json={"product_ids": [first["id"]]})
    ).status_code == 409

    deleted = await client.delete(f"/v1/products/{second['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] and deleted.json()["purge_after"]
    assert [item["id"] for item in (await client.get("/v1/products")).json()] == [first["id"]]
    assert (await client.get(f"/v1/products/{second['id']}")).status_code == 404
    assert [item["id"] for item in (await client.get("/v1/products/trash")).json()] == [
        second["id"]
    ]

    restored = await client.post(f"/v1/products/{second['id']}/restore")
    assert restored.status_code == 200 and restored.json()["deleted_at"] is None
    assert [item["id"] for item in (await client.get("/v1/products")).json()] == [
        first["id"],
        second["id"],
    ]


@pytest.mark.asyncio
async def test_permanent_delete_and_expiry_cleanup(api_client):
    client, session_factory = api_client
    active = await create_product(client, "Active")
    expired = await create_product(client, "Expired")
    assert (await client.delete(f"/v1/products/{active['id']}/permanent")).status_code == 409
    await client.delete(f"/v1/products/{expired['id']}")

    async with session_factory() as db:
        product = await db.get(Product, expired["id"])
        product.purge_after = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
        assert await purge_expired_products(db) == 1

    assert (await client.get("/v1/products/trash")).json() == []
