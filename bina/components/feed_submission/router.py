"""
Router for the feed_submission component.
روتر کامپوننت افزودن فید.

Usage: /addfeed <url> [category]
"""

from __future__ import annotations

import httpx
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from bina.bot.i18n import t
from bina.components.feed_submission.service import DEFAULT_CATEGORY, InvalidFeedError, submit_feed
from bina.core.db import get_session
from bina.core.models import User

router = Router(name="feed_submission")


@router.message(Command("addfeed"))
async def handle_addfeed(message: Message, command: CommandObject) -> None:
    if message.from_user is None:
        return

    args = (command.args or "").split(maxsplit=1)
    if not args:
        return  # No URL supplied; a full FSM-based prompt is a future upgrade.

    url = args[0]
    category = args[1].strip() if len(args) > 1 else DEFAULT_CATEGORY

    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        lang = user.ui_lang

        try:
            async with httpx.AsyncClient() as client:
                await submit_feed(session, client, user.id, url, category)
        except InvalidFeedError:
            await message.answer(t("feed_invalid", lang))
            return

    await message.answer(t("feed_added_probation", lang))
