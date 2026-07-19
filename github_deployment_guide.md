# راهنمای قدم‌به‌قدم استقرار Forex Bot Pro روی GitHub

## هدف
این راهنما کمک می‌کند پروژه را روی GitHub قرار بدهی و با GitHub Actions بدون VPS اجرا کنی.

## فایل‌هایی که باید داخل ریپو داشته باشی
- `forex_bot_pro.py`
- `requirements.txt`
- `.env.example`
- `README.md`
- `.github/workflows/forex_bot.yml`

> فایل `github_actions_forex_bot.yml` را بعد از آپلود، به مسیر بالا منتقل کن و نامش را `forex_bot.yml` بگذار.

---

## مرحله 1: ساخت ریپو در GitHub
1. وارد GitHub شو.
2. روی **New repository** کلیک کن.
3. یک نام مثل `forex-bot-pro` انتخاب کن.
4. ریپو را بساز.

---

## مرحله 2: آپلود فایل‌ها
فایل‌های پروژه را داخل ریپو قرار بده:
- `forex_bot_pro.py`
- `requirements.txt`
- `.env.example`
- `README.md`

سپس فایل workflow را در این مسیر قرار بده:

```text
.github/workflows/forex_bot.yml
```

---

## مرحله 3: ساخت GitHub Secrets
داخل ریپو:
1. برو به **Settings**
2. سپس **Secrets and variables**
3. سپس **Actions**
4. این دو secret را بساز:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

---

## مرحله 4: فعال کردن مجوز write برای GitHub Actions
برای اینکه state پروژه در SQLite و offset تلگرام بعد از هر اجرا حفظ شود، workflow باید بتواند commit و push انجام دهد.

بررسی کن که:
- در تنظیمات ریپو، GitHub Actions مجاز به **Read and write permissions** باشد

مسیر معمول:
1. **Settings**
2. **Actions**
3. **General**
4. بخش **Workflow permissions**
5. گزینه **Read and write permissions** را فعال کن

---

## مرحله 5: اجرای دستی اولین بار
بعد از آپلود فایل‌ها:
1. وارد تب **Actions** شو
2. workflow را باز کن
3. روی **Run workflow** کلیک کن

این کار کمک می‌کند اولین اجرای تستی انجام شود.

---

## مرحله 6: بررسی اجرای زمان‌بندی‌شده
workflow این jobها را دارد:
- اول هر ماه: `monthly-sync`
- هر یکشنبه: `weekly-refresh`
- هر 5 دقیقه: `dispatch`
- هر 10 دقیقه: `telegram-commands`

---

## مرحله 7: تست بات تلگرامی
در تلگرام به رباتت این دستورها را بفرست:
- `/start`
- `/status`
- `/nextnews`

اگر همه‌چیز درست باشد، ربات باید پاسخ بدهد.

---

## مرحله 8: بررسی فایل‌های state
بعد از چند اجرا، ممکن است این فایل‌ها داخل ریپو ایجاد یا آپدیت شوند:
- `forex_events.db`
- `telegram_offset.txt`

این طبیعی است، چون پروژه برای حالت بدون VPS state را داخل ریپو نگه می‌دارد.

---

## مشکلات رایج
### 1. بات تلگرام پاسخ نمی‌دهد
بررسی کن:
- Bot Token درست باشد
- Chat ID درست باشد
- حداقل یک بار به ربات پیام داده باشی

### 2. workflow push نمی‌کند
بررسی کن:
- Workflow permissions روی **Read and write** باشد
- branch protection مانع push نشده باشد

### 3. خبرها استخراج نمی‌شوند
احتمال دارد:
- ساختار HTML Forex Factory تغییر کرده باشد
- parser نیاز به تنظیم مجدد داشته باشد

### 4. زمان خبرها اشتباه است
بررسی کن:
- `FOREX_FACTORY_TIMEZONE=America/New_York`
- `TARGET_TIMEZONE=UTC`

---

## پیشنهاد استقرار بهتر در آینده
اگر بعداً بخواهی نسخه حرفه‌ای‌تر و پایدارتر داشته باشی:
- از VPS یا Render/Railway استفاده کن
- state را به storage جدا منتقل کن
- parser را با HTML واقعی بیشتر تست کن
- لاگ‌گیری و error alert اضافه کن
