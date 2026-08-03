# Promise Bot (ربات ثبت قول)

یک ربات تلگرامی حرفه‌ای و امن برای ثبت و مدیریت قول‌ها و تعهدات بین دوستان با قابلیت پشتیبانی از چت خصوصی و گروه‌ها، تاریخ شمسی، و مدیریت وضعیت‌ها (FSM).

## امکانات
- **ثبت قول به خود یا دوست**: امکان ثبت تعهد شخصی یا ارسال درخواست قول به دوستان
- **مدیریت تایید/رد**: ارسال دکمه‌های تایید و رد برای شخص مقابل همراه با لینک دعوت اختصاصی در صورت عدم استارت ربات
- **لیست قول‌ها**: مشاهده قول‌های داده شده و دریافتی با تبدیل تاریخ دقیق به تقویم جلالی (شمسی)
- **پشتیبانی کامل از گروه‌ها**: تفکیک کامل Stateها در گروه‌ها و کنترل دسترسی دکمه‌های شیشه‌ای (Callback Query)
- **معماری مدرن**: Python 3.12, aiogram 3.x, SQLAlchemy Async, SQLite, Docker
- **دستور گروهی `/promise`**: ثبت قول در گروه با mention یا reply
- **پروفایل و امتیاز اعتبار**: محاسبه اعتبار بر اساس قول‌های انجام‌شده/نقض‌شده

## راه‌اندازی و اجرا

1. فایل `.env` را ایجاد کرده و توکن ربات خود را قرار دهید:
```env
BOT_TOKEN=your_bot_token_here
DB_PATH=promise_bot.db
```

2. اجرا با Docker Compose:
```bash
docker-compose up -d --build
```

3. یا اجرای محلی:
```bash
pip install -r requirements.txt
python bot.py
```

## مدیریت Migration دیتابیس (Alembic)

از این نسخه به بعد، تمام تغییرات اسکیمای دیتابیس باید از طریق **Alembic** مدیریت شوند، نه دستی یا `create_all`.

### پیش‌نیازها
```bash
pip install alembic
```

### دستورهای رایج

**ساخت migration جدید (بعد از تغییر مدل‌ها در `src/database/models.py`):**
```bash
alembic revision --autogenerate -m "توضیح تغییرات"
```

**اعمال migrationها روی دیتابیس:**
```bash
alembic upgrade head
```

**مشاهده تاریخچه migrationها:**
```bash
alembic history
```

**بررسی وضعیت فعلی:**
```bash
alembic current
```

### نکات مهم
- **هرگز** مستقیماً `CREATE TABLE` یا `ALTER TABLE` دستی نزنی
- **هرگز** `Base.metadata.create_all` برای migration استفاده نکن (فقط برای تست‌ها یا دیتابیس تازه مناسب است)
- قبل از `alembic upgrade head` در production، **بک‌آپ از فایل دیتابیس بگیر**
- Migrationهای تولیدشده در `alembic/versions/` باید به گیت کامیت بشن

### Migration اولیه (Baseline)
نسخه فعلی (`4f5f3043495c`) شامل اسکیمای کامل فاز ۲ است:
- جدول `users` با فیلدهای telegram_id, username, full_name, has_started_bot, created_at
- جدول `promises` با promise_id, content, giver_id, receiver_id, target_type, status (PENDING/CONFIRMED/REJECTED/DONE/BROKEN), created_at

## تست‌ها
```bash
pytest -v
```
تمام ۱۲ تست (شامل FSM handlers، promises، credibility score، group commands) باید پاس شوند.