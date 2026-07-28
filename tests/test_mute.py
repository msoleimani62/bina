from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.mute.service import get_muted_feed_ids, list_followed_feeds, toggle_mute
from bina.core.models import Base, Feed, FeedStatus, User, UserFeedSubscription, UserSubscription


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_followed_feeds_combine_category_and_explicit_subscriptions(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        category_feed = Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE)
        explicit_feed = Feed(url="https://b", category="art", status=FeedStatus.PROBATION)
        session.add_all([category_feed, explicit_feed])
        await session.commit()
        await session.refresh(user)
        await session.refresh(category_feed)
        await session.refresh(explicit_feed)

        session.add(UserSubscription(user_id=user.id, category="tech"))
        session.add(UserFeedSubscription(user_id=user.id, feed_id=explicit_feed.id))
        await session.commit()

        feeds = await list_followed_feeds(session, user.id)
        feed_ids = {f.id for f in feeds}
        assert feed_ids == {category_feed.id, explicit_feed.id}


async def test_toggle_mute_then_unmute(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        feed = Feed(url="https://a", category="tech")
        session.add_all([user, feed])
        await session.commit()
        await session.refresh(user)
        await session.refresh(feed)

        muted = await toggle_mute(session, user.id, feed.id)
        await session.commit()
        assert muted is True
        assert await get_muted_feed_ids(session, user.id) == {feed.id}

        unmuted = await toggle_mute(session, user.id, feed.id)
        await session.commit()
        assert unmuted is False
        assert await get_muted_feed_ids(session, user.id) == set()
