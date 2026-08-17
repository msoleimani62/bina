# تغییرات این بسته — بینا (v0.1.1)

بر اساس بررسی گزارش کامل sarand (سویچ `--full`) روی commit `ec979e7`، به‌علاوه‌ی
دو دور اصلاح بعدی که روی خروجی واقعی `mypy`/`pytest --cov` روی دستگاه شما
انجام شد. فقط فایل‌های این بسته تغییر کرده یا اضافه شده‌اند؛ بقیه‌ی پروژه
دست‌نخورده است.

## دور ۱ — باگ‌های واقعی (از گزارش sarand)

1. **`bina/core/models.py`** — بحرانی. بدنه‌ی کلاس `UserFeedSubscription`
   به‌اشتباه داخل کلاس `UserDelivery` چسبیده بود؛ کلاس `UserFeedSubscription`
   عملاً وجود نداشت درحالی‌که در ۴ فایل دیگر import می‌شد → `ImportError` در
   کل زنجیره‌ی مخاطب‌یابی. دو کلاس جدا شدند.
2. **`bina/bot/scheduler.py`** — `datetime.now()` بدون timezone با
   `last_fetched_at` (timezone-aware) مقایسه می‌شد → کرش در اولین اجرای
   واقعی چرخه. به `datetime.now(UTC)` اصلاح شد.
3. اصلاحات lint واقعی: `functools.cache` به‌جای `lru_cache(maxsize=None)`
   (`bot/i18n.py`)، quote اضافی در type annotation (`core/models.py`)،
   ترتیب import (`core/ingest.py`, `tests/test_ingest.py`,
   `components/save/router.py`)، import بلااستفاده (`tests/test_delivery.py`).
4. README.md / README.fa.md بازنویسی و گسترش کامل؛ `assets/icon.png` اضافه شد؛
   ROADMAP.md/CONTRIBUTING.md/AI_BUILD_PROMPT.md که در گزارش sarand به‌خاطر
   بلوک کد تو در تو ناقص افتاده بودند، کامل بازیابی شدند.

✅ روی دستگاه واقعی تأیید شد: بعد از این دور، **۳۱ از ۳۱ تست پاس شد**
(قبلش با `ImportError` کلاً collect نمی‌شدند).

## دور ۲ — رفع ۱۷ خطای واقعی `mypy --strict`

- `pyproject.toml`: override برای `feedparser`/`apscheduler` (این دو پکیج
  اصلاً stub ندارند — نقص بالادستی، نه باگ پروژه).
- `bina/bot/i18n.py`: annotation صریح روی خروجی `json.loads` تا mypy آن را
  Any نداند.
- `bina/components/{subscriptions,save,mute}/router.py`: پارامتر `session`
  در ۳ تابع بدون type بود → `AsyncSession` اضافه شد.
- **یافته‌ی واقعی مهم‌تر:** در ۶ جا (`subscriptions`, `settings`, `save`,
  `mute` routers) کد فرض می‌کرد `callback.data` و `callback.message` همیشه
  مقدار دارند. در واقعیت تلگرام گاهی `callback.data=None` یا `message` را
  به‌صورت `InaccessibleMessage` (پیام قدیمی/غیرقابل‌دسترس) می‌فرستد — یعنی
  اگر کاربر روی دکمه‌ی یک پیام خیلی قدیمی می‌زد، `edit_reply_markup`/
  `edit_text`/`delete` می‌توانست با `AttributeError` کرش کند. با گارد
  `isinstance(callback.message, Message)` + بررسی `callback.data is None`
  در همه‌ی هندلرهای مربوطه اصلاح شد.

⚠️ این دور روی دستگاه شما اجرا **نشده** — لطفاً `mypy bina` را دوباره اجرا
کنید و اگر چیزی باقی ماند خبر بدهید.

## دور ۳ — تست‌های جدید برای رساندن پوشش به بالای ۸۰٪

پوشش تست قبل از این دور ۴۸٪ بود (کف مجاز در `pyproject.toml`: ۸۰٪)، چون
لایه‌ی روترهای aiogram و `bot/handlers/start.py` اصلاً تست نداشتند (۰٪
پوشش روی ۲۵۹+۲۷=۲۸۶ خط). این ۸ فایل تست جدید اضافه شدند:

- `tests/conftest.py` — دو fixture مشترک: `db_session` (دیتابیس
  in-memory که با `monkeypatch` به `bina.core.db.get_session()` وصل
  می‌شود) و `create_user` (فکتوری برای ساخت رکورد User تستی).
- `tests/telegram_fakes.py` — کمک‌کننده‌های ساخت `Message`/`CallbackQuery`
  ساختگی (`MagicMock(spec=...)`) از جمله حالت `InaccessibleMessage` برای
  تست همان گارد جدید دور ۲.
- `tests/test_start_handler.py` — هندلر `/start` (تشخیص زبان، جلوگیری از
  ساخت کاربر تکراری).
- `tests/test_subscriptions_router.py`, `test_mute_router.py`,
  `test_settings_router.py`, `test_save_router.py`,
  `test_feed_submission_router.py` — هرکدام تمام مسیرهای هر روتر را
  پوشش می‌دهند: بدون `from_user`/`data`، کاربر ناشناس، پیام
  غیرقابل‌دسترس، و مسیر موفق.

⚠️ **این دور، برخلاف دو دور قبل، هیچ‌جا روی دستگاه واقعی یا با pytest واقعی
اجرا نشده** — چون در محیط من نه شبکه هست نه `aiogram`/`sqlalchemy` نصب.
نوشته‌شده با بررسی دقیق خط‌به‌خط کد واقعی روترها، ولی احتمال دارد یک یا دو
دور اصلاح جزئی لازم باشد (مثلاً روی رفتار دقیق `MagicMock(spec=...)` با
مدل‌های pydantic آیوگرم). لطفاً `pytest -v` را اجرا کنید و خروجی کامل را
بفرستید تا هرچه لازم بود اصلاح شود.

## نکات جانبی (نیازی به تغییر فایل نداشتند)

- خروجی `bandit` نشان می‌دهد `.venv` هم داخل اسکن امنیتی رفته
  (۸۴۶٬۳۳۹ خط در برابر ۳٬۳۶۹ خط واقعی پروژه) — با
  `bandit -r bina/ tests/` به‌جای اسکن کل مسیر حل می‌شود.
- CI واقعی پروژه از `black --check .` استفاده می‌کند نه `ruff format` —
  ۲۲ فایلی که `black` می‌خواهد reformat کند را با یک اجرای
  `.venv/bin/python -m black .` مرتب کنید (فرمت خودکار، بدون خطر).
