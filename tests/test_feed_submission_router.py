from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from aiogram.filters import CommandObject

from bina.bot.i18n import t
from bina.components.feed_submission import router as feed_submission_router
from bina.components.feed_submission.router import handle_addfeed
from bina.components.feed_submission.service import DEFAULT_CATEGORY, InvalidFeedError
from bina.core.models import Feed, FeedStatus
from tests.telegram_fakes import make_message


def _command(args: str | None) -> CommandObject:
    command = MagicMock(spec=CommandObject)
    command.args = args
    return command


async def test_handle_addfeed_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)

    await handle_addfeed(message, _command("https://a"))

    message.answer.assert_not_called()


async def test_handle_addfeed_no_url_does_nothing(db_session):
    message = make_message(telegram_id=940)

    await handle_addfeed(message, _command(None))
    message.answer.assert_not_called()

    await handle_addfeed(message, _command("   "))
    message.answer.assert_not_called()


async def test_handle_addfeed_unknown_user_does_nothing(db_session, monkeypatch):
    submit_feed = AsyncMock()
    monkeypatch.setattr(feed_submission_router, "submit_feed", submit_feed)
    message = make_message(telegram_id=941)

    await handle_addfeed(message, _command("https://a"))

    message.answer.assert_not_called()
    submit_feed.assert_not_awaited()


async def test_handle_addfeed_invalid_feed_notifies_user(db_session, create_user, monkeypatch):
    await create_user(telegram_id=942, ui_lang="fa")
    submit_feed = AsyncMock(side_effect=InvalidFeedError("bad feed"))
    monkeypatch.setattr(feed_submission_router, "submit_feed", submit_feed)
    message = make_message(telegram_id=942)

    await handle_addfeed(message, _command("https://broken"))

    message.answer.assert_awaited_once_with(t("feed_invalid", "fa"))


async def test_handle_addfeed_default_category(db_session, create_user, monkeypatch):
    await create_user(telegram_id=943, ui_lang="fa")
    fake_feed = Feed(id=1, url="https://a", category=DEFAULT_CATEGORY, status=FeedStatus.PROBATION)
    submit_feed = AsyncMock(return_value=fake_feed)
    monkeypatch.setattr(feed_submission_router, "submit_feed", submit_feed)
    message = make_message(telegram_id=943)

    await handle_addfeed(message, _command("https://a"))

    assert submit_feed.await_args.args[3] == "https://a"
    assert submit_feed.await_args.args[4] == DEFAULT_CATEGORY
    message.answer.assert_awaited_once_with(t("feed_added_probation", "fa"))


async def test_handle_addfeed_explicit_category(db_session, create_user, monkeypatch):
    await create_user(telegram_id=944, ui_lang="fa")
    fake_feed = Feed(id=2, url="https://a", category="tech", status=FeedStatus.PROBATION)
    submit_feed = AsyncMock(return_value=fake_feed)
    monkeypatch.setattr(feed_submission_router, "submit_feed", submit_feed)
    message = make_message(telegram_id=944)

    await handle_addfeed(message, _command("https://a tech"))

    assert submit_feed.await_args.args[4] == "tech"
    message.answer.assert_awaited_once_with(t("feed_added_probation", "fa"))
