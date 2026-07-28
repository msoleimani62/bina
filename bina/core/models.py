"""
Core data models for Bina.
مدل‌های اصلی داده‌ی پروژه‌ی بینا.

All identifiers and docstrings are in English by convention; explanatory
comments are duplicated in Persian directly above the line they describe.
تمام شناسه‌ها و docstring‌ها طبق قرارداد پروژه به انگلیسی هستند؛ کامنت‌های
توضیحی دقیقاً بالای همان خط، هم به انگلیسی و هم به فارسی نوشته می‌شوند.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Declarative base shared by every model in the project."""


class FeedStatus(str, enum.Enum):
    """Lifecycle states of a feed in the shared pool."""

    # A newly-added feed starts here and is only delivered to its submitter.
    # فید تازه‌اضافه‌شده اینجا شروع می‌شود و فقط برای اضافه‌کننده‌اش ارسال می‌شود.
    PROBATION = "probation"
    # Promoted feeds join the shared pool and reach every subscriber.
    # فیدهای ترفیع‌یافته وارد استخر مشترک شده و به همه‌ی مشترکین می‌رسند.
    ACTIVE = "active"
    # Feeds that repeatedly fail to fetch/parse are marked broken and skipped.
    # فیدهایی که مکرراً در دریافت/پارس شکست می‌خورند خراب علامت‌گذاری و رد می‌شوند.
    BROKEN = "broken"


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[FeedStatus] = mapped_column(
        Enum(FeedStatus), default=FeedStatus.PROBATION, nullable=False
    )
    added_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Minutes between fetches; the scheduler reads this per-feed.
    # فاصله‌ی زمانی بین دریافت‌ها به دقیقه؛ زمان‌بند این مقدار را برای هر فید می‌خواند.
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Reset to 0 on any successful fetch; incremented on failure.
    # با هر دریافت موفق صفر می‌شود؛ با هر شکست یک واحد افزایش می‌یابد.
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="feed")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("feed_id", "guid", name="uq_feed_guid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), nullable=False)
    # guid is the RSS entry's stable identifier, used for deduplication.
    # guid شناسه‌ی پایدار آیتم RSS است که برای جلوگیری از تکرار استفاده می‌شود.
    guid: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Short description/summary pulled from the feed entry, if present.
    # خلاصه/توضیح کوتاه گرفته‌شده از ورودی فید، در صورت وجود.
    summary: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    feed: Mapped["Feed"] = relationship(back_populates="articles")
    translations: Mapped[list["ArticleTranslation"]] = relationship(
        back_populates="article"
    )


class ArticleTranslation(Base):
    """
    One cached translation of an article into one target language.
    یک ترجمه‌ی کش‌شده از یک مقاله به یک زبان مقصد مشخص.

    Cached per (article_id, target_lang) so the same translation is never
    purchased twice from the API for two users who share a language.
    کش‌شدن بر اساس (article_id, target_lang) باعث می‌شود ترجمه‌ی یکسان برای
    دو کاربر با زبان یکسان هرگز دوبار از API خریداری نشود.
    """

    __tablename__ = "article_translations"
    __table_args__ = (
        UniqueConstraint("article_id", "target_lang", name="uq_article_lang"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    translated_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    translated_body: Mapped[str] = mapped_column(String(8192), nullable=False)
    translated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    article: Mapped["Article"] = relationship(back_populates="translations")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    # Language the bot's own UI (menus, buttons) is displayed in.
    # زبانی که رابط کاربری خود بات (منوها، دکمه‌ها) با آن نمایش داده می‌شود.
    ui_lang: Mapped[str] = mapped_column(String(8), default="en")
    # Language articles are translated into for this user.
    # زبانی که مقالات برای این کاربر به آن ترجمه می‌شوند.
    target_lang: Mapped[str] = mapped_column(String(8), default="fa")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)


class UserDelivery(Base):
    """
    Records that a specific article has already been delivered to a
    specific user, so the delivery cycle never sends it twice.
    ثبت می‌کند که یک مقاله‌ی مشخص قبلاً به یک کاربر مشخص تحویل داده شده، تا
    چرخه‌ی تحویل هرگز آن را دوبار نفرستد.
    """

    __tablename__ = "user_deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_delivery"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    """
    An explicit per-feed follow, independent of category subscriptions.
    یک دنبال‌کردن صریح در سطح فید، مستقل از اشتراک دسته‌بندی.

    Used for probation feeds (the submitter follows their own feed before it
    reaches the shared pool) and for any feed a user wants to follow
    individually regardless of its category.
    برای فیدهای probation استفاده می‌شود (اضافه‌کننده فید خودش را قبل از ورود
    به استخر مشترک دنبال می‌کند) و برای هر فیدی که کاربر می‌خواهد صرف‌نظر از
    دسته‌بندی‌اش، جداگانه دنبال کند.
    """

    __tablename__ = "user_feed_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "feed_id", name="uq_user_feed_subscription"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), nullable=False)


class UserFeedMute(Base):
    __tablename__ = "user_feed_mutes"
    __table_args__ = (UniqueConstraint("user_id", "feed_id", name="uq_user_feed_mute"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), nullable=False)


class SavedItemStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"


class SavedItem(Base):
    __tablename__ = "saved_items"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_saved"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    status: Mapped[SavedItemStatus] = mapped_column(
        Enum(SavedItemStatus), default=SavedItemStatus.UNREAD
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
