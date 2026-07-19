# راهنمای نهایی تست پروژه بعد از آپلود روی GitHub

## هدف
این راهنما برای تست نهایی پروژه بعد از آپلود روی GitHub و فعال‌سازی GitHub Actions است.

## قبل از شروع
بررسی کن که این موارد انجام شده باشند:
- فایل‌های پروژه داخل ریپو قرار گرفته‌اند
- workflow در مسیر `.github/workflows/forex_bot.yml` قرار گرفته
- `TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID` در GitHub Secrets ساخته شده‌اند
- مجوز **Read and write permissions** برای Actions فعال شده است

---

## مرحله 1: تست اجرای دستی workflow
1. وارد تب **Actions** شو
2. workflow مربوط به Forex Bot را باز کن
3. روی **Run workflow** کلیک کن
4. منتظر بمان تا jobها اجرا شوند

### چیزی که باید ببینی
- workflow بدون خطای syntax اجرا شود
- Python و dependencyها نصب شوند
- اسکریپت بدون crash بالا بیاید

---

## مرحله 2: تست `monthly-sync`
این job باید:
- صفحه Forex Factory را بخواند
- رویدادهای مرتبط را parse کند
- دیتابیس SQLite را پر کند

### چک‌های لازم
- در لاگ job دنبال پیام‌هایی شبیه این بگرد:
  - `Monthly sync finished`
  - `Upserted X events`

### اگر مشکل دیدی
- احتمالاً parser نتوانسته جدول را پیدا کند
- یا ساختار HTML صفحه با selectorهای فعلی فرق دارد

---

## مرحله 3: تست ایجاد state در ریپو
بعد از اجرای sync یا dispatcher بررسی کن:
- فایل `forex_events.db` ایجاد شده باشد
- اگر پیام تلگرامی دریافت یا پردازش شده، فایل `telegram_offset.txt` هم ایجاد شود

### نتیجه مورد انتظار
اگر auto-commit درست کار کند، این فایل‌ها باید به ریپو push شوند.

---

## مرحله 4: تست `dispatch`
job مربوط به dispatch را اجرا کن.

### چیزی که باید چک شود
- اگر خبر نزدیک باشد، باید پیام تلگرامی ارسال شود
- اگر خبر نزدیک نباشد، اجرای job باید بدون خطا تمام شود

### لاگ‌های مطلوب
- `Preparation alert sent`
- `Final alert sent`
- یا حداقل اجرای بدون error

---

## مرحله 5: تست بات تلگرامی
در تلگرام این دستورها را بفرست:
- `/start`
- `/status`
- `/nextnews`

### خروجی مورد انتظار
#### `/start`
باید لیست دستورات را برگرداند

#### `/status`
باید این‌ها را نشان دهد:
- زمان فعلی UTC
- زمان فعلی نیویورک
- چند خبر بعدی

#### `/nextnews`
باید چند خبر بعدی را با زمان UTC و New York نشان دهد

---

## مرحله 6: تست auto-commit
بعد از اجرای `dispatch` یا `telegram-commands`:
- وارد تب **Commits** شو
- ببین commit جدیدی با پیام شبیه این ساخته شده باشد:
  - `Update forex bot state`

اگر این commit وجود نداشت:
- permissionهای GitHub Actions را بررسی کن
- branch protection را بررسی کن

---

## مرحله 7: تست زمان‌بندی
بعد از چند ساعت یا با صبر کمتر از طریق اجرای دستی jobها بررسی کن که:
- monthly sync کار می‌کند
- weekly refresh کار می‌کند
- dispatcher اجرا می‌شود
- telegram commands اجرا می‌شود

---

## مرحله 8: تست صحت زمان‌ها
در پیام‌های تلگرام بررسی کن:
- `Time (UTC)`
- `Time (New York)`

این دو باید با timezone مورد انتظار هماهنگ باشند.

---

## مرحله 9: تست موتور تحلیل
در پیام pre-news بررسی کن که این موارد نمایش داده شوند:
- `Confidence`
- `Bias strength`
- `Event tier`
- سناریوهای مربوط به `EURUSD`، `GBPUSD` و `DXY`

---

## مشکلات رایج
### 1. بات در تلگرام جواب نمی‌دهد
- Bot Token اشتباه است
- Chat ID اشتباه است
- هنوز به ربات پیام نداده‌ای
- job مربوط به `telegram-commands` اجرا نشده

### 2. دیتابیس ساخته نمی‌شود
- sync اجرا نشده
- parser داده‌ای پیدا نکرده
- permission نوشتن روی ریپو مشکل دارد

### 3. commit انجام نمی‌شود
- `contents: write` فعال نیست
- Workflow permissions روی read-only است
- branch protection مانع push می‌شود

### 4. خبرها خالی هستند
- selectorهای HTML نیاز به تنظیم دارند
- سایت ساختار متفاوتی برگردانده

---

## معیار موفقیت نهایی
اگر این 5 مورد درست بود، پروژه از نظر استقرار اولیه موفق است:
- workflow بدون خطا اجرا شود
- `forex_events.db` ساخته و ذخیره شود
- `/status` جواب بدهد
- `/nextnews` جواب بدهد
- حداقل یک state commit در ریپو ثبت شود
