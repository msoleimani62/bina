"""
Tests for bina.core.ingest — dedup, failure handling, and probation
promotion. fetch_and_parse is monkeypatched so these tests never touch the
network.
تست‌های bina.core.ingest — حذف تکرار، مدیریت شکست، و ترفیع از probation.
fetch_and_parse mock می‌شود تا این تست‌ها هرگز به شبکه دست نزنند.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.core import ingest as ingest_module
from bina.core.fetcher import FeedFetchError, NormalizedEntry
from bina.core.models import Article, Base, Feed, FeedStatus


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _entry(n: int) -> NormalizedEntry:
    return NormalizedEntry(
        guid=f"guid-{n}",
        title=f"Article {n}",
        summary=f"Summary of article {n}.",
        link=f"https://example.com/{n}",
        image_url=None,
        published_at=None,
    )


async def test_duplicate_entries_are_not_reinserted(session_factory, monkeypatch):
    async def fake_fetch_and_parse(url, client):
        return [_entry(1), _entry(2)]

    monkeypatch.setattr(ingest_module, "fetch_and_parse", fake_fetch_and_parse)

    async with session_factory() as session:
        feed = Feed(url="https://example.com/feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        first_run = await ingest_module.ingest_feed(session, feed, client=None)
        await session.commit()
        second_run = await ingest_module.ingest_feed(session, feed, client=None)
        await session.commit()

        assert first_run == 2
        assert second_run == 0

        articles = (await session.execute(select(Article))).scalars().all()
        assert len(articles) == 2


async def test_feed_marked_broken_after_max_failures(session_factory, monkeypatch):
    async def always_fails(url, client):
        raise FeedFetchError("simulated network failure")

    monkeypatch.setattr(ingest_module, "fetch_and_parse", always_fails)

    async with session_factory() as session:
        feed = Feed(url="https://example.com/dead-feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        for _ in range(ingest_module.MAX_CONSECUTIVE_FAILURES):
            await ingest_module.ingest_feed(session, feed, client=None)
            await session.commit()

        assert feed.status == FeedStatus.BROKEN


async def test_feed_promoted_out_of_probation_with_enough_articles(session_factory, monkeypatch):
    entries = [_entry(n) for n in range(ingest_module.PROBATION_MIN_ARTICLES)]

    async def fake_fetch_and_parse(url, client):
        return entries

    monkeypatch.setattr(ingest_module, "fetch_and_parse", fake_fetch_and_parse)

    async with session_factory() as session:
        feed = Feed(url="https://example.com/rising-feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        assert feed.status == FeedStatus.PROBATION

        await ingest_module.ingest_feed(session, feed, client=None)
        await session.commit()

        assert feed.status == FeedStatus.ACTIVE
