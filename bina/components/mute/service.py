"""
Mute logic: hiding a specific feed even within a followed category.
منطق mute: مخفی‌کردن یک فید خاص حتی داخل دسته‌ای که دنبال می‌شود.

The audience-resolution queries (which feeds are followed, which are muted)
live in bina.core.audience since the delivery pipeline needs them too; this
module only owns the mute/unmute mutation itself.
کوئری‌های تشخیص مخاطب (کدام فیدها دنبال می‌شوند، کدام بی‌صدا هستند) در
bina.core.audience هستند چون خط‌لوله‌ی تحویل هم به آن‌ها نیاز دارد؛ این ماژول
فقط خودِ تغییر mute/unmute را در اختیار دارد.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Re-exported so existing imports (bot router, tests) keep working unchanged.
# دوباره‌صادر شده تا import‌های موجود (روتر بات، تست‌ها) بدون تغییر کار کنند.
from bina.core.audience import get_muted_feed_ids, list_followed_feeds
from bina.core.models import UserFeedMute

__all__ = ["get_muted_feed_ids", "list_followed_feeds", "toggle_mute"]


async def toggle_mute(session: AsyncSession, user_id: int, feed_id: int) -> bool:
    """Returns True if the feed is now muted, False if now unmuted."""
    result = await session.execute(
        select(UserFeedMute).where(UserFeedMute.user_id == user_id, UserFeedMute.feed_id == feed_id)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        return False

    session.add(UserFeedMute(user_id=user_id, feed_id=feed_id))
    return True
