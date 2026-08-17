from __future__ import annotations

from bina.bot.i18n import t
from bina.components.mute.router import _CALLBACK_PREFIX, handle_mutefeeds, handle_toggle
from bina.core.models import Feed, FeedStatus, UserFeedSubscription
from tests.telegram_fakes import make_callback, make_inaccessible_message, make_message


async def test_handle_mutefeeds_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)

    await handle_mutefeeds(message)

    message.answer.assert_not_called()


async def test_handle_mutefeeds_unknown_user_does_nothing(db_session):
    message = make_message(telegram_id=910)

    await handle_mutefeeds(message)

    message.answer.assert_not_called()


async def test_handle_mutefeeds_lists_followed_feeds(db_session, create_user):
    user = await create_user(telegram_id=911, ui_lang="fa")
    async with db_session() as session:
        feed = Feed(url="https://example.com/rss", category="tech", status=FeedStatus.ACTIVE)
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        session.add(UserFeedSubscription(user_id=user.id, feed_id=feed.id))
        await session.commit()

    message = make_message(telegram_id=911)
    await handle_mutefeeds(message)

    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert args[0] == t("settings_mute_list", "fa")
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.text.startswith("🔔 [tech]")
    assert button.callback_data == f"{_CALLBACK_PREFIX}{feed.id}"


async def test_handle_toggle_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_CALLBACK_PREFIX}1", telegram_id=None)
    await handle_toggle(callback)
    callback.answer.assert_not_called()

    callback = make_callback(data=None)
    await handle_toggle(callback)
    callback.answer.assert_not_called()


async def test_handle_toggle_on_inaccessible_message_only_answers(db_session):
    callback = make_callback(
        data=f"{_CALLBACK_PREFIX}1", telegram_id=912, message=make_inaccessible_message()
    )

    await handle_toggle(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_toggle_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_CALLBACK_PREFIX}1", telegram_id=913)

    await handle_toggle(callback)

    callback.answer.assert_awaited_once_with()
    callback.message.edit_reply_markup.assert_not_called()


async def test_handle_toggle_mutes_then_unmutes(db_session, create_user):
    user = await create_user(telegram_id=914)
    async with db_session() as session:
        feed = Feed(url="https://example.com/rss", category="tech", status=FeedStatus.ACTIVE)
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        session.add(UserFeedSubscription(user_id=user.id, feed_id=feed.id))
        await session.commit()

    callback = make_callback(data=f"{_CALLBACK_PREFIX}{feed.id}", telegram_id=914)
    await handle_toggle(callback)

    keyboard = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].text.startswith("🔕")
    callback.answer.assert_awaited_once_with()

    callback = make_callback(data=f"{_CALLBACK_PREFIX}{feed.id}", telegram_id=914)
    await handle_toggle(callback)

    keyboard = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].text.startswith("🔔")
