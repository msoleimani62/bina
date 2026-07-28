from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.save.service import delete_saved, list_saved, mark_read, save_article
from bina.core.models import Base, SavedItemStatus, User


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_save_then_mark_read_then_delete(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        item = await save_article(session, user.id, article_id=42)
        await session.commit()
        assert item.status == SavedItemStatus.UNREAD

        saved = await list_saved(session, user.id)
        assert len(saved) == 1

        assert await mark_read(session, user.id, item.id) is True
        await session.commit()
        unread = await list_saved(session, user.id, status=SavedItemStatus.UNREAD)
        assert unread == []

        assert await delete_saved(session, user.id, item.id) is True
        await session.commit()
        assert await list_saved(session, user.id) == []


async def test_saving_twice_does_not_create_duplicates(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await save_article(session, user.id, article_id=1)
        await session.commit()
        await save_article(session, user.id, article_id=1)
        await session.commit()

        assert len(await list_saved(session, user.id)) == 1
