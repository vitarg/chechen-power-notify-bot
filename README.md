# Chechen Power Notify

Telegram-бот для уведомлений о плановых ограничениях электроснабжения по данным АО "Чеченэнерго".

## MVP

- Источник: `https://chechenenergo.ru/wp-json/tribe/events/v1/events`.
- Бот: aiogram 3.
- База: PostgreSQL.
- Планировщик: APScheduler внутри процесса бота.
- Деплой: Python virtualenv + systemd, без Docker.

## Локальный запуск

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.main
```

## Основные команды

Пользовательские:

```text
/start
/addresses
/add_address
/history
/help
/delete_me
```

Админские:

```text
/sync
/sync_dry_run
/latest
/stats
/sources
/broadcast
```

## Деплой

См. [deploy/ubuntu-24.04.md](deploy/ubuntu-24.04.md).

