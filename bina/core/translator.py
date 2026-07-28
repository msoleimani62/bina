"""
Translation layer for Bina.
لایه‌ی ترجمه برای بینا.

TranslatorProvider is a Protocol so the concrete API (Google, DeepL, ...) can
be swapped without touching any code that calls translate_article().
TranslatorProvider یک Protocol است تا API واقعی (Google، DeepL و ...) بدون
دست‌زدن به هیچ کدی که translate_article() را صدا می‌زند، قابل‌تعویض باشد.
"""

from __future__ import annotations

from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.core.models import Article, ArticleTranslation


class TranslationError(Exception):
    """Raised when a translation provider fails to return a result."""


class TranslatorProvider(Protocol):
    """Anything that can translate a string is a valid provider."""

    async def translate(self, text: str, target_lang: str) -> str: ...


class GoogleTranslateProvider:
    """Translates text using the Google Cloud Translation v2 REST API."""

    API_URL = "https://translation.googleapis.com/language/translate2"

    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._client = client

    async def translate(self, text: str, target_lang: str) -> str:
        try:
            response = await self._client.post(
                self.API_URL,
                params={"key": self._api_key},
                json={"q": text, "target": target_lang, "format": "text"},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["data"]["translations"][0]["translatedText"])
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            # Normalize every possible failure (network, auth, malformed
            # response) into one exception type callers can handle uniformly.
            # هر شکست ممکن (شبکه، احراز هویت، پاسخ بدفرمت) به یک نوع خطای
            # یکسان تبدیل می‌شود تا فراخوان‌کننده بتواند یکنواخت مدیریتش کند.
            raise TranslationError(f"Google translation failed: {exc}") from exc


async def get_or_translate_article(
    session: AsyncSession,
    article: Article,
    target_lang: str,
    provider: TranslatorProvider,
) -> ArticleTranslation:
    """Return the cached translation for (article, target_lang), or create it.

    This is the single choke point that guarantees the same article is never
    translated twice for the same language, regardless of how many users
    share that language — the cost-saving property decided earlier.
    این تنها نقطه‌ی گلوگاهیه که تضمین می‌کنه یک مقاله هرگز برای یک زبان دوبار
    ترجمه نشه، صرف‌نظر از اینکه چند کاربر اون زبان رو مشترکن — ویژگی
    صرفه‌جویی هزینه‌ای که قبلاً توافق شد.
    """
    existing = await session.execute(
        select(ArticleTranslation).where(
            ArticleTranslation.article_id == article.id,
            ArticleTranslation.target_lang == target_lang,
        )
    )
    cached = existing.scalar_one_or_none()
    if cached is not None:
        return cached

    translated_title = await provider.translate(article.title, target_lang)
    translated_body = (
        await provider.translate(article.summary, target_lang)
        if article.summary
        else ""
    )

    translation = ArticleTranslation(
        article_id=article.id,
        target_lang=target_lang,
        translated_title=translated_title,
        translated_body=translated_body,
    )
    session.add(translation)
    return translation
