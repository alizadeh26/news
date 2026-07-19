# Forex Bot Pro

ربات تحلیل و هشدار اخبار فارکس با تمرکز روی خبرهای مرتبط با **USD / EUR / GBP** از تقویم **Forex Factory**.

این پروژه خبرهای مهم و متوسط را ذخیره می‌کند، قبل از زمان خبر تحلیل سناریویی می‌سازد و نتیجه را به تلگرام می‌فرستد. همچنین از طریق دستورهای تلگرامی می‌توان وضعیت ربات و خبرهای بعدی را مشاهده کرد.

## قابلیت‌ها
- دریافت و استخراج خبرهای مرتبط با **USD / EUR / GBP**
- فیلتر روی **Medium** و **High impact**
- همگام‌سازی **ماهانه** در ابتدای هر ماه
- **refresh هفتگی** برای ماه جاری
- ذخیره state در **SQLite**
- هشدار **60 دقیقه قبل** از خبر
- هشدار **10 دقیقه قبل** از خبر
- نمایش زمان خبر در **UTC** و **New York time**
- ارسال پیام به **Telegram**
- پشتیبانی از دستورهای تلگرامی:
  - `/start`
  - `/status`
  - `/nextnews`
- سازگار با **GitHub Actions** و اجرای محلی
- نگه‌داری state در GitHub از طریق **auto-commit**

## فایل‌های پروژه
- `forex_bot_pro.py` : فایل اصلی پروژه
- `.env.example` : نمونه تنظیمات محیطی
- `requirements.txt` : وابستگی‌های پایتون
- `github_actions_forex_bot.yml` : نمونه workflow برای GitHub Actions

## پیش‌نیازها
- Python 3.11 یا بالاتر
- یک ربات تلگرام و Bot Token
- Chat ID تلگرام

## نصب محلی
```bash
pip install -r requirements.txt
```

## تنظیمات محیطی
از روی فایل `.env.example` یک فایل `.env` بساز، یا environment variableها را مستقیم ست کن.

### متغیرهای اصلی
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DB_PATH`
- `FOREX_FACTORY_MONTH_URL`
- `FOREX_FACTORY_TIMEZONE`
- `TARGET_TIMEZONE`
- `ALERT_BEFORE_MINUTES`
- `PREPARE_BEFORE_MINUTES`
- `TARGET_CURRENCIES`
- `TARGET_IMPACTS`
- `TELEGRAM_OFFSET_FILE`

## اجرای دستی دستورات
### همگام‌سازی ماهانه
```bash
python forex_bot_pro.py monthly-sync
```

### refresh هفتگی
```bash
python forex_bot_pro.py weekly-refresh
```

### dispatch هشدارهای نزدیک خبر
```bash
python forex_bot_pro.py dispatch
```

### پردازش دستورهای تلگرام
```bash
python forex_bot_pro.py telegram-commands
```

### خروجی JSON از رویدادها
```bash
python forex_bot_pro.py export-json --output events_export.json
```

## زمان‌بندی منطقی پروژه
### 1) Monthly Sync
در ابتدای هر ماه:
- صفحه تقویم Forex Factory خوانده می‌شود
- خبرهای مرتبط با USD / EUR / GBP استخراج می‌شوند
- فقط Medium / High impact نگه‌داری می‌شوند
- اطلاعات در SQLite ذخیره یا بروزرسانی می‌شود

### 2) Weekly Refresh
هفته‌ای یک بار:
- خبرهای ماه جاری دوباره بررسی می‌شوند
- اگر زمان یا ساختار خبرها تغییر کرده باشد، اطلاعات بروزرسانی می‌شود

### 3) Dispatcher
به‌صورت دوره‌ای:
- اگر تا خبر **60 دقیقه** مانده باشد، پیام آمادگی ارسال می‌شود
- اگر تا خبر **10 دقیقه** مانده باشد، پیام نهایی pre-news ارسال می‌شود

### 4) Telegram Commands
به‌صورت دوره‌ای:
- پیام‌های جدید تلگرام خوانده می‌شوند
- دستورهای `/status` و `/nextnews` پاسخ داده می‌شوند

## دستورهای تلگرامی
### `/start`
نمایش معرفی کوتاه ربات و لیست دستورات

### `/status`
نمایش:
- زمان فعلی UTC
- زمان فعلی نیویورک
- چند خبر بعدی ذخیره‌شده

### `/nextnews`
نمایش لیست خبرهای بعدی با:
- عنوان خبر
- ارز
- سطح اثر
- زمان UTC
- زمان New York

### `/today`
نمایش خبرهای برنامه‌ریزی‌شده همان روز بر اساس timezone نیویورک

## GitHub Actions
برای اجرای زمان‌بندی‌شده بدون VPS:
1. فایل workflow را در مسیر `.github/workflows/forex_bot.yml` قرار بده
2. در بخش **GitHub Secrets** این دو مقدار را بساز:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. به ریپو اجازه بده که GitHub Actions بتواند روی branch اصلی **push** انجام دهد

### زمان‌بندی پیشنهادی workflow
- **اول هر ماه**: اجرای `monthly-sync`
- **هر یکشنبه**: اجرای `weekly-refresh`
- **هر 5 دقیقه**: اجرای `dispatch`
- **هر 10 دقیقه**: اجرای `telegram-commands`

## state پایدار در GitHub Actions
چون GitHub Actions به‌صورت پیش‌فرض فایل‌ها را بین اجراها حفظ نمی‌کند، این پروژه state را با این روش حفظ می‌کند:
- دیتابیس SQLite داخل ریپو نگه‌داری می‌شود
- فایل offset مربوط به تلگرام هم داخل ریپو نگه‌داری می‌شود
- بعد از هر اجرا، اگر state تغییر کرده باشد، به‌صورت خودکار commit و push می‌شود

این روش برای پروژه‌های سبک و بدون VPS مناسب است.

## محدودیت‌ها و نکات مهم
- ساختار HTML سایت Forex Factory ممکن است در آینده تغییر کند
- parser فعلی برای ساختار متداول صفحه طراحی شده، اما ممکن است گاهی نیاز به تنظیم مجدد داشته باشد
- رویدادهای `All Day` و `Tentative` فعلاً نادیده گرفته می‌شوند
- برای استفاده production-grade بهتر است در آینده تست بیشتر روی HTML واقعی و سناریوهای تغییر تقویم انجام شود

## وضعیت فعلی موتور تحلیل
موتور تحلیل قبل از خبر نسبت به نسخه اولیه تقویت شده و حالا شامل این موارد است:
- وزن‌دهی قوی‌تر بر اساس نوع خبر
- دسته‌بندی رویدادها به `Tier 1`، `Tier 2`، `Tier 3`
- نگاشت دقیق‌تر اثر روی `EURUSD`، `GBPUSD` و `DXY`
- محاسبه `Confidence score`
- تولید `Bias strength` در سه سطح `Strong`، `Moderate` و `Mild`

## پیشنهاد توسعه بعدی
- افزودن دستور `/today`
- افزودن دستور `/event <keyword>`
- استخراج پایدارتر forecast / previous / actual
- ذخیره‌سازی حرفه‌ای‌تر به‌جای commit دیتابیس در ریپو
- Dockerfile
- تست‌های واحد و integration test
