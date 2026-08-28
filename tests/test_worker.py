import asyncio

from app.worker import _create_worker_session_factory
from sqlalchemy import text
from sqlalchemy.pool import NullPool


def test_worker_database_sessions_are_safe_across_repeated_event_loops(tmp_path):
    engine, session_factory = _create_worker_session_factory(
        f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}"
    )

    async def query_database():
        async with session_factory() as session:
            assert (await session.execute(text("SELECT 1"))).scalar_one() == 1

    assert isinstance(engine.pool, NullPool)
    asyncio.run(query_database())
    asyncio.run(query_database())
