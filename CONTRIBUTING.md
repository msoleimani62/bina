# Contributing to Bina

## Architecture rules (please read before opening a PR)

1. **Core stays framework-agnostic.** Nothing in `bina/core/` may import
   `aiogram` or anything Telegram-specific. Core exposes plain async
   functions/classes; the bot layer calls them.
2. **New feature → new component.** If you're adding user-facing behavior
   (a new menu, a new per-user toggle), put it in `bina/components/<name>/`
   with its own handlers, tests, and — if it needs new strings — new keys in
   *both* `locales/en.json` and `locales/fa.json`. A component should be
   removable by deleting its folder and its registration line, nothing else.
3. **No hardcoded UI strings.** Every user-facing string goes through the
   locale system. CI fails the build if `en.json` and `fa.json` keys don't
   match exactly.
4. **Bilingual comments only where logic isn't obvious.** One English line,
   one Persian line, directly above the code. Don't comment self-explanatory
   lines in either language.
5. **Every new module needs tests.** Unit tests for logic with no external
   dependency; integration tests (mocked HTTP/DB) for anything that touches
   feeds, translation, or the database.

## Adding a new language

1. Copy `bina/locales/en.json` to `bina/locales/<code>.json`.
2. Translate every value (keep the keys identical).
3. Add `<code>` to the list of selectable UI/translation languages in the
   settings component.
4. Run `pytest` — the locale-parity test will confirm nothing was missed.

## Local development

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

All four checks below must pass before a PR can merge: `ruff`, `black
--check`, `mypy`, `pytest` (with the 80% coverage floor).
