from __future__ import annotations

from sqlalchemy import select

from bina.bot.handlers.start import handle_start
from bina.bot.i18n import t
from bina.core.models import User
from tests.telegram_fakes import make_message


async def test_no_from_user_does_nothing(db_session):
    message = make_message(telegram_id=None)

    await handle_start(message)

    message.answer.assert_not_called()


async def test_new_user_detects_supported_language(db_session):
    message = make_message(telegram_id=555, language_code="fa-IR")

    await handle_start(message)

    async with db_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == 555))
        user = result.scalar_one()
        assert user.ui_lang == "fa"
        # Default translation target mirrors the detected UI language.
        assert user.target_lang == "fa"

    message.answer.assert_awaited_once_with(t("welcome", "fa"))


async def test_new_user_unsupported_language_falls_back_to_default(db_session):
    message = make_message(telegram_id=556, language_code="de-DE")

    await handle_start(message)

    async with db_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == 556))
        user = result.scalar_one()
        assert user.ui_lang == "en"

    message.answer.assert_awaited_once_with(t("welcome", "en"))


async def test_existing_user_reuses_stored_language_and_is_not_duplicated(db_session, create_user):
    await create_user(telegram_id=557, ui_lang="fa", target_lang="en")
    # A different language_code this time — an existing user's stored
    # preference must win over re-detecting it from Telegram.
    message = make_message(telegram_id=557, language_code="en-US")

    await handle_start(message)

    async with db_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == 557))
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].ui_lang == "fa"

    message.answer.assert_awaited_once_with(t("welcome", "fa"))
