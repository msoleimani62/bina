"""
Router for the subscriptions component.
روتر کامپوننت اشتراک دسته‌بندی‌ها.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.subscriptions.service import (
    get_user_categories,
    list_available_categories,
    toggle_category,
)
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="subscriptions")

_CALLBACK_PREFIX = "sub_toggle:"


async def _build_keyboard(session, user_id: int) -> InlineKeyboardMarkup:
    categories = await list_available_categories(session)
    subscribed = await get_user_categories(session, user_id)

    rows = []
    for category in categories:
        mark = "✅" if category in subscribed else "▫️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {category}",
                    callback_data=f"{_CALLBACK_PREFIX}{category}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("categories"))
async def handle_categories(message: Message) -> None:
    if message.from_user is None:
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return

        keyboard = await _build_keyboard(session, user.id)
        lang = user.ui_lang

    await message.answer(t("menu_subscriptions", lang), reply_markup=keyboard)


@router.callback_query(F.data.startswith(_CALLBACK_PREFIX))
async def handle_toggle(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.message is None:
        return

    category = callback.data.removeprefix(_CALLBACK_PREFIX)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer()
            return

        await toggle_category(session, user.id, category)
        keyboard = await _build_keyboard(session, user.id)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()
