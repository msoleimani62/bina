"""
Bot application bootstrap.
راه‌اندازی اپلیکیشن بات.

This is the only module allowed to know about aiogram's Bot/Dispatcher
objects directly; everything else in bina/bot/ works through routers.
تنها ماژولی که مستقیماً از اشیای Bot/Dispatcher در aiogram اطلاع دارد همین
ماژول است؛ بقیه‌ی بخش‌های bina/bot/ از طریق router کار می‌کنند.
"""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bina.bot.handlers.start import router as start_router
from bina.components.feed_submission.router import router as feed_submission_router
from bina.components.mute.router import router as mute_router
from bina.components.save.router import router as save_router
from bina.components.settings.router import router as settings_router
from bina.components.subscriptions.router import router as subscriptions_router


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(settings_router)
    dispatcher.include_router(subscriptions_router)
    dispatcher.include_router(mute_router)
    dispatcher.include_router(save_router)
    dispatcher.include_router(feed_submission_router)
    return dispatcher


def build_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def run_polling(token: str) -> None:
    from bina.bot.scheduler import build_scheduler

    bot = build_bot(token)
    dispatcher = build_dispatcher()

    scheduler = build_scheduler(bot)
    scheduler.start()
    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
