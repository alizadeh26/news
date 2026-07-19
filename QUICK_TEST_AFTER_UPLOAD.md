# تست سریع بعد از آپلود

## 1) قبل از اجرا
- فایل workflow را در `.github/workflows/forex_bot.yml` بگذار
- این Secrets را بساز:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- در Settings > Actions > General، گزینه `Read and write permissions` را فعال کن

## 2) اجرای دستی
- برو به تب `Actions`
- workflow را اجرا کن

## 3) چیزهایی که باید چک کنی
- job بدون خطا اجرا شود
- لاگ `monthly-sync` یا `dispatch` خطای parser نداشته باشد
- فایل `forex_events.db` بعد از اجرا در ریپو ظاهر شود
- بعد از دستور تلگرامی، فایل `telegram_offset.txt` هم ایجاد شود

## 4) تست تلگرام
به ربات این دستورها را بفرست:
- `/start`
- `/status`
- `/nextnews`
- `/today`

## 5) نشانه موفقیت
- ربات به دستورها جواب بدهد
- حداقل یک commit با پیام `Update forex bot state` ساخته شود
- زمان‌ها در پیام با `UTC` و `New York` نمایش داده شوند

## 6) اگر مشکل بود
- Token / Chat ID را چک کن
- permissionهای GitHub Actions را چک کن
- اگر خبرها خالی بودند، parser احتمالاً نیاز به تنظیم selector دارد
