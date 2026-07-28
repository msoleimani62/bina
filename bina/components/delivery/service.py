"""
Delivery pipeline for Bina.
خط‌لوله‌ی تحویل برای بینا.

This lives in components/, not core/, specifically because it needs
aiogram's Bot to actually send messages — core/ stays framework-agnostic by
rule (see CONTRIBUTING.md). It builds on core.audience and core.translator,
which is the correct dependency direction.
این ماژول در components/ است، نه core/، دقیقاً چون برای ارسال واقعی پیام به
Bot از aiogram نیاز داره — core/ طبق قانون (نگاه کنید به CONTRIBUTING.md)
بدون وابستگی به فریم‌ورک باقی می‌مونه. این ماژول روی core.audience و
core.translator ساخته شده، که جهت وابستگی درستیه.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.components.save.service import SAVE_ARTICLE_CALLBACK_PREFIX
from bina.core.audience import get_deliverable_feeds
from bina.core.models import Article, ArticleTranslation, User, UserDelivery
from bina.core.translator import TranslatorProvider, get_or_translate_article

# Telegram's hard limits: 1024 chars for a photo caption, 4096 for plain text.
# محدودیت‌های سخت تلگرام: ۱۰۲۴ کاراکتر برای کپشن عکس، ۴۰۹۶ برای متن معمولی.
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def _format_message(translation: ArticleTranslation, link: str, limit: int) -> str:
    body = f"<b>{translation.translated_title}</b>"
    if translation.translated_body:
        body += f"\n\n{translation.translated_body}"
    body += f"\n\n{link}"

    if len(body) <= limit:
        return body

    # Truncate the body, not the title or link, so the two most important
    # pieces — headline and source — are never the part that gets cut.
    # فقط متن خلاصه کوتاه می‌شود، نه عنوان یا لینک — تا دو بخش مهم‌تر (تیتر و
    # منبع) هرگز آن قسمتی نباشند که بریده می‌شود.
    overflow = len(body) - limit + 1  # +1 for the ellipsis character
    keep = max(0, len(translation.translated_body) - overflow)
    truncated_body = translation.translated_body[:keep]
    body = f"<b>{translation.translated_title}</b>"
    if truncated_body:
        body += f"\n\n{truncated_body}…"
    body += f"\n\n{link}"
    return body[:limit]


def _save_button(article_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐", callback_data=f"{SAVE_ARTICLE_CALLBACK_PREFIX}{article_id}")]
        ]
    )


async def _already_delivered(session: AsyncSession, user_id: int, article_id: int) -> bool:
    result = await session.execute(
        select(UserDelivery).where(
            UserDelivery.user_id == user_id, UserDelivery.article_id == article_id
        )
    )
    return result.scalar_one_or_none() is not None


async def deliver_article_to_user(
    session: AsyncSession,
    bot: Bot,
    user: User,
    article: Article,
    translator: TranslatorProvider,
) -> bool:
    """Translate, send, and record delivery of one article to one user.

    Returns False (without raising) on a Telegram send failure — a blocked
    bot or a deactivated account shouldn't crash the whole delivery cycle
    for every other user.
    در صورت شکست ارسال تلگرام، False برمی‌گرداند (بدون پرتاب خطا) — بلاک‌شدن
    بات یا غیرفعال‌بودن حساب یک کاربر نباید کل چرخه‌ی تحویل را برای بقیه‌ی
    کاربران متوقف کند.
    """
    if await _already_delivered(session, user.id, article.id):
        return False

    translation = await get_or_translate_article(session, article, user.target_lang, translator)
    keyboard = _save_button(article.id)

    try:
        if article.image_url:
            caption = _format_message(translation, article.link, CAPTION_LIMIT)
            await bot.send_photo(
                chat_id=user.telegram_id,
                photo=article.image_url,
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            text = _format_message(translation, article.link, TEXT_LIMIT)
            await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=keyboard)
    except TelegramAPIError:
        # A photo URL Telegram can't fetch/decode is a known failure mode;
        # fall back to a text-only message rather than losing the article.
        # لینک عکسی که تلگرام نتونه دریافت/دیکد کنه یک حالت شکست شناخته‌شده‌ست؛
        # به‌جای از دست‌دادن کل خبر، به پیام متنی fallback می‌کنیم.
        try:
            text = _format_message(translation, article.link, TEXT_LIMIT)
            await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=keyboard)
        except TelegramAPIError:
            return False

    session.add(UserDelivery(user_id=user.id, article_id=article.id))
    return True


async def run_delivery_cycle(session: AsyncSession, bot: Bot, translator: TranslatorProvider) -> int:
    """Deliver every undelivered article to every eligible user.

    Returns the total number of messages actually sent.
    """
    sent_count = 0

    users = (await session.execute(select(User))).scalars().all()
    for user in users:
        feeds = await get_deliverable_feeds(session, user.id)
        if not feeds:
            continue
        feed_ids = [f.id for f in feeds]

        articles = (
            await session.execute(select(Article).where(Article.feed_id.in_(feed_ids)))
        ).scalars().all()

        for article in articles:
            delivered = await deliver_article_to_user(session, bot, user, article, translator)
            if delivered:
                sent_count += 1

    return sent_count
