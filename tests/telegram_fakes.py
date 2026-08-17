"""
Helpers for building lightweight fake aiogram objects for router tests.
کمک‌کننده‌هایی برای ساخت آبجکت‌های ساختگی سبک aiogram جهت تست روترها.

Not a test module itself (no test_ prefix) — pytest won't try to collect
it, it's just imported by the router test files.
خودش یک ماژول تست نیست (پیشوند test_ ندارد) — pytest سراغ collect کردنش
نمی‌رود، فقط توسط فایل‌های تست روتر import می‌شود.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from aiogram.types import User as TelegramUser


def make_telegram_user(telegram_id: int = 100, language_code: str | None = "en") -> TelegramUser:
    """A fake Telegram-side user, i.e. `message.from_user` /
    `callback.from_user` — not to be confused with `bina.core.models.User`,
    the DB row."""
    user = MagicMock(spec=TelegramUser)
    user.id = telegram_id
    user.language_code = language_code
    return user


def make_message(telegram_id: int | None = 100, language_code: str | None = "en") -> Message:
    """A fake incoming `Message`, e.g. for `/start`, `/settings`, `/addfeed`."""
    message = MagicMock(spec=Message)
    message.from_user = (
        make_telegram_user(telegram_id, language_code) if telegram_id is not None else None
    )
    message.answer = AsyncMock()
    return message


def make_callback_message() -> Message:
    """An accessible message — the kind a callback normally carries, which
    can be edited or deleted via the Bot API."""
    message = MagicMock(spec=Message)
    message.edit_text = AsyncMock()
    message.edit_reply_markup = AsyncMock()
    message.delete = AsyncMock()
    return message


def make_inaccessible_message() -> InaccessibleMessage:
    """A message too old for the Bot API to edit or delete — exercises the
    defensive `isinstance(callback.message, Message)` guard in routers."""
    return MagicMock(spec=InaccessibleMessage)


def make_callback(
    data: str | None,
    telegram_id: int | None = 100,
    message: Message | InaccessibleMessage | None = None,
) -> CallbackQuery:
    """A fake `CallbackQuery`. Pass `message=make_inaccessible_message()` to
    exercise the "old message" branch, or leave it unset for the normal
    accessible-message case."""
    callback = MagicMock(spec=CallbackQuery)
    callback.data = data
    callback.from_user = make_telegram_user(telegram_id) if telegram_id is not None else None
    callback.message = message if message is not None else make_callback_message()
    callback.answer = AsyncMock()
    return callback
