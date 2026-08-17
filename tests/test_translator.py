"""
Tests for bina.core.translator — verifies the translation cache never calls
the provider twice for the same (article, target_lang) pair.
تست‌های bina.core.translator — تضمین می‌کند کش ترجمه هرگز برای یک جفت
(مقاله، زبان مقصد) یکسان، دوبار provider را صدا نمی‌زند.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.core.models import Article, Base, Feed
from bina.core.translator import get_or_translate_article


class FakeProvider:
    """Counts calls so tests can assert the cache is actually working."""

    def __init__(self) -> None:
        self.call_count = 0

    async def translate(self, text: str, target_lang: str) -> str:
        self.call_count += 1
        return f"[{target_lang}] {text}"


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_second_call_uses_cache_not_provider(session_factory):
    provider = FakeProvider()

    async with session_factory() as session:
        feed = Feed(url="https://example.com/feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        article = Article(
            feed_id=feed.id,
            guid="g1",
            title="Hello World",
            summary="A short summary.",
            link="https://example.com/g1",
        )
        session.add(article)
        await session.commit()
        await session.refresh(article)

        first = await get_or_translate_article(session, article, "fa", provider)
        await session.commit()
        second = await get_or_translate_article(session, article, "fa", provider)
        await session.commit()

        assert provider.call_count == 2  # title + summary, once each
        assert first.translated_title == second.translated_title == "[fa] Hello World"


async def test_different_languages_are_translated_independently(session_factory):
    provider = FakeProvider()

    async with session_factory() as session:
        feed = Feed(url="https://example.com/feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        article = Article(feed_id=feed.id, guid="g1", title="Hello", summary=None, link="https://x")
        session.add(article)
        await session.commit()
        await session.refresh(article)

        fa = await get_or_translate_article(session, article, "fa", provider)
        en_again = await get_or_translate_article(session, article, "en", provider)
        await session.commit()

        assert fa.target_lang == "fa"
        assert en_again.target_lang == "en"
        assert provider.call_count == 2  # one title translation per language
