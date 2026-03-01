# Servio (servio_uz_bot)

Production-ready шаблон SaaS-проекта Telegram-бота для онлайн-записи (multi-tenant).

## Stack
- Python 3.12+
- Django 5+ (совместимый код)
- DRF
- PostgreSQL
- Redis
- Celery + Celery Beat
- aiogram 3+
- Docker / docker-compose

## Структура
- `backend/config` — настройки Django, Celery, URL.
- `backend/apps/tenants` — бизнесы (тенанты).
- `backend/apps/accounts` — custom User + Customer.
- `backend/apps/services` — услуги, сотрудники, график работы.
- `backend/apps/bookings` — записи, API слотов, Celery reminders.
- `backend/bot` — Telegram bot flow `/start`.

## Быстрый старт
1. Скопируйте env:
   ```bash
   cp .env.example .env
   ```
2. Заполните `TELEGRAM_BOT_TOKEN`.
3. Запустите:
   ```bash
   docker-compose up --build
   ```
4. Создайте superuser:
   ```bash
   docker-compose exec django python manage.py createsuperuser
   ```
5. Откройте админку: `http://localhost:8000/admin/`

## API
- `GET /api/tenants/<tenant_id>/services/` — список услуг бизнеса
- `GET /api/tenants/<tenant_id>/slots/?service_id=<id>&date=YYYY-MM-DD` — доступные слоты
- `POST /api/bookings/` — создание записи
- `GET /api/tenants/<tenant_id>/bookings/` — список записей бизнеса (auth required)

## Пример payload для создания записи
```json
{
  "tenant": 1,
  "customer_telegram_id": 123456789,
  "service": 2,
  "staff": null,
  "start_datetime": "2026-02-24T09:30:00+05:00",
  "status": "confirmed",
  "comment": "Первичный визит"
}
```

## Напоминания
Celery Beat запускает задачу `send_booking_reminders` каждую минуту.
Задача отправляет Telegram-напоминание клиенту за ~2 часа до записи со статусом `confirmed`.
