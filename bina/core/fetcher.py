"""
Feed fetching and parsing for Bina.
دریافت و پارس فید برای بینا.

Two responsibilities are kept deliberately separate:
  - fetch_raw(): pure network I/O (easy to mock in tests).
  - parse_feed_content(): pure parsing logic, no network involved at all.
دو مسئولیت عمداً از هم جدا نگه داشته شده‌اند:
  - fetch_raw(): فقط ورودی/خروجی شبکه (به‌سادگی در تست قابل mock کردن).
  - parse_feed_content(): فقط منطق پارس، بدون هیچ ارتباط شبکه‌ای.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx

# A feed that fails this many times in a row is eligible to be marked broken.
# فیدی که به همین تعداد پیاپی شکست بخورد، واجد شرایط علامت‌گذاری به‌عنوان خراب است.
MAX_CONSECUTIVE_FAILURES = 5

DEFAULT_TIMEOUT_SECONDS = 15.0


class FeedFetchError(Exception):
    """Raised when the raw feed content could not be retrieved over HTTP."""


@dataclass(frozen=True)
class NormalizedEntry:
    """A feed entry reduced to the fields Bina actually stores."""

    guid: str
    title: str
    summary: str | None
    link: str
    image_url: str | None
    published_at: datetime | None


async def fetch_raw(url: str, client: httpx.AsyncClient) -> str:
    """Fetch the raw feed body over HTTP. Raises FeedFetchError on failure."""
    try:
        response = await client.get(url, timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # Wrap every httpx exception in our own type so callers only need
        # to catch one thing regardless of the underlying failure mode.
        # تمام خطاهای httpx در یک نوع خطای خودمان پیچیده می‌شود تا فراخوان‌کننده
        # فقط لازم باشد یک نوع خطا را مدیریت کند، صرف‌نظر از علت اصلی شکست.
        raise FeedFetchError(f"Failed to fetch {url}: {exc}") from exc
    return response.text


def _extract_image_url(entry: feedparser.FeedParserDict) -> str | None:
    """Try, in order, media:content, media:thumbnail, then enclosures."""
    media_content = entry.get("media_content")
    if media_content:
        url = media_content[0].get("url")
        if url:
            return str(url)

    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail:
        url = media_thumbnail[0].get("url")
        if url:
            return str(url)

    for link_obj in entry.get("links", []):
        if str(link_obj.get("type", "")).startswith("image/"):
            return str(link_obj.get("href"))

    return None


def _extract_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time is None:
        return None
    # feedparser gives a UTC struct_time; calendar.timegm avoids local-tz drift.
    # feedparser یک struct_time به‌وقت UTC می‌دهد؛ calendar.timegm از خطای منطقه‌ی
    # زمانی محلی جلوگیری می‌کند.
    return datetime.fromtimestamp(calendar.timegm(struct_time), tz=UTC)


def parse_feed_content(raw: str) -> list[NormalizedEntry]:
    """Parse raw RSS/Atom content into a list of normalized entries.

    Malformed feeds are not rejected outright — feedparser is lenient by
    design (`bozo` just flags that something looked off), so we still
    extract whatever usable entries exist rather than discarding everything.
    فیدهای بدفرمت کاملاً رد نمی‌شوند — feedparser عمداً اغماض‌کننده است
    (`bozo` فقط نشان می‌دهد چیزی مشکوک بوده)، پس هر ورودی قابل‌استفاده‌ای که
    وجود دارد استخراج می‌شود، نه اینکه همه‌چیز دور ریخته شود.
    """
    parsed = feedparser.parse(raw)

    entries: list[NormalizedEntry] = []
    for entry in parsed.entries:
        guid = entry.get("id") or entry.get("guid") or entry.get("link")
        link = entry.get("link")
        title = entry.get("title")
        if not guid or not link or not title:
            # Skip entries missing the fields Bina requires downstream.
            # ورودی‌هایی که فیلدهای موردنیاز پایین‌دستی بینا را ندارند رد می‌شوند.
            continue

        entries.append(
            NormalizedEntry(
                guid=str(guid),
                title=str(title),
                summary=str(entry["summary"]) if entry.get("summary") else None,
                link=str(link),
                image_url=_extract_image_url(entry),
                published_at=_extract_published_at(entry),
            )
        )

    return entries


async def fetch_and_parse(url: str, client: httpx.AsyncClient) -> list[NormalizedEntry]:
    """Convenience wrapper combining fetch_raw() and parse_feed_content()."""
    raw = await fetch_raw(url, client)
    return parse_feed_content(raw)
