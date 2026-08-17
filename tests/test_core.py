"""
Smoke tests for Phase 0/1 — verifies the database layer and locale parity.
تست‌های اولیه‌ی فاز ۰/۱ — بررسی لایه‌ی دیتابیس و برابری کلیدهای زبان.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.core.models import Base, Feed, FeedStatus

LOCALES_DIR = Path(__file__).resolve().parent.parent / "bina" / "locales"


@pytest.fixture
async def session_factory():
    # In-memory SQLite so tests never touch a real file.
    # SQLite درون‌حافظه‌ای تا تست‌ها هرگز به فایل واقعی دست نزنند.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_feed_defaults_to_probation(session_factory):
    async with session_factory() as session:
        feed = Feed(url="https://example.com/feed", category="tech")
        session.add(feed)
        await session.commit()
        await session.refresh(feed)

        assert feed.status == FeedStatus.PROBATION
        assert feed.fetch_interval_minutes == 60


def test_locale_key_parity():
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    fa = json.loads((LOCALES_DIR / "fa.json").read_text(encoding="utf-8"))

    # Every key must exist in both files — no orphaned translations.
    # هر کلید باید در هر دو فایل وجود داشته باشد — بدون ترجمه‌ی یتیم.
    assert set(en.keys()) == set(fa.keys()), f"Locale key mismatch: {set(en) ^ set(fa)}"
