"""
Router for the save component.
روتر کامپوننت ذخیره‌سازی.

The "save" callback button itself gets attached to article delivery
messages once the delivery pipeline (Phase 5 of the roadmap) is built; this
router already handles it so no further wiring will be needed there beyond
adding the button.
دکمه‌ی callback «ذخیره» خودش وقتی خط‌لوله‌ی تحویل (فاز ۵ رودمپ) ساخته بشه به
پیام‌های تحویل خبر اضافه می‌شه؛ این روتر از همین الان مدیریتش می‌کنه، پس اونجا
فقط افزودن دکمه لازمه، نه سیم‌کشی بیشتر.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.save.service import SAVE_ARTICLE_CALLBACK_PREFIX, delete_saved, mark_read, save_article
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="save")

_SAVE_PREFIX = SAVE_ARTICLE_CALLBACK_PREFIX
_READ_PREFIX = "save_read:"
_DELETE_PREFIX = "save_delete:"


async def _get_user(session, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


@router.callback_query(F.data.startswith(_SAVE_PREFIX))
async def handle_save(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    article_id = int(callback.data.removeprefix(_SAVE_PREFIX))

    async with get_session() as session:
        user = await _get_user(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        await save_article(session, user.id, article_id)
        lang = user.ui_lang

    await callback.answer(t("article_saved", lang))


@router.message(Command("saved"))
async def handle_list_saved(message: Message) -> None:
    if message.from_user is None:
        return

    from bina.components.save.service import list_saved

    async with get_session() as session:
        user = await _get_user(session, message.from_user.id)
        if user is None:
            return
        items = await list_saved(session, user.id)
        lang = user.ui_lang

        if not items:
            await message.answer(t("menu_saved", lang))
            return

        for item in items:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t("article_marked_read", lang),
                            callback_data=f"{_READ_PREFIX}{item.id}",
                        ),
                        InlineKeyboardButton(
                            text=t("article_deleted", lang),
                            callback_data=f"{_DELETE_PREFIX}{item.id}",
                        ),
                    ]
                ]
            )
            await message.answer(f"#{item.article_id} — {item.status.value}", reply_markup=keyboard)


@router.callback_query(F.data.startswith(_READ_PREFIX))
async def handle_mark_read(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    saved_item_id = int(callback.data.removeprefix(_READ_PREFIX))

    async with get_session() as session:
        user = await _get_user(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        await mark_read(session, user.id, saved_item_id)
        lang = user.ui_lang

    await callback.answer(t("article_marked_read", lang))


@router.callback_query(F.data.startswith(_DELETE_PREFIX))
async def handle_delete(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.message is None:
        return
    saved_item_id = int(callback.data.removeprefix(_DELETE_PREFIX))

    async with get_session() as session:
        user = await _get_user(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        await delete_saved(session, user.id, saved_item_id)
        lang = user.ui_lang

    await callback.message.delete()
    await callback.answer(t("article_deleted", lang))
