from __future__ import annotations

from bina.bot.i18n import t
from bina.components.subscriptions.router import _CALLBACK_PREFIX, handle_categories, handle_toggle
from bina.core.models import Feed, FeedStatus, UserSubscription
from tests.telegram_fakes import make_callback, make_inaccessible_message, make_message


async def test_handle_categories_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)

    await handle_categories(message)

    message.answer.assert_not_called()


async def test_handle_categories_unknown_user_does_nothing(db_session):
    message = make_message(telegram_id=900)

    await handle_categories(message)

    message.answer.assert_not_called()


async def test_handle_categories_marks_subscribed_and_skips_probation(db_session, create_user):
    user = await create_user(telegram_id=901, ui_lang="fa")
    async with db_session() as session:
        session.add(Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE))
        session.add(Feed(url="https://b", category="art", status=FeedStatus.ACTIVE))
        # A probation feed's category must never appear as subscribe-able.
        session.add(Feed(url="https://c", category="rumors", status=FeedStatus.PROBATION))
        session.add(UserSubscription(user_id=user.id, category="tech"))
        await session.commit()

    message = make_message(telegram_id=901)
    await handle_categories(message)

    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert args[0] == t("menu_subscriptions", "fa")
    keyboard = kwargs["reply_markup"]
    rows = {row[0].callback_data: row[0].text for row in keyboard.inline_keyboard}
    assert rows == {
        f"{_CALLBACK_PREFIX}tech": "✅ tech",
        f"{_CALLBACK_PREFIX}art": "▫️ art",
    }
    assert f"{_CALLBACK_PREFIX}rumors" not in rows


async def test_handle_toggle_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_CALLBACK_PREFIX}tech", telegram_id=None)
    await handle_toggle(callback)
    callback.answer.assert_not_called()

    callback = make_callback(data=None)
    await handle_toggle(callback)
    callback.answer.assert_not_called()


async def test_handle_toggle_on_inaccessible_message_only_answers(db_session):
    callback = make_callback(
        data=f"{_CALLBACK_PREFIX}tech",
        telegram_id=902,
        message=make_inaccessible_message(),
    )

    await handle_toggle(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_toggle_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_CALLBACK_PREFIX}tech", telegram_id=903)

    await handle_toggle(callback)

    callback.answer.assert_awaited_once_with()
    callback.message.edit_reply_markup.assert_not_called()


async def test_handle_toggle_subscribes_then_unsubscribes(db_session, create_user):
    await create_user(telegram_id=904)
    async with db_session() as session:
        session.add(Feed(url="https://a", category="tech", status=FeedStatus.ACTIVE))
        await session.commit()

    callback = make_callback(data=f"{_CALLBACK_PREFIX}tech", telegram_id=904)
    await handle_toggle(callback)

    callback.message.edit_reply_markup.assert_awaited_once()
    keyboard = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].text == "✅ tech"
    callback.answer.assert_awaited_once_with()

    callback = make_callback(data=f"{_CALLBACK_PREFIX}tech", telegram_id=904)
    await handle_toggle(callback)

    keyboard = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].text == "▫️ tech"
