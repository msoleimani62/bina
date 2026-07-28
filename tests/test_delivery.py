from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.delivery.service import (
    CAPTION_LIMIT,
    _format_message,
    deliver_article_to_user,
    run_delivery_cycle,
)
from bina.core.models import (
    Article,
    ArticleTranslation,
    Base,
    Feed,
    FeedStatus,
    User,
    UserDelivery,
    UserSubscription,
)


class FakeProvider:
    async def translate(self, text: str, target_lang: str) -> str:
        return f"[{target_lang}] {text}"


class FakeBot:
    def __init__(self, fail_photo: bool = False) -> None:
        self.sent_messages: list[dict] = []
        self.sent_photos: list[dict] = []
        self._fail_photo = fail_photo

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)

    async def send_photo(self, **kwargs):
        if self._fail_photo:
            from aiogram.exceptions import TelegramBadRequest

            raise TelegramBadRequest(method=None, message="bad photo url")
        self.sent_photos.append(kwargs)


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def test_format_message_respects_caption_limit():
    translation = ArticleTranslation(
        article_id=1,
        target_lang="fa",
        translated_title="Title",
        translated_body="x" * 5000,
    )
    message = _format_message(translation, "https://example.com/x", CAPTION_LIMIT)
    assert len(message) <= CAPTION_LIMIT
    assert message.endswith("https://example.com/x")
    assert "Title" in message


async def test_deliver_sends_photo_when_image_present(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1, target_lang="fa")
        feed = Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE)
        session.add_all([user, feed])
        await session.commit()
        await session.refresh(user)
        await session.refresh(feed)

        article = Article(
            feed_id=feed.id,
            guid="g1",
            title="Hello",
            summary="World",
            link="https://a/1",
            image_url="https://a/1.jpg",
        )
        session.add(article)
        await session.commit()
        await session.refresh(article)

        bot = FakeBot()
        provider = FakeProvider()

        sent = await deliver_article_to_user(session, bot, user, article, provider)
        await session.commit()

        assert sent is True
        assert len(bot.sent_photos) == 1
        assert len(bot.sent_messages) == 0


async def test_deliver_falls_back_to_text_when_photo_fails(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1, target_lang="fa")
        feed = Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE)
        session.add_all([user, feed])
        await session.commit()
        await session.refresh(user)
        await session.refresh(feed)

        article = Article(
            feed_id=feed.id,
            guid="g1",
            title="Hello",
            summary=None,
            link="https://a/1",
            image_url="https://broken/image.jpg",
        )
        session.add(article)
        await session.commit()
        await session.refresh(article)

        bot = FakeBot(fail_photo=True)
        provider = FakeProvider()

        sent = await deliver_article_to_user(session, bot, user, article, provider)

        assert sent is True
        assert len(bot.sent_messages) == 1
        assert len(bot.sent_photos) == 0


async def test_deliver_is_not_repeated_for_same_user_and_article(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1, target_lang="fa")
        feed = Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE)
        session.add_all([user, feed])
        await session.commit()
        await session.refresh(user)
        await session.refresh(feed)

        article = Article(feed_id=feed.id, guid="g1", title="Hello", summary=None, link="https://a/1")
        session.add(article)
        await session.commit()
        await session.refresh(article)

        bot = FakeBot()
        provider = FakeProvider()

        first = await deliver_article_to_user(session, bot, user, article, provider)
        await session.commit()
        second = await deliver_article_to_user(session, bot, user, article, provider)
        await session.commit()

        assert first is True
        assert second is False
        assert len(bot.sent_messages) == 1


async def test_delivery_cycle_only_reaches_subscribed_users(session_factory):
    async with session_factory() as session:
        subscribed_user = User(telegram_id=1, target_lang="fa")
        other_user = User(telegram_id=2, target_lang="fa")
        feed = Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE)
        session.add_all([subscribed_user, other_user, feed])
        await session.commit()
        await session.refresh(subscribed_user)
        await session.refresh(feed)

        session.add(UserSubscription(user_id=subscribed_user.id, category="tech"))
        article = Article(feed_id=feed.id, guid="g1", title="Hello", summary=None, link="https://a/1")
        session.add(article)
        await session.commit()

        bot = FakeBot()
        provider = FakeProvider()

        sent_count = await run_delivery_cycle(session, bot, provider)
        await session.commit()

        assert sent_count == 1
        assert len(bot.sent_messages) == 1
