"""
Feed submission logic: validating and registering a user-supplied feed URL.
منطق افزودن فید: اعتبارسنجی و ثبت آدرس فیدی که کاربر وارد کرده.
"""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.fetcher import FeedFetchError, fetch_and_parse
from bina.core.models import Feed, FeedStatus, UserFeedSubscription

DEFAULT_CATEGORY = "general"


class InvalidFeedError(Exception):
    """Raised when a submitted URL is not a usable RSS/Atom feed."""


async def submit_feed(
    session: AsyncSession,
    client: httpx.AsyncClient,
    user_id: int,
    url: str,
    category: str = DEFAULT_CATEGORY,
) -> Feed:
    if not url.startswith(("http://", "https://")):
        raise InvalidFeedError("URL must start with http:// or https://")

    existing_result = await session.execute(select(Feed).where(Feed.url == url))
    feed = existing_result.scalar_one_or_none()

    if feed is None:
        # New URL — must actually parse into at least one entry before we
        # accept it, otherwise every broken link becomes a dead probation
        # entry cluttering the shared pool.
        # آدرس جدید — باید حداقل یک ورودی واقعی داشته باشه، وگرنه هر لینک
        # خراب به یک رکورد probation مرده و شلوغ‌کننده‌ی استخر مشترک تبدیل می‌شه.
        try:
            entries = await fetch_and_parse(url, client)
        except FeedFetchError as exc:
            raise InvalidFeedError(str(exc)) from exc

        if not entries:
            raise InvalidFeedError("Feed parsed but contained no entries.")

        feed = Feed(
            url=url, category=category, status=FeedStatus.PROBATION, added_by_user_id=user_id
        )
        session.add(feed)
        await session.flush()  # assign feed.id before we reference it below

    sub_result = await session.execute(
        select(UserFeedSubscription).where(
            UserFeedSubscription.user_id == user_id,
            UserFeedSubscription.feed_id == feed.id,
        )
    )
    if sub_result.scalar_one_or_none() is None:
        session.add(UserFeedSubscription(user_id=user_id, feed_id=feed.id))

    return feed
