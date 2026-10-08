# 🚀 Деплой обновлений на сервер

## Что изменилось:
- ✅ Убраны все комментарии из кода
- ✅ `/start` упрощен до "Привет, {username}!"
- ✅ Игры хранятся в БД - кнопки не умирают
- ✅ Все функции async - нет блокировок
- ✅ BAR медведь: автовыдача + уведомление админу
- ✅ Бриллиант: автовыдача настроена

## Команды для деплоя:

### 1. Загрузить обновленные файлы на сервер:

```bash
scp bot.py root@142.248.83.52:/opt/bots/buttontori/
scp database/models.py root@142.248.83.52:/opt/bots/buttontori/database/
scp database/db.py root@142.248.83.52:/opt/bots/buttontori/database/
```

### 2. Зайти на сервер:

```bash
ssh root@142.248.83.52
cd /opt/bots/buttontori
```

### 3. Пересобрать и перезапустить контейнеры:

```bash
docker-compose down
docker-compose up -d --build
```

### 4. Проверить логи:

```bash
docker-compose logs -f bot
docker-compose logs -f worker
```

### 5. Проверить что таблица создалась:

```bash
docker-compose exec db psql -U buttontori_user -d buttontori_db -c "\d casino_games"
```

Должна показаться структура таблицы с полями:
- game_id (PRIMARY KEY)
- user_id
- source_message_id
- field
- selected
- finished
- current_prize
- stage
- upgrade_target
- upgrade_winner
- upgrade_slots
- upgrade_revealed
- upgrade_started
- prize_claimed
- bar_bear_index
- bar_selected
- bar_revealed
- created_at

## Проверка работы:

1. Отправь в чат 🎰 казино
2. Если выпадет 777 - нажми на кнопку
3. Подожди 1 час
4. Нажми на другую кнопку - должна работать!

## Если что-то пошло не так:

### Таблица не создалась:
```bash
docker-compose exec bot python -c "import asyncio; from database.db import Database; from config import DATABASE_URL; asyncio.run(Database(DATABASE_URL).init_db())"
```

### Бот не запускается:
```bash
docker-compose logs bot --tail 100
```

### Worker не работает:
```bash
docker-compose logs worker --tail 100
```

### Полная переустановка (осторожно - удалит данные!):
```bash
docker-compose down -v
docker-compose up -d --build
```
