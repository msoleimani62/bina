"""
Shared pytest fixtures for the router/handler test layer.
Fixtureهای مشترک pytest برای لایه‌ی تست روترها/هندلرها.

Router and handler modules call `bina.core.db.get_session()` directly
rather than taking a session as a dependency-injected argument, so the
only way to control which database they hit in a test is to monkeypatch
the module-level engine/session-factory that `get_session()` reads.
ماژول‌های روتر و هندلر مستقیماً `bina.core.db.get_session()` را صدا
می‌زنند، نه اینکه session را به‌عنوان یک آرگومان تزریق‌شده بگیرند؛ پس
تنها راه کنترل اینکه در یک تست به کدام دیتابیس برخورد کنند، monkeypatch
کردن engine/session-factory سطح‌ماژولی است که `get_session()` می‌خواند.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from bina.core.models import Base, User


@pytest.fixture
async def session_factory():
    """A bare in-memory session factory, for tests that talk to the DB
    directly (no router/get_session() involved)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def db_session(monkeypatch):
    """An in-memory database wired into `bina.core.db.get_session()`, for
    testing routers/handlers that call `get_session()` internally.

    StaticPool keeps the same in-memory database alive across every
    connection checkout in the test, instead of each one getting its own
    empty `:memory:` database.
    یک دیتابیس درون‌حافظه‌ای که به `bina.core.db.get_session()` وصل شده،
    برای تست روترها/هندلرهایی که خودشان `get_session()` را صدا می‌زنند.

    StaticPool همان دیتابیس درون‌حافظه‌ای را در تمام دفعات checkout کانکشن
    در طول تست زنده نگه می‌دارد، به‌جای اینکه هر بار یک `:memory:` خالی
    جدید بسازد.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr("bina.core.db.engine", engine)
    monkeypatch.setattr("bina.core.db.async_session_factory", factory)

    yield factory
    await engine.dispose()


@pytest.fixture
def create_user(db_session):
    """Factory fixture: `await create_user(telegram_id=100)` inserts a User
    row into the same in-memory database `db_session` patched `get_session()`
    to use, and returns the persisted row."""

    async def _create(**kwargs) -> User:
        async with db_session() as session:
            user = User(**kwargs)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return _create
