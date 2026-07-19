# برنامه تقویت موتور تحلیل قبل از خبر

## اولویت‌های انتخاب‌شده
- وزن‌دهی بهتر نوع خبر
- نگاشت دقیق‌تر اثر روی EURUSD / GBPUSD / DXY
- امتیاز اطمینان (Confidence score)

## مسیر پیشنهادی ارتقا

### 1. وزن‌دهی بهتر نوع خبر
به‌جای وزن‌دهی ساده، خبرها در چند دسته قرار بگیرند:
- Tier 1: FOMC, ECB, BOE, CPI, NFP, Interest Rate
- Tier 2: GDP, PMI, Employment, Unemployment
- Tier 3: Retail Sales, Speeches, Secondary indicators

### 2. نگاشت دقیق‌تر روی جفت‌ارزها
#### برای USD خبر مثبت:
- DXY: bullish strong
- EURUSD: bearish strong
- GBPUSD: bearish strong

#### برای EUR خبر مثبت:
- EURUSD: bullish strong
- DXY: bearish mild
- GBPUSD: neutral to mild indirect

#### برای GBP خبر مثبت:
- GBPUSD: bullish strong
- DXY: neutral to mild indirect
- EURUSD: mostly neutral

### 3. Confidence score
امتیاز نهایی بر اساس این عوامل:
- impact level
- tier خبر
- currency relevance
- proximity to event
- keyword strength

خروجی نمونه:
- Confidence: 82/100
- Bias strength: Strong / Moderate / Mild

### 4. توسعه آینده
اگر بعداً داده‌های forecast/previous/actual به‌صورت پایدار استخراج شوند:
- pre-news bias دقیق‌تر
- post-release reaction model
- divergence analysis between forecast and actual

## پیشنهاد اجرای مرحله بعد
در مرحله بعد، بهتر است همین ارتقاها مستقیماً داخل `forex_bot_pro.py` اعمال شوند.
