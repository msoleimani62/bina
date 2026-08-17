from __future__ import annotations

from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.settings.router import (
    _LANG_PREFIX,
    handle_hint_categories,
    handle_hint_mute,
    handle_hint_saved,
    handle_open_lang,
    handle_set_lang,
    handle_settings,
)
from bina.components.settings.service import AVAILABLE_TARGET_LANGS
from bina.core.models import User
from tests.telegram_fakes import make_callback, make_inaccessible_message, make_message


async def test_handle_settings_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)

    await handle_settings(message)

    message.answer.assert_not_called()


async def test_handle_settings_unknown_user_does_nothing(db_session):
    message = make_message(telegram_id=920)

    await handle_settings(message)

    message.answer.assert_not_called()


async def test_handle_settings_shows_full_menu(db_session, create_user):
    await create_user(telegram_id=921, ui_lang="fa")
    message = make_message(telegram_id=921)

    await handle_settings(message)

    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert args[0] == t("menu_settings", "fa")
    callback_datas = [row[0].callback_data for row in kwargs["reply_markup"].inline_keyboard]
    assert callback_datas == [
        "settings_open_lang",
        "settings_hint_categories",
        "settings_hint_mute",
        "settings_hint_saved",
    ]


async def test_handle_open_lang_no_from_user_does_nothing(db_session):
    callback = make_callback(data="settings_open_lang", telegram_id=None)

    await handle_open_lang(callback)

    callback.answer.assert_not_called()


async def test_handle_open_lang_on_inaccessible_message_only_answers(db_session):
    callback = make_callback(
        data="settings_open_lang", telegram_id=922, message=make_inaccessible_message()
    )

    await handle_open_lang(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_open_lang_unknown_user_only_answers(db_session):
    callback = make_callback(data="settings_open_lang", telegram_id=923)

    await handle_open_lang(callback)

    callback.answer.assert_awaited_once_with()
    callback.message.edit_text.assert_not_called()


async def test_handle_open_lang_marks_current_target(db_session, create_user):
    await create_user(telegram_id=924, target_lang="fa")
    callback = make_callback(data="settings_open_lang", telegram_id=924)

    await handle_open_lang(callback)

    callback.message.edit_text.assert_awaited_once()
    _, kwargs = callback.message.edit_text.await_args
    rows = {row[0].callback_data: row[0].text for row in kwargs["reply_markup"].inline_keyboard}
    assert rows[f"{_LANG_PREFIX}fa"] == "✅ fa"
    assert rows[f"{_LANG_PREFIX}en"] == "en"
    assert set(rows) == {f"{_LANG_PREFIX}{code}" for code in AVAILABLE_TARGET_LANGS}
    callback.answer.assert_awaited_once_with()


async def test_handle_set_lang_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_LANG_PREFIX}fa", telegram_id=None)
    await handle_set_lang(callback)
    callback.answer.assert_not_called()

    callback = make_callback(data=None)
    await handle_set_lang(callback)
    callback.answer.assert_not_called()


async def test_handle_set_lang_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_LANG_PREFIX}fa", telegram_id=925)

    await handle_set_lang(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_set_lang_updates_target_language(db_session, create_user):
    user = await create_user(telegram_id=926, target_lang="en")
    callback = make_callback(data=f"{_LANG_PREFIX}fa", telegram_id=926)

    await handle_set_lang(callback)

    async with db_session() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        assert result.scalar_one().target_lang == "fa"
    callback.answer.assert_awaited_once_with("✅ fa")


async def test_settings_hint_callbacks_answer_with_the_relevant_command(db_session):
    callback = make_callback(data="settings_hint_categories")
    await handle_hint_categories(callback)
    callback.answer.assert_awaited_once_with("/categories")

    callback = make_callback(data="settings_hint_mute")
    await handle_hint_mute(callback)
    callback.answer.assert_awaited_once_with("/mutefeeds")

    callback = make_callback(data="settings_hint_saved")
    await handle_hint_saved(callback)
    callback.answer.assert_awaited_once_with("/saved")
