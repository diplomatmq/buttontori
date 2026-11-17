-- ============================================================
--  Очистка очереди доставок подарков для конкретного юзера
--  Пользователь: 793216884
--  Таблица: prize_deliveries
-- ============================================================
--
--  Зачем: этот юзер накрутил бесплатные призы через команду /play
--  (ячейки давали гарантированный приз, и воркер автоматически
--  отправлял реальные подарки). Нужно убрать всё, что ему "должно"
--  быть отправлено.
--
--  Как запустить на сервере:
--    ssh root@142.248.83.52
--    cd /opt/bots/buttontori
--    docker compose exec -T postgres psql -U bot -d bot < cleanup_user_deliveries.sql
--
-- ============================================================

-- 1) Что будет удалено (предпросмотр строк)
SELECT delivery_id, user_id, prize_type, prize_value, status, attempts, created_at
FROM prize_deliveries
WHERE user_id = 793216884
ORDER BY delivery_id;

-- 2) Сводка по статусам
SELECT status, COUNT(*) AS cnt
FROM prize_deliveries
WHERE user_id = 793216884
GROUP BY status;

-- 3) Удаляем ВСЕ записи о доставках этого пользователя
DELETE FROM prize_deliveries
WHERE user_id = 793216884;

-- 4) Проверка: должно вернуть 0
SELECT COUNT(*) AS remaining
FROM prize_deliveries
WHERE user_id = 793216884;

-- ============================================================
-- 5) Поиск других накрутчиков: топ пользователей по числу доставок.
--    У нормальных игроков приз выпадает редко (нужно 777 или три BAR),
--    поэтому большие числа — повод присмотреться.
-- ============================================================
SELECT
    user_id,
    COUNT(*)                                   AS deliveries,
    COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
    COUNT(*) FILTER (WHERE status = 'pending')   AS pending,
    MIN(created_at)                            AS first_at,
    MAX(created_at)                            AS last_at
FROM prize_deliveries
GROUP BY user_id
ORDER BY deliveries DESC
LIMIT 30;

-- Если найдешь других накрутчиков, удали их доставки, подставив нужные id:
-- DELETE FROM prize_deliveries WHERE user_id IN (id1, id2, id3);
