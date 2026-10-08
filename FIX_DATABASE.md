# 🔧 СРОЧНОЕ ИСПРАВЛЕНИЕ БД

## Проблема:
User ID слишком большие для INT32 (например: 7077664742, 8890630065)
PostgreSQL INTEGER поддерживает только до ~2.1 млрд

## Решение:

### ВАРИАНТ 1: Быстрый (удалить и пересоздать)

```bash
ssh root@142.248.83.52
cd /opt/bots/buttontori

# Остановить контейнеры
docker-compose down

# Удалить старые данные (ОСТОРОЖНО!)
docker volume rm buttontori_postgres_data

# Загрузить новые файлы с вашего компьютера:
# scp database/models.py root@142.248.83.52:/opt/bots/buttontori/database/
# scp bot.py root@142.248.83.52:/opt/bots/buttontori/

# Запустить заново - создастся новая БД с BIGINT
docker-compose up -d --build

# Проверить логи
docker-compose logs -f bot
```

### ВАРИАНТ 2: Безопасный (миграция с сохранением данных)

```bash
ssh root@142.248.83.52
cd /opt/bots/buttontori

# 1. Подключиться к БД
docker-compose exec db psql -U buttontori_user -d buttontori_db

# 2. Выполнить миграцию (скопировать команды ниже):
```

```sql
-- Изменяем users.user_id
ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;

-- Изменяем games.user_id
ALTER TABLE games ALTER COLUMN user_id TYPE BIGINT;

-- Изменяем wins.user_id (если есть)
ALTER TABLE wins ALTER COLUMN user_id TYPE BIGINT;

-- Изменяем prize_deliveries.user_id
ALTER TABLE prize_deliveries ALTER COLUMN user_id TYPE BIGINT;

-- Удаляем и пересоздаем casino_games
DROP TABLE IF EXISTS casino_games;

CREATE TABLE casino_games (
    game_id VARCHAR(100) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    source_message_id INTEGER NOT NULL,
    field TEXT,
    selected INTEGER DEFAULT -1,
    finished BOOLEAN DEFAULT FALSE,
    current_prize VARCHAR(32),
    stage INTEGER,
    upgrade_target VARCHAR(32),
    upgrade_winner INTEGER,
    upgrade_slots INTEGER DEFAULT 0,
    upgrade_revealed TEXT DEFAULT '{}',
    upgrade_started BOOLEAN DEFAULT FALSE,
    prize_claimed BOOLEAN DEFAULT FALSE,
    bar_bear_index INTEGER,
    bar_selected INTEGER DEFAULT -1,
    bar_revealed TEXT DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_casino_games_user_id ON casino_games(user_id);

-- Выйти из psql
\q
```

```bash
# 3. Загрузить обновленные файлы
# На вашем компьютере:
scp database/models.py root@142.248.83.52:/opt/bots/buttontori/database/
scp bot.py root@142.248.83.52:/opt/bots/buttontori/

# 4. На сервере - перезапустить контейнеры
docker-compose restart bot worker

# 5. Проверить логи
docker-compose logs -f bot worker
```

## Проверка что всё работает:

```bash
# Проверить структуру таблицы
docker-compose exec db psql -U buttontori_user -d buttontori_db -c "\d casino_games"

# Должно показать:
# user_id | bigint | not null
```

## После исправления:

Попроси пользователя отправить 🎰 снова - теперь должно работать!
