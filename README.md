# Gift Caps Bot

Бот для игры "Джекпот" на aiogram 3.x и SQLite (WAL).

## Установка

```bash
pip install -r requirements.txt
```

Отредактируйте `.env`:
```env
BOT_TOKEN=ваш_токен
ADMIN_ID=ваш_id
```

## Запуск

**Без Docker:**
```bash
python bot.py
```

**С Docker:**
```bash
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```
