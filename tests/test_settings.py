from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bina.components.settings.service import set_target_lang
from bina.core.models import Base, User


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_set_valid_target_lang(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1, target_lang="fa")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert await set_target_lang(session, user.id, "es") is True
        await session.commit()
        await session.refresh(user)
        assert user.target_lang == "es"


async def test_rejects_unsupported_language(session_factory):
    async with session_factory() as session:
        user = User(telegram_id=1, target_lang="fa")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert await set_target_lang(session, user.id, "klingon") is False
        await session.refresh(user)
        assert user.target_lang == "fa"
