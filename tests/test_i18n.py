"""
Tests for bina.bot.i18n.t — key lookup and fallback behavior.
تست‌های bina.bot.i18n.t — رفتار جست‌وجوی کلید و بازگشت به پیش‌فرض.
"""

from __future__ import annotations

from bina.bot.i18n import t


def test_returns_persian_text_for_known_key():
    assert t("menu_settings", "fa") == "تنظیمات"


def test_returns_english_text_for_known_key():
    assert t("menu_settings", "en") == "Settings"


def test_unsupported_language_falls_back_to_english():
    assert t("menu_settings", "xx") == "Settings"


def test_unknown_key_returns_the_key_itself():
    assert t("this_key_does_not_exist", "en") == "this_key_does_not_exist"
