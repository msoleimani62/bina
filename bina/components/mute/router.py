"""
Router for the mute component.
روتر کامپوننت بی‌صداکردن فید.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.bot.i18n import t
from bina.components.mute.service import get_muted_feed_ids, list_followed_feeds, toggle_mute
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="mute")

_CALLBACK_PREFIX = "mute_toggle:"


async def _build_keyboard(session: AsyncSession, user_id: int) -> InlineKeyboardMarkup:
    feeds = await list_followed_feeds(session, user_id)
    muted_ids = await get_muted_feed_ids(session, user_id)

    rows = []
    for feed in feeds:
        mark = "🔕" if feed.id in muted_ids else "🔔"
        # Feed URLs can be long; the category gives a shorter, still-useful
        # label for the button so it doesn't overflow the Telegram UI.
        # آدرس فیدها می‌تونن طولانی باشن؛ دسته‌بندی برچسب کوتاه‌تر و بازهم
        # مفیدی برای دکمه فراهم می‌کنه تا از رابط تلگرام سرریز نکنه.
        label = f"{mark} [{feed.category}] {feed.url[:40]}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"{_CALLBACK_PREFIX}{feed.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("mutefeeds"))
async def handle_mutefeeds(message: Message) -> None:
    if message.from_user is None:
        return

    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            return

        keyboard = await _build_keyboard(session, user.id)
        lang = user.ui_lang

    await message.answer(t("settings_mute_list", lang), reply_markup=keyboard)


@router.callback_query(F.data.startswith(_CALLBACK_PREFIX))
async def handle_toggle(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None:
        return
    # An old/inaccessible message can't be edited — bail out early rather
    # than crash; the callback is still answered so the tap doesn't hang.
    # پیام قدیمی/غیرقابل‌دسترس قابل ویرایش نیست — به‌جای کرش، زودتر خارج
    # می‌شویم؛ callback همچنان answer می‌شود تا ضربه‌ی کاربر معلق نماند.
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    feed_id = int(callback.data.removeprefix(_CALLBACK_PREFIX))

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer()
            return

        await toggle_mute(session, user.id, feed_id)
        keyboard = await _build_keyboard(session, user.id)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()
