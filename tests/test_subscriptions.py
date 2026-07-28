from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.subscriptions.service import (
    get_user_categories,
    list_available_categories,
    toggle_category,
)
from bina.core.models import Base, Feed, FeedStatus, User


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_only_active_feed_categories_are_listed(session_factory):
    async with session_factory() as session:
        session.add_all(
            [
                Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE),
                Feed(url="https://b", category="art", status=FeedStatus.PROBATION),
            ]
        )
        await session.commit()

        categories = await list_available_categories(session)
        assert categories == ["tech"]


async def test_toggle_subscribes_then_unsubscribes(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        subscribed = await toggle_category(session, user.id, "tech")
        await session.commit()
        assert subscribed is True
        assert await get_user_categories(session, user.id) == {"tech"}

        subscribed_again = await toggle_category(session, user.id, "tech")
        await session.commit()
        assert subscribed_again is False
        assert await get_user_categories(session, user.id) == set()
