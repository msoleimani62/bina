"""
Save logic: bookmarking an article, marking it read, or deleting it.
منطق ذخیره: نشان‌کردن یک مقاله، علامت‌زدن خوانده‌شده، یا حذف آن.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.models import SavedItem, SavedItemStatus

# Shared with components/save/router.py and components/delivery/service.py so
# the "save" button on a delivered article and the /saved list agree on the
# same callback_data format without importing each other's Telegram code.
# با components/save/router.py و components/delivery/service.py مشترکه تا
# دکمه‌ی «ذخیره» روی خبر تحویلی و لیست /saved بدون import کردن کد تلگرامی
# همدیگه، روی یک قالب callback_data یکسان توافق داشته باشن.
SAVE_ARTICLE_CALLBACK_PREFIX = "save_article:"


async def save_article(session: AsyncSession, user_id: int, article_id: int) -> SavedItem:
    result = await session.execute(
        select(SavedItem).where(SavedItem.user_id == user_id, SavedItem.article_id == article_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        # Already saved — return the existing row instead of erroring, so
        # tapping "save" twice is harmless rather than a crash.
        # قبلاً ذخیره شده — به‌جای خطا، همان رکورد موجود برگردانده می‌شود تا
        # دوبار زدن دکمه‌ی «ذخیره» بی‌ضرر باشد، نه یک کرش.
        return existing

    item = SavedItem(user_id=user_id, article_id=article_id)
    session.add(item)
    return item


async def list_saved(
    session: AsyncSession, user_id: int, status: SavedItemStatus | None = None
) -> list[SavedItem]:
    query = select(SavedItem).where(SavedItem.user_id == user_id)
    if status is not None:
        query = query.where(SavedItem.status == status)
    result = await session.execute(query.order_by(SavedItem.saved_at.desc()))
    return list(result.scalars().all())


async def mark_read(session: AsyncSession, user_id: int, saved_item_id: int) -> bool:
    result = await session.execute(
        select(SavedItem).where(SavedItem.id == saved_item_id, SavedItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    item.status = SavedItemStatus.READ
    return True


async def delete_saved(session: AsyncSession, user_id: int, saved_item_id: int) -> bool:
    result = await session.execute(
        select(SavedItem).where(SavedItem.id == saved_item_id, SavedItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    await session.delete(item)
    return True
