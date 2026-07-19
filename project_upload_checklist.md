# چک‌لیست نهایی آپلود روی GitHub

## فایل‌های لازم
- [ ] `forex_bot_pro.py`
- [ ] `requirements.txt`
- [ ] `.env.example`
- [ ] `README.md`
- [ ] `.github/workflows/forex_bot.yml`

## Secrets لازم در GitHub
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `TELEGRAM_CHAT_ID`

## تنظیمات GitHub Actions
- [ ] Workflow permissions روی `Read and write` تنظیم شده
- [ ] branch protection جلوی push را نگرفته

## تست بعد از استقرار
- [ ] اجرای دستی workflow
- [ ] تست `/start`
- [ ] تست `/status`
- [ ] تست `/nextnews`
- [ ] بررسی ایجاد `forex_events.db`
- [ ] بررسی ایجاد `telegram_offset.txt`

## نکته مهم
اگر parser خبرها را درست استخراج نکرد، باید ساختار HTML واقعی Forex Factory دوباره بررسی و selectorها تنظیم شوند.
