"""
Async database engine and session factory for Bina.
موتور دیتابیس async و سازنده‌ی session برای بینا.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bina.core.models import Base

# Read from the environment so the same code works in dev, CI, and prod.
# خواندن از متغیر محیطی تا کد یکسان در محیط توسعه، CI و پروداکشن کار کند.
DATABASE_URL = os.environ.get("BINA_DATABASE_URL", "sqlite+aiosqlite:///bina.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they do not already exist."""
    # Idempotent: safe to call on every startup.
    # ایمن برای فراخوانی در هر بار اجرا؛ اگر جدول‌ها وجود داشته باشند کاری انجام نمی‌دهد.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a scoped session, committing on success and rolling back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
