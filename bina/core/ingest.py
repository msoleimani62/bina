"""
Ingest orchestration for Bina.
هماهنگ‌سازی درج داده برای بینا.

Ties fetcher.py (network + parsing) to the database: deduplicates entries,
inserts new articles, and manages the probation -> active / broken
transitions decided earlier in the project.
fetcher.py (شبکه + پارس) را به دیتابیس متصل می‌کند: ورودی‌های تکراری را حذف
می‌کند، مقالات جدید را درج می‌کند، و انتقال‌های probation -> active / broken
را که قبلاً در پروژه تصمیم‌گیری شد مدیریت می‌کند.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.fetcher import FeedFetchError, NormalizedEntry, fetch_and_parse
from bina.core.models import Article, Feed, FeedStatus

import httpx

# Promotion threshold agreed on earlier: enough real activity in a short
# window is treated as evidence the feed is worth sharing with everyone.
# آستانه‌ی ترفیعی که قبلاً توافق شد: فعالیت واقعی کافی در یک بازه‌ی کوتاه به
# معنای ارزش اشتراک‌گذاری فید با همه در نظر گرفته می‌شود.
PROBATION_MIN_ARTICLES = 5
PROBATION_WINDOW_DAYS = 7
MAX_CONSECUTIVE_FAILURES = 5


async def _insert_new_articles(
    session: AsyncSession, feed: Feed, entries: list[NormalizedEntry]
) -> int:
    if not entries:
        return 0

    existing_guids_result = await session.execute(
        select(Article.guid).where(
            Article.feed_id == feed.id,
            Article.guid.in_([e.guid for e in entries]),
        )
    )
    existing_guids = {row[0] for row in existing_guids_result.all()}

    new_count = 0
    for entry in entries:
        if entry.guid in existing_guids:
            # Already ingested — skip rather than re-insert or re-translate.
            # قبلاً درج شده — به‌جای درج یا ترجمه‌ی دوباره، رد می‌شود.
            continue
        session.add(
            Article(
                feed_id=feed.id,
                guid=entry.guid,
                title=entry.title,
                summary=entry.summary,
                link=entry.link,
                image_url=entry.image_url,
                published_at=entry.published_at,
            )
        )
        new_count += 1

    return new_count


async def _maybe_promote(session: AsyncSession, feed: Feed) -> None:
    if feed.status != FeedStatus.PROBATION:
        return

    window_start = datetime.now(timezone.utc) - timedelta(days=PROBATION_WINDOW_DAYS)
    count_result = await session.execute(
        select(func.count(Article.id)).where(
            Article.feed_id == feed.id, Article.fetched_at >= window_start
        )
    )
    article_count = count_result.scalar_one()

    if article_count >= PROBATION_MIN_ARTICLES:
        # Enough proven activity — join the shared pool for every subscriber.
        # فعالیت اثبات‌شده‌ی کافی — ورود به استخر مشترک برای همه‌ی مشترکین.
        feed.status = FeedStatus.ACTIVE


async def ingest_feed(
    session: AsyncSession, feed: Feed, client: httpx.AsyncClient
) -> int:
    """Fetch, parse, and store new articles for a single feed.

    Returns the number of newly-inserted articles. Never raises on a feed
    that is merely unreachable/broken — that's an expected, recoverable
    condition, tracked via `consecutive_failures` instead of a crash.
    تعداد مقالات تازه‌درج‌شده را برمی‌گرداند. برای فیدی که صرفاً غیرقابل‌دسترس/
    خراب است هرگز خطا پرتاب نمی‌کند — این یک وضعیت قابل‌انتظار و قابل‌جبران
    است که به‌جای کرش، از طریق `consecutive_failures` ردیابی می‌شود.
    """
    try:
        entries = await fetch_and_parse(feed.url, client)
    except FeedFetchError:
        feed.consecutive_failures += 1
        if feed.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            feed.status = FeedStatus.BROKEN
        return 0

    # A successful fetch clears any prior failure streak, even if this
    # particular pull happened to contain zero new entries.
    # یک دریافت موفق هر سابقه‌ی شکست قبلی را پاک می‌کند، حتی اگر همین دریافت
    # هیچ ورودی جدیدی نداشته باشد.
    feed.consecutive_failures = 0
    feed.last_fetched_at = datetime.now(timezone.utc)

    new_count = await _insert_new_articles(session, feed, entries)
    await _maybe_promote(session, feed)

    return new_count
