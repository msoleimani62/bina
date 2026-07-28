"""
Subscription logic: which categories a user follows.
منطق اشتراک: کاربر دنبال‌کننده‌ی کدام دسته‌بندی‌هاست.
"""

from __future__ import annotations

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.models import Feed, FeedStatus, UserSubscription


async def list_available_categories(session: AsyncSession) -> list[str]:
    """Distinct categories among feeds that have left probation."""
    # Only ACTIVE feeds are offered — probation feeds aren't proven yet,
    # so they shouldn't appear as a general subscribe-able category.
    # فقط فیدهای ACTIVE پیشنهاد می‌شوند — فیدهای probation هنوز اثبات‌نشده‌اند،
    # پس نباید به‌عنوان یک دسته‌ی عمومی قابل‌اشتراک نمایش داده شوند.
    result = await session.execute(
        select(distinct(Feed.category)).where(Feed.status == FeedStatus.ACTIVE)
    )
    return sorted(row[0] for row in result.all())


async def get_user_categories(session: AsyncSession, user_id: int) -> set[str]:
    result = await session.execute(
        select(UserSubscription.category).where(UserSubscription.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def toggle_category(session: AsyncSession, user_id: int, category: str) -> bool:
    """Subscribe if not already subscribed, unsubscribe otherwise.

    Returns True if the user is now subscribed, False if now unsubscribed.
    """
    result = await session.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.category == category,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        return False

    session.add(UserSubscription(user_id=user_id, category=category))
    return True
