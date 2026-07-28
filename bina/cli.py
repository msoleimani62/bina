"""
Command-line entry point for Bina.
نقطه‌ی ورود خط‌فرمان برای بینا.

`bina-bot install`  -> verifies Python version and dependencies.
`bina-bot run`       -> starts the bot (polling mode for now).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

MIN_PYTHON = (3, 11)


def check_environment() -> bool:
    """Verify the running Python version meets the minimum requirement."""
    ok = sys.version_info >= MIN_PYTHON
    # Print a clear pass/fail line so the install step is scriptable.
    # چاپ یک خط واضح موفق/ناموفق تا مرحله‌ی نصب قابل اسکریپت‌نویسی باشد.
    status = "OK" if ok else "FAIL"
    print(f"[{status}] Python >= {'.'.join(map(str, MIN_PYTHON))}")
    return ok


def cmd_install(_: argparse.Namespace) -> int:
    if not check_environment():
        print("Please upgrade Python before continuing.")
        return 1
    print("Environment OK. Run 'pip install -e .[dev]' to install dependencies.")
    return 0


def cmd_run(_: argparse.Namespace) -> int:
    import os

    from bina.core.db import init_db

    token = os.environ.get("BINA_BOT_TOKEN")
    if not token:
        print("BINA_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        return 1

    async def _start() -> None:
        from bina.bot.app import run_polling

        await init_db()
        await run_polling(token)

    asyncio.run(_start())
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="bina-bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Check environment/dependencies")
    install_parser.set_defaults(func=cmd_install)

    run_parser = subparsers.add_parser("run", help="Initialize DB and start the bot")
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
