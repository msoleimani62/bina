"""
Settings logic: changing the translation target language.
منطق تنظیمات: تغییر زبان مقصد ترجمه.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.models import User

# The starter set; adding a language here (plus a locale file, per
# CONTRIBUTING.md) is the entire integration surface.
# مجموعه‌ی اولیه؛ افزودن یک زبان اینجا (به‌همراه یک فایل locale، طبق
# CONTRIBUTING.md) کل سطح یکپارچه‌سازی لازمه.
AVAILABLE_TARGET_LANGS = ("fa", "en", "ar", "es", "fr", "de", "tr")


async def set_target_lang(session: AsyncSession, user_id: int, lang: str) -> bool:
    if lang not in AVAILABLE_TARGET_LANGS:
        return False

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False

    user.target_lang = lang
    return True
