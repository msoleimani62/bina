"""
Unit tests for bina.core.fetcher.parse_feed_content.
تست‌های واحد برای parse_feed_content — بدون هیچ وابستگی شبکه‌ای.
"""

from __future__ import annotations

from bina.core.fetcher import parse_feed_content

SAMPLE_RSS_WITH_MEDIA = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>First Article</title>
      <link>https://example.com/first</link>
      <guid>https://example.com/first</guid>
      <description>A short summary of the first article.</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <media:content url="https://example.com/first.jpg" medium="image"/>
    </item>
    <item>
      <title>Second Article</title>
      <link>https://example.com/second</link>
      <guid>https://example.com/second</guid>
      <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_MISSING_TITLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Broken-ish Feed</title>
    <item>
      <link>https://example.com/no-title</link>
      <guid>https://example.com/no-title</guid>
    </item>
  </channel>
</rss>
"""


def test_parses_title_link_and_image():
    entries = parse_feed_content(SAMPLE_RSS_WITH_MEDIA)

    assert len(entries) == 2
    first = entries[0]
    assert first.title == "First Article"
    assert first.link == "https://example.com/first"
    assert first.image_url == "https://example.com/first.jpg"
    assert first.summary == "A short summary of the first article."
    assert first.published_at is not None


def test_entry_without_image_has_none():
    entries = parse_feed_content(SAMPLE_RSS_WITH_MEDIA)
    second = entries[1]
    assert second.image_url is None


def test_entries_missing_required_fields_are_skipped():
    # An entry with no title is not usable downstream, so it's dropped
    # rather than stored with a blank title.
    # ورودی بدون عنوان در ادامه‌ی مسیر قابل‌استفاده نیست، پس به‌جای ذخیره‌ی
    # عنوان خالی، حذف می‌شود.
    entries = parse_feed_content(SAMPLE_RSS_MISSING_TITLE)
    assert entries == []
