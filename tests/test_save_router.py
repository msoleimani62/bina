from __future__ import annotations

from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.save.router import (
    _DELETE_PREFIX,
    _READ_PREFIX,
    _SAVE_PREFIX,
    handle_delete,
    handle_list_saved,
    handle_mark_read,
    handle_save,
)
from bina.core.models import SavedItem, SavedItemStatus
from tests.telegram_fakes import make_callback, make_inaccessible_message, make_message


async def test_handle_save_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_SAVE_PREFIX}1", telegram_id=None)
    await handle_save(callback)
    callback.answer.assert_not_called()

    callback = make_callback(data=None)
    await handle_save(callback)
    callback.answer.assert_not_called()


async def test_handle_save_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_SAVE_PREFIX}1", telegram_id=930)

    await handle_save(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_save_saves_the_article(db_session, create_user):
    await create_user(telegram_id=931, ui_lang="fa")
    callback = make_callback(data=f"{_SAVE_PREFIX}42", telegram_id=931)

    await handle_save(callback)

    async with db_session() as session:
        result = await session.execute(select(SavedItem).where(SavedItem.article_id == 42))
        item = result.scalar_one()
        assert item.status == SavedItemStatus.UNREAD
    callback.answer.assert_awaited_once_with(t("article_saved", "fa"))


async def test_handle_list_saved_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)
    await handle_list_saved(message)
    message.answer.assert_not_called()


async def test_handle_list_saved_unknown_user_does_nothing(db_session):
    message = make_message(telegram_id=932)
    await handle_list_saved(message)
    message.answer.assert_not_called()


async def test_handle_list_saved_empty_shows_placeholder(db_session, create_user):
    await create_user(telegram_id=933, ui_lang="fa")
    message = make_message(telegram_id=933)

    await handle_list_saved(message)

    message.answer.assert_awaited_once_with(t("menu_saved", "fa"))


async def test_handle_list_saved_lists_each_item_with_buttons(db_session, create_user):
    user = await create_user(telegram_id=934, ui_lang="fa")
    async with db_session() as session:
        session.add(SavedItem(user_id=user.id, article_id=7))
        await session.commit()

    message = make_message(telegram_id=934)
    await handle_list_saved(message)

    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert args[0] == f"#7 — {SavedItemStatus.UNREAD.value}"
    buttons = kwargs["reply_markup"].inline_keyboard[0]
    assert buttons[0].callback_data.startswith(_READ_PREFIX)
    assert buttons[1].callback_data.startswith(_DELETE_PREFIX)


async def test_handle_mark_read_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_READ_PREFIX}1", telegram_id=None)
    await handle_mark_read(callback)
    callback.answer.assert_not_called()


async def test_handle_mark_read_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_READ_PREFIX}1", telegram_id=935)

    await handle_mark_read(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_mark_read_marks_the_item(db_session, create_user):
    user = await create_user(telegram_id=936, ui_lang="fa")
    async with db_session() as session:
        item = SavedItem(user_id=user.id, article_id=8)
        session.add(item)
        await session.commit()
        await session.refresh(item)

    callback = make_callback(data=f"{_READ_PREFIX}{item.id}", telegram_id=936)
    await handle_mark_read(callback)

    async with db_session() as session:
        result = await session.execute(select(SavedItem).where(SavedItem.id == item.id))
        assert result.scalar_one().status == SavedItemStatus.READ
    callback.answer.assert_awaited_once_with(t("article_marked_read", "fa"))


async def test_handle_delete_ignores_callback_without_from_user_or_data(db_session):
    callback = make_callback(data=f"{_DELETE_PREFIX}1", telegram_id=None)
    await handle_delete(callback)
    callback.answer.assert_not_called()


async def test_handle_delete_on_inaccessible_message_only_answers(db_session):
    callback = make_callback(
        data=f"{_DELETE_PREFIX}1", telegram_id=937, message=make_inaccessible_message()
    )

    await handle_delete(callback)

    callback.answer.assert_awaited_once_with()


async def test_handle_delete_unknown_user_only_answers(db_session):
    callback = make_callback(data=f"{_DELETE_PREFIX}1", telegram_id=938)

    await handle_delete(callback)

    callback.answer.assert_awaited_once_with()
    callback.message.delete.assert_not_called()


async def test_handle_delete_removes_the_item(db_session, create_user):
    user = await create_user(telegram_id=939, ui_lang="fa")
    async with db_session() as session:
        item = SavedItem(user_id=user.id, article_id=9)
        session.add(item)
        await session.commit()
        await session.refresh(item)

    callback = make_callback(data=f"{_DELETE_PREFIX}{item.id}", telegram_id=939)
    await handle_delete(callback)

    async with db_session() as session:
        result = await session.execute(select(SavedItem).where(SavedItem.id == item.id))
        assert result.scalar_one_or_none() is None
    callback.message.delete.assert_awaited_once_with()
    callback.answer.assert_awaited_once_with(t("article_deleted", "fa"))
