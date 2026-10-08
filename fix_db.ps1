# PowerShell скрипт для исправления БД

$SERVER = "root@142.248.83.52"
$PATH = "/opt/bots/buttontori"

Write-Host "🔧 ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ" -ForegroundColor Green
Write-Host ""
Write-Host "Эта команда изменит тип user_id с INTEGER на BIGINT" -ForegroundColor Yellow
Write-Host ""

Write-Host "📤 1. Загружаем обновленные файлы..." -ForegroundColor Cyan
scp database/models.py "${SERVER}:${PATH}/database/"
scp database/db.py "${SERVER}:${PATH}/database/"
scp bot.py "${SERVER}:${PATH}/"

Write-Host ""
Write-Host "🗄️ 2. Применяем миграцию БД..." -ForegroundColor Cyan

$migrationSQL = @"
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
"@

ssh $SERVER "cd $PATH && echo `"$migrationSQL`" | docker-compose exec -T db psql -U buttontori_user -d buttontori_db"

Write-Host ""
Write-Host "🔄 3. Перезапускаем контейнеры..." -ForegroundColor Cyan
ssh $SERVER "cd $PATH && docker-compose restart bot worker"

Write-Host ""
Write-Host "⏳ Ожидаем запуска..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "📋 Проверяем логи бота:" -ForegroundColor Yellow
ssh $SERVER "cd $PATH && docker-compose logs bot --tail 20"

Write-Host ""
Write-Host "📋 Проверяем логи worker:" -ForegroundColor Yellow
ssh $SERVER "cd $PATH && docker-compose logs worker --tail 10"

Write-Host ""
Write-Host "✅ Готово! Теперь бот должен работать с большими user_id" -ForegroundColor Green
