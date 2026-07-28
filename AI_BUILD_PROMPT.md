# AI Build Prompt — Project "Bina" (بینا)

Paste this entire document as the initial instruction to your AI coding agent
(e.g. Claude Code) to scaffold and build the project.

---

## 1. Project Summary

Build **Bina**, a multi-user Telegram bot that aggregates news from RSS feeds,
translates non-native-language articles into each user's chosen language, and
delivers them privately via Telegram DM. Users can subscribe to categories,
add their own feeds (which join a shared pool after a probation period), mute
individual feeds, save articles for later, and configure their translation
language — all through an inline-keyboard settings menu.

Repository: `msoleimani62/bina`
Bot username: `@bina_news_bot`

---

## 2. Non-Negotiable Architecture Requirements

1. **Core + Component pattern.** A single `core/` package owns feed fetching,
   deduplication, storage, and scheduling. Every user-facing capability
   (mute, save, settings, feed submission, media rendering) is implemented as
   an independent, pluggable component under `components/`. Components
   depend on the Core's public API only — never on each other directly, and
   never on the Telegram layer.
2. **Strict layering.** `storage/` (data models) → `core/` (business logic)
   → `bot/` (Telegram interface). The bot layer is a thin consumer of Core
   services; it must not contain business logic.
3. **Dependency inversion.** Define `Protocol`/ABC interfaces for anything
   swappable: `TranslatorProvider`, `FeedFetcher`, `Scheduler`. Concrete
   implementations (Google Translate, DeepL) are injected, never
   hard-imported into business logic.
4. **No hardcoded user-facing strings.** All bot-facing text lives in
   `locales/fa.json` and `locales/en.json`, loaded through a small i18n
   helper (`t(key, lang, **kwargs)`). Adding a third language must require
   zero code changes — only a new locale file.
5. **Async-first.** Use `asyncio` throughout; `aiogram 3.x` for the bot,
   `SQLAlchemy 2.0` (async engine) for storage, `httpx.AsyncClient` for HTTP.

---

## 3. Tech Stack

- Python 3.11+
- `aiogram` 3.x (Telegram bot framework, FSM support for multi-step flows)
- `SQLAlchemy` 2.0 (async) + `SQLite` (aiosqlite driver)
- `feedparser`, `httpx`, `langdetect`
- `APScheduler` for the periodic fetch/translate cycle
- `pytest`, `pytest-asyncio`, `pytest-cov` for testing
- `ruff` + `black` + `mypy` for linting/formatting/type-checking
- `pre-commit` for git hooks
- GitHub Actions for CI

---

## 4. Data Model (minimum viable set)

```
Feed(id, url, category, status[probation|active|broken], added_by_user_id,
     fetch_interval, last_fetched_at)
Article(id, feed_id, guid, title, link, published_at, image_url)
ArticleTranslation(article_id, target_lang, translated_title, translated_body,
                    translated_at)
User(id, telegram_id, ui_lang, target_lang, created_at)
UserSubscription(user_id, feed_id_or_category)
UserFeedMute(user_id, feed_id)
SavedItem(id, user_id, article_id, status[unread|read], saved_at)
```

---

## 5. Security Requirements

- All secrets (bot token, translation API keys) loaded from environment
  variables via `.env` — never committed, never logged.
- All user input (feed URLs, callback data) validated and sanitized before
  use; reject non-http(s) URLs; enforce a max feed count per user to prevent
  abuse.
- All DB access through the ORM — no raw string-interpolated SQL.
- Strip/sanitize any HTML pulled from RSS content before rendering in
  Telegram (Telegram HTML parse mode is limited but still needs escaping).
- Rate-limit outbound calls to translation APIs and inbound bot commands per
  user to avoid abuse and API cost overrun.

---

## 6. Internationalization (i18n) Requirements

- Full parity between `locales/fa.json` and `locales/en.json` — no key
  present in one and missing in the other (enforce this with a test).
- Correct Persian typography: proper RTL rendering, half-space (`\u200c`)
  handling in generated Persian strings, Persian digit rendering as an
  optional per-user setting.
- UI language auto-detected from the user's Telegram client language on
  first `/start`, overridable in settings.
- Document in `CONTRIBUTING.md` exactly how a third-party contributor adds a
  new language (copy `en.json` → `xx.json`, translate values, done).

---

## 7. Testing Requirements

- Unit tests for all Core logic (dedup, probation threshold, translation
  caching) with zero network/Telegram dependency.
- Integration tests using an in-memory SQLite DB and mocked HTTP responses
  for feeds and translation APIs.
- Bot-layer tests using `aiogram`'s test utilities to simulate updates.
- A locale-parity test that fails CI if `fa.json` and `en.json` keys diverge.
- Minimum 80% coverage on `core/` and `components/`, enforced in CI
  (`pytest --cov --cov-fail-under=80`).
- All tests must pass in CI before merge; no direct pushes to `main`.

---

## 8. Packaging, Install & Update

- `pyproject.toml` with a console-script entry point (`bina-bot`).
- A `bina-bot install` command (or install script) that checks the Python
  version and required system packages, and installs/upgrades missing
  Python dependencies automatically, printing clear pass/fail status for
  each check.
- A `systemd` unit file template (`deploy/bina-bot.service`) for running the
  bot persistently on Linux.
- A self-update check: on a configurable interval, compare the running
  version against the latest GitHub Release tag and notify (or, if the user
  opts in, apply) the update.
- Must run cleanly on both the target environments: Arch Linux (desktop,
  systemd) and Termux/proot on Android (no systemd — provide a plain
  foreground-run fallback).

---

## 9. Code Comment Convention

Every comment that explains non-obvious logic must be written twice: one
line in English, one line in Persian, directly above the code it describes.
Example:

```python
# Deduplicate articles by GUID hash before insertion.
# حذف خبرهای تکراری بر اساس هش GUID قبل از درج در دیتابیس.
```

Do not write Persian anywhere inside identifiers, strings meant for
execution, or commit messages — only in explanatory comments.

---

## 10. Documentation Deliverable

- `README.md` (English) and `README.fa.md` (Persian) — both complete,
  visually polished (badges, table of contents, screenshots section
  placeholder), and kept in sync. Structure: overview, features, screenshots,
  installation, configuration, usage, all bot commands, contributing,
  license.
- `CONTRIBUTING.md` explaining the modular architecture and how to add a
  new component or a new language.

---

## 11. Definition of Done for Each Phase

A phase is complete only when: code is merged via PR, CI is green (lint +
type-check + tests + coverage threshold + locale-parity check), and the
relevant section of both README files is updated. Do not start the next
phase on top of a phase that has failing or missing tests.
