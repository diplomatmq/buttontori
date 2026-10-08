-- Миграция user_id с INTEGER на BIGINT для поддержки больших Telegram ID

-- 1. Изменяем users.user_id
ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;

-- 2. Изменяем games.user_id
ALTER TABLE games ALTER COLUMN user_id TYPE BIGINT;

-- 3. Изменяем wins.user_id
ALTER TABLE wins ALTER COLUMN user_id TYPE BIGINT;

-- 4. Изменяем prize_deliveries.user_id
ALTER TABLE prize_deliveries ALTER COLUMN user_id TYPE BIGINT;

-- 5. Удаляем таблицу casino_games если существует (она пока пустая)
DROP TABLE IF EXISTS casino_games;

-- 6. Создаем casino_games с правильным типом
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
