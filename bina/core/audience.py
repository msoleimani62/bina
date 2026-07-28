"""
Audience resolution: which feeds a user actually receives.
تشخیص مخاطب: کاربر واقعاً کدام فیدها را دریافت می‌کند.

Shared by the `mute` component (to render the mute list) and the delivery
pipeline (to know who to send a new article to) — kept in core rather than
in a component so neither has to depend on the other.
مشترک بین کامپوننت `mute` (برای نمایش لیست بی‌صداها) و خط‌لوله‌ی تحویل (برای
اینکه بداند مقاله‌ی جدید را به چه کسی بفرستد) — در core نگه داشته شده تا هیچ‌
کدام از این دو مجبور به وابستگی به دیگری نباشد.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.models import Feed, FeedStatus, UserFeedMute, UserFeedSubscription, UserSubscription


async def list_followed_feeds(session: AsyncSession, user_id: int) -> list[Feed]:
    """Every feed this user currently receives: active feeds in a subscribed
    category, plus any feed explicitly followed on its own (mute not yet
    applied — see get_deliverable_feeds for that)."""
    category_result = await session.execute(
        select(UserSubscription.category).where(UserSubscription.user_id == user_id)
    )
    categories = {row[0] for row in category_result.all()}

    feeds: dict[int, Feed] = {}

    if categories:
        by_category = await session.execute(
            select(Feed).where(
                Feed.status == FeedStatus.ACTIVE, Feed.category.in_(categories)
            )
        )
        for feed in by_category.scalars().all():
            feeds[feed.id] = feed

    explicit_result = await session.execute(
        select(Feed)
        .join(UserFeedSubscription, UserFeedSubscription.feed_id == Feed.id)
        .where(UserFeedSubscription.user_id == user_id)
    )
    for feed in explicit_result.scalars().all():
        feeds[feed.id] = feed

    return list(feeds.values())


async def get_muted_feed_ids(session: AsyncSession, user_id: int) -> set[int]:
    result = await session.execute(
        select(UserFeedMute.feed_id).where(UserFeedMute.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def get_deliverable_feeds(session: AsyncSession, user_id: int) -> list[Feed]:
    """Followed feeds with muted ones removed — exactly what should reach
    this user's chat."""
    followed = await list_followed_feeds(session, user_id)
    muted = await get_muted_feed_ids(session, user_id)
    return [feed for feed in followed if feed.id not in muted]
