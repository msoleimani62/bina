<div align="center">

<img src="assets/icon.png" alt="Bina logo" width="140" height="140">

# Bina 🗞️

**A modular, multi-user Telegram bot that aggregates news from RSS feeds
and translates it into each user's own language.**

[![CI](https://github.com/msoleimani62/bina/actions/workflows/ci.yml/badge.svg)](https://github.com/msoleimani62/bina/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](pyproject.toml)
[![Framework](https://img.shields.io/badge/Telegram-aiogram%203-26A5E4.svg)](https://github.com/aiogram/aiogram)

**English** · [فارسی](README.fa.md)

</div>

---

## Table of contents

- [Status](#status)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running](#running)
- [Bot commands (usage guide)](#bot-commands-usage-guide)
- [Development](#development)
- [Uninstalling](#uninstalling)
- [Contributing](#contributing)
- [License](#license)

## Status

✅ **MVP complete (Phases 0–5).** Core engine, translation layer, all five
user components, and the scheduler + delivery pipeline are built and
unit-tested end to end: feeds are ingested on their own cadence regardless
of whether anyone opens the chat, translated once per language and cached,
and delivered as photo-or-text messages (with a save button) to every
eligible subscriber, with delivery deduplicated per user. See
[`ROADMAP.md`](ROADMAP.md) for what's next (self-update, richer feed
discovery, packaging polish).

## Features

- Add any RSS feed with `/addfeed`; new feeds go through a probation
  period (delivered only to the submitter) before joining the shared pool
  for everyone.
- Per-category subscriptions (technology, general news, art, or anything
  you add) via `/categories`.
- Automatic translation into the language you choose in `/settings`,
  cached so the same article is never translated twice for the same
  language, no matter how many users share it.
- Mute individual feeds even within a category you otherwise follow, via
  `/mutefeeds`.
- Save articles for later with the ⭐ button, with read/unread state and
  one-tap delete via `/saved`.
- Article images shown alongside translated text where available, with an
  automatic fallback to text-only if Telegram can't fetch the image.
- Fully bilingual (English/Persian) interface and documentation, with the
  locale system designed for adding more languages in minutes.
- A shared, central feed database: one scheduler cycle serves every user,
  so news keeps flowing even if nobody opens the bot for days.

## Architecture

```
bina/
├── core/         # Fetching, deduplication, DB models — no Telegram code here
├── bot/          # Telegram (aiogram) handlers — thin, consumes core/ only
├── components/   # Pluggable features: mute, save, settings, feed_submission, subscriptions, delivery
├── locales/      # en.json / fa.json — no hardcoded UI strings anywhere else
tests/            # Unit + integration tests
deploy/           # systemd unit template
```

Design rules (see [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full list):

- `core/` never imports `aiogram` — it stays framework-agnostic.
- A new user-facing feature is a new folder under `components/`, removable
  by deleting its folder and its one registration line.
- No hardcoded UI string is ever allowed outside `locales/*.json`.

See [`AI_BUILD_PROMPT.md`](AI_BUILD_PROMPT.md) for the full architecture
and engineering requirements this project is built against, and
[`ROADMAP.md`](ROADMAP.md) for the phased build plan.

## Installation

Requires **Python 3.11+**.

```bash
git clone https://github.com/msoleimani62/bina.git
cd bina
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env and set BINA_BOT_TOKEN and BINA_TRANSLATE_API_KEY
bina-bot install
```

`bina-bot install` only verifies your Python version and prints a
confirmation — it doesn't install anything by itself; `pip install -e
".[dev]"` above already installed every dependency.

## Configuration

All configuration is read from environment variables (`.env` is loaded
automatically). Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `BINA_BOT_TOKEN` | Yes | Telegram bot token from [@BotFather](https://t.me/BotFather). |
| `BINA_TRANSLATE_API_KEY` | Yes | Google Cloud Translation v2 API key. |
| `BINA_DATABASE_URL` | No | SQLAlchemy async URL. Defaults to a local `sqlite+aiosqlite:///bina.db`. |

## Running

```bash
bina-bot run
```

This initializes the database (creating tables on first run) and starts
the bot in polling mode, with the scheduler running in the background on
a 15-minute cycle.

For persistent operation on a systemd-based Linux system, see
[`deploy/bina-bot.service`](deploy/bina-bot.service) — copy it to
`/etc/systemd/system/`, adjust the paths inside it, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bina-bot.service
```

## Bot commands (usage guide)

| Command / action | What it does |
|---|---|
| `/start` | First contact — registers you and detects your UI language from Telegram. |
| `/categories` | Subscribe/unsubscribe to news categories with a tap. |
| `/mutefeeds` | Mute or unmute individual feeds, even within a subscribed category. |
| `/addfeed <url> [category]` | Submit your own RSS/Atom feed. It starts on probation, delivered only to you, until enough activity promotes it to the shared pool. |
| `/settings` | Change your translation language and jump to categories/mute/saved. |
| `/saved` | List your saved articles, with buttons to mark read or delete. |
| ⭐ button on a delivered article | Save that article for later. |

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

All checks below must pass before a PR can merge:

```bash
ruff check .
black --check .
mypy bina
pytest   # enforces an 80% coverage floor on bina/
```

## Uninstalling

```bash
# stop the systemd service, if you set one up
sudo systemctl disable --now bina-bot.service
sudo rm /etc/systemd/system/bina-bot.service

# remove the package and its virtual environment
deactivate 2>/dev/null || true
rm -rf .venv

# remove the local database and environment file (this deletes all stored data)
rm -f bina.db .env

# finally, remove the project folder itself
cd .. && rm -rf bina
```

If you installed Bina system-wide instead of in a virtual environment, run
`pip uninstall bina` before removing the folder.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the architecture guide and
instructions on adding a new component or a new language.

## License

MIT — see [`LICENSE`](LICENSE).
