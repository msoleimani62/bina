"""
/start handler.
هندلر دستور /start.

First contact with a new user: detect a starting UI language from Telegram's
own client-language hint, create the User row, and greet them.
اولین برخورد با کاربر جدید: تشخیص زبان اولیه‌ی رابط کاربری از راهنمای زبان
کلاینت تلگرام خودش، ساخت رکورد User، و خوش‌آمدگویی.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select

from bina.bot.i18n import DEFAULT_LANG, SUPPORTED_LANGS, t
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="start")


def _detect_ui_lang(telegram_language_code: str | None) -> str:
    if telegram_language_code and telegram_language_code[:2] in SUPPORTED_LANGS:
        return telegram_language_code[:2]
    return DEFAULT_LANG


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if message.from_user is None:
        # Defensive: CommandStart always carries a from_user in practice,
        # but we never trust external input to be well-formed.
        # احتیاطی: CommandStart در عمل همیشه from_user دارد، ولی هرگز به
        # ورودی خارجی برای خوش‌فرم‌بودن اعتماد نمی‌کنیم.
        return

    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if user is None:
            ui_lang = _detect_ui_lang(message.from_user.language_code)
            user = User(
                telegram_id=telegram_id,
                ui_lang=ui_lang,
                # Default translation target mirrors the UI language until
                # the user picks something different in settings.
                # زبان مقصد ترجمه تا زمانی که کاربر چیز دیگری در تنظیمات
                # انتخاب کند، از زبان رابط کاربری پیروی می‌کند.
                target_lang=ui_lang,
            )
            session.add(user)

        lang = user.ui_lang

    await message.answer(t("welcome", lang))
