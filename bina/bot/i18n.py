"""
i18n helper for Bina's bot layer.
کمک‌کننده‌ی چندزبانگی برای لایه‌ی بات بینا.

No user-facing string is ever hardcoded in a handler — everything goes
through t(key, lang). This module is the only place that reads the locale
files, and CI's locale-parity test guarantees en.json and fa.json never
drift apart.
هیچ رشته‌ی رابط‌کاربری هرگز مستقیم در یک هندلر نوشته نمی‌شود — همه از
t(key, lang) عبور می‌کنند. این ماژول تنها جاییه که فایل‌های locale را
می‌خواند، و تست برابری locale در CI تضمین می‌کند en.json و fa.json هرگز از
هم فاصله نمی‌گیرند.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "fa")


@lru_cache(maxsize=None)
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, lang: str, **kwargs: object) -> str:
    """Look up `key` in the given language, falling back to English, then
    to the key itself so a missing translation never crashes a handler —
    it just shows up visibly wrong instead of failing silently or loudly.
    جست‌وجوی `key` در زبان داده‌شده، با بازگشت به انگلیسی و سپس به خود کلید،
    تا یک ترجمه‌ی گم‌شده هرگز هندلر را کرش نکند — فقط به‌طور قابل‌مشاهده
    اشتباه نمایش داده می‌شود، نه اینکه بی‌صدا یا با کرش شکست بخورد.
    """
    lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    text = _load(lang).get(key) or _load(DEFAULT_LANG).get(key) or key
    return text.format(**kwargs) if kwargs else text
