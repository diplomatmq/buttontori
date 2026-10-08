#!/bin/bash

echo "🔧 ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ"
echo ""
echo "Эта команда изменит тип user_id с INTEGER на BIGINT"
echo ""

SERVER="root@142.248.83.52"
PATH="/opt/bots/buttontori"

echo "📤 1. Загружаем обновленные файлы..."
scp database/models.py ${SERVER}:${PATH}/database/
scp database/db.py ${SERVER}:${PATH}/database/
scp bot.py ${SERVER}:${PATH}/

echo ""
echo "🗄️ 2. Применяем миграцию БД..."
ssh $SERVER << 'ENDSSH'
cd /opt/bots/buttontori

docker-compose exec -T db psql -U buttontori_user -d buttontori_db << 'ENDSQL'
ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;
ALTER TABLE games ALTER COLUMN user_id TYPE BIGINT;
ALTER TABLE prize_deliveries ALTER COLUMN user_id TYPE BIGINT;
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
ENDSQL

echo ""
echo "🔄 3. Перезапускаем контейнеры..."
docker-compose restart bot worker

echo ""
echo "⏳ Ожидаем запуска..."
sleep 3

echo ""
echo "📋 Проверяем логи бота:"
docker-compose logs bot --tail 20

echo ""
echo "📋 Проверяем логи worker:"
docker-compose logs worker --tail 10
ENDSSH

echo ""
echo "✅ Готово! Теперь бот должен работать с большими user_id"
