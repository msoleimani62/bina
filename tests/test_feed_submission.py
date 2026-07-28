from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.feed_submission import service as submission_service
from bina.components.feed_submission.service import InvalidFeedError, submit_feed
from bina.core.fetcher import FeedFetchError, NormalizedEntry
from bina.core.models import Base, Feed, FeedStatus, User, UserFeedSubscription


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _fake_entry() -> NormalizedEntry:
    return NormalizedEntry(
        guid="g1", title="T", summary=None, link="https://x/1", image_url=None, published_at=None
    )


async def test_valid_feed_is_created_on_probation_and_followed(session_factory, monkeypatch):
    async def fake_fetch_and_parse(url, client):
        return [_fake_entry()]

    monkeypatch.setattr(submission_service, "fetch_and_parse", fake_fetch_and_parse)

    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        feed = await submit_feed(session, client=None, user_id=user.id, url="https://example.com/feed")
        await session.commit()

        assert feed.status == FeedStatus.PROBATION
        assert feed.added_by_user_id == user.id

        sub_result = await session.execute(
            select(UserFeedSubscription).where(
                UserFeedSubscription.user_id == user.id, UserFeedSubscription.feed_id == feed.id
            )
        )
        assert sub_result.scalar_one_or_none() is not None


async def test_rejects_non_http_url(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(InvalidFeedError):
            await submit_feed(session, client=None, user_id=user.id, url="ftp://example.com/feed")


async def test_rejects_feed_that_fails_to_fetch(session_factory, monkeypatch):
    async def always_fails(url, client):
        raise FeedFetchError("boom")

    monkeypatch.setattr(submission_service, "fetch_and_parse", always_fails)

    async with session_factory() as session:
        user = User(telegram_id=1)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(InvalidFeedError):
            await submit_feed(session, client=None, user_id=user.id, url="https://dead.example.com")


async def test_second_user_subscribing_to_existing_feed_reuses_it(session_factory, monkeypatch):
    async def fake_fetch_and_parse(url, client):
        return [_fake_entry()]

    monkeypatch.setattr(submission_service, "fetch_and_parse", fake_fetch_and_parse)

    async with session_factory() as session:
        first_user = User(telegram_id=1)
        second_user = User(telegram_id=2)
        session.add_all([first_user, second_user])
        await session.commit()
        await session.refresh(first_user)
        await session.refresh(second_user)

        feed_a = await submit_feed(
            session, client=None, user_id=first_user.id, url="https://shared.example.com/feed"
        )
        await session.commit()
        feed_b = await submit_feed(
            session, client=None, user_id=second_user.id, url="https://shared.example.com/feed"
        )
        await session.commit()

        # Same URL must not create a second Feed row.
        # آدرس یکسان نباید یک رکورد Feed دوم بسازد.
        assert feed_a.id == feed_b.id

        count_result = await session.execute(
            select(Feed).where(Feed.url == "https://shared.example.com/feed")
        )
        assert len(count_result.scalars().all()) == 1
