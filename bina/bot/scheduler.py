"""
Scheduler bootstrap.
راه‌اندازی زمان‌بند.

Runs independently of any single user's presence in the chat — the whole
point of the shared-database design decided earlier: news keeps flowing
even if nobody opens the bot for days.
مستقل از حضور هر کاربر خاصی در چت اجرا می‌شه — دقیقاً همون نکته‌ی اصلی
طراحی دیتابیس مشترکی که قبلاً تصمیم گرفتیم: خبر حتی اگر چند روز هیچ‌کس بات
رو باز نکنه، همچنان جریان داره.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import httpx
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from bina.components.delivery.service import run_delivery_cycle
from bina.core.db import get_session
from bina.core.ingest import ingest_feed
from bina.core.models import Feed
from bina.core.translator import GoogleTranslateProvider, TranslatorProvider

DEFAULT_CYCLE_MINUTES = 15


def _is_due(feed: Feed, now: datetime) -> bool:
    if feed.last_fetched_at is None:
        return True
    next_due = feed.last_fetched_at + timedelta(minutes=feed.fetch_interval_minutes)
    return now >= next_due


async def run_ingest_and_deliver(bot: Bot, translator: TranslatorProvider) -> None:
    """One full cycle: fetch every due feed, then deliver whatever is new."""
    now = datetime.now(UTC)

    async with httpx.AsyncClient() as client, get_session() as session:
        feeds = (await session.execute(select(Feed))).scalars().all()
        for feed in feeds:
            if _is_due(feed, now):
                await ingest_feed(session, feed, client)

    async with get_session() as session:
        await run_delivery_cycle(session, bot, translator)


def build_scheduler(bot: Bot, interval_minutes: int = DEFAULT_CYCLE_MINUTES) -> AsyncIOScheduler:
    api_key = os.environ.get("BINA_TRANSLATE_API_KEY", "")
    scheduler = AsyncIOScheduler()

    async def _job() -> None:
        # A fresh client per cycle keeps connection reuse simple and avoids
        # holding one open for the scheduler's entire lifetime.
        # یک client تازه در هر چرخه، reuse اتصال رو ساده نگه می‌داره و از باز
        # موندن یک اتصال برای کل عمر زمان‌بند جلوگیری می‌کنه.
        async with httpx.AsyncClient() as translate_client:
            provider = GoogleTranslateProvider(api_key, translate_client)
            await run_ingest_and_deliver(bot, provider)

    scheduler.add_job(_job, "interval", minutes=interval_minutes, next_run_time=datetime.now(UTC))
    return scheduler
