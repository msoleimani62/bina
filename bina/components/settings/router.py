"""
Router for the settings component.
روتر کامپوننت تنظیمات.

/settings shows a menu; the language sub-menu is the first fully wired
option. Other rows (categories, mute list, saved) simply point the user to
the dedicated commands each of those components already registers.
/settings یک منو نشون می‌ده؛ زیرمنوی زبان اولین گزینه‌ی کاملاً سیم‌کشی‌شده‌ست.
بقیه‌ی ردیف‌ها (دسته‌بندی‌ها، فیدهای بی‌صدا، ذخیره‌شده‌ها) کاربر رو فقط به
دستورات اختصاصی‌ای که هرکدوم از اون کامپوننت‌ها از قبل ثبت کرده‌ن ارجاع می‌دن.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.settings.service import AVAILABLE_TARGET_LANGS, set_target_lang
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="settings")

_LANG_PREFIX = "settings_lang:"


@router.message(Command("settings"))
async def handle_settings(message: Message) -> None:
    if message.from_user is None:
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return
        lang = user.ui_lang

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("settings_language", lang), callback_data="settings_open_lang")],
            [InlineKeyboardButton(text=t("menu_subscriptions", lang), callback_data="settings_hint_categories")],
            [InlineKeyboardButton(text=t("settings_mute_list", lang), callback_data="settings_hint_mute")],
            [InlineKeyboardButton(text=t("menu_saved", lang), callback_data="settings_hint_saved")],
        ]
    )
    await message.answer(t("menu_settings", lang), reply_markup=keyboard)


@router.callback_query(F.data == "settings_open_lang")
async def handle_open_lang(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.message is None:
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer()
            return
        lang = user.ui_lang
        current_target = user.target_lang

    rows = [
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if code == current_target else ''}{code}",
                callback_data=f"{_LANG_PREFIX}{code}",
            )
        ]
        for code in AVAILABLE_TARGET_LANGS
    ]
    await callback.message.edit_text(
        t("settings_language", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith(_LANG_PREFIX))
async def handle_set_lang(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    new_lang = callback.data.removeprefix(_LANG_PREFIX)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer()
            return
        await set_target_lang(session, user.id, new_lang)

    await callback.answer(f"✅ {new_lang}")


# These three are placeholders that simply tell the user which command to
# run — kept here so the settings menu is a complete map of the bot, even
# before each sub-feature grows its own inline flow.
# این سه مورد فقط دستوری که باید اجرا بشه رو به کاربر یادآوری می‌کنن — اینجا
# نگه داشته شدن تا منوی تنظیمات نقشه‌ی کاملی از بات باشه، حتی قبل از اینکه
# هر زیرقابلیت جریان inline مخصوص خودش رو پیدا کنه.
@router.callback_query(F.data == "settings_hint_categories")
async def handle_hint_categories(callback: CallbackQuery) -> None:
    await callback.answer("/categories")


@router.callback_query(F.data == "settings_hint_mute")
async def handle_hint_mute(callback: CallbackQuery) -> None:
    await callback.answer("/mutefeeds")


@router.callback_query(F.data == "settings_hint_saved")
async def handle_hint_saved(callback: CallbackQuery) -> None:
    await callback.answer("/saved")
