# Bina 🗞️

> A modular, multi-user Telegram bot that aggregates news from RSS feeds and
> translates it into each user's chosen language.

[![CI](https://github.com/msoleimani62/bina/actions/workflows/ci.yml/badge.svg)](https://github.com/msoleimani62/bina/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

نسخه‌ی فارسی: [README.fa.md](README.fa.md)

---

## Status

✅ **MVP complete (Phases 0–5).** Core engine, translation layer, all five
user components, and the scheduler + delivery pipeline are built and
unit-tested end to end: feeds are ingested on their own cadence regardless
of whether anyone opens the chat, translated once per language and cached,
and delivered as photo-or-text messages (with a save button) to every
eligible subscriber, with delivery deduplicated per user. See
[`ROADMAP.md`](ROADMAP.md) for what's next (self-update, richer feed
discovery, packaging polish).

## Features (planned)

- Add any RSS feed; new feeds go through a probation period before joining
  the shared pool for everyone.
- Per-category subscriptions (technology, general news, art, or anything you
  add).
- Automatic translation into the language you choose, cached so the same
  article is never translated twice for the same language.
- Mute individual feeds even within a category you otherwise follow.
- Save articles for later, with read/unread state and one-tap delete.
- Article images shown alongside translated text where available.
- Fully bilingual (English/Persian) interface and documentation, with the
  locale system designed for adding more languages.

## Architecture

```
bina/
├── core/         # Fetching, deduplication, DB models — no Telegram code here
├── bot/          # Telegram (aiogram) handlers — thin, consumes core/ only
├── components/   # Pluggable features: mute, save, settings, feed_submission
├── locales/      # en.json / fa.json — no hardcoded UI strings anywhere else
tests/            # Unit + integration tests
deploy/           # systemd unit template
```

See [`AI_BUILD_PROMPT.md`](AI_BUILD_PROMPT.md) for the full architecture and
engineering requirements this project is built against.

## Installation

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

## Running

```bash
bina-bot run
```

For persistent operation on a systemd-based Linux system, see
[`deploy/bina-bot.service`](deploy/bina-bot.service).

## Development

```bash
pre-commit install
pytest
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the architecture guide and
instructions on adding a new component or a new language.

## License

MIT
