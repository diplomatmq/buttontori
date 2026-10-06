# 🛡️ Обработка ошибок Gift Delivery System

## Типы ошибок и их обработка

### 1. ❌ Постоянные ошибки (Failed after max attempts)

Эти ошибки приводят к пометке доставки как `failed` после 3 попыток:

#### UserIdInvalidError
- **Причина**: Пользователь не найден или недействителен
- **Действие**: Попытки исчерпаны → status = failed
- **Решение**: Проверить правильность user_id

#### UserNotMutualContactError
- **Причина**: Пользователь недоступен (не mutual contact)
- **Действие**: Попытки исчерпаны → status = failed
- **Решение**: Пользователь должен начать диалог с ботом или отправителем

### 2. ⏳ Временные ошибки (Retry)

Эти ошибки приводят к повторной попытке:

#### FloodWaitError
- **Причина**: Telegram rate limiting
- **Действие**: Worker ждет указанное время, затем повторяет
- **Поведение**: 
  - Если wait < 5 минут → ждет и повторяет
  - Счетчик attempts увеличивается
  - После 3 попыток → status = failed

### 3. 💰 Недостаток Stars (Infinite retry)

**InsufficientStarsError** - особый тип ошибки:

#### Поведение
```
Попытка отправить подарок
  ↓
Недостаточно Stars на балансе
  ↓
НЕ увеличивается счетчик attempts
  ↓
Delivery остается в очереди (status = pending)
  ↓
Админ получает уведомление
  ↓
Worker ждет 30 секунд
  ↓
Повторяет попытку (бесконечно, пока не пополнится баланс)
```

#### Характеристики
- ✅ **Не исчерпывает попытки** - доставка всегда остается в очереди
- ✅ **Уведомление админа** - отправляется сообщение о недостатке Stars
- ✅ **Автоматическое продолжение** - после пополнения баланса доставка продолжится
- ⏰ **Увеличенная задержка** - 30 секунд между попытками (вместо стандартных 0.5)

#### Сообщение админу
```
⚠️ Недостаточно Stars на балансе!

Подарок для user_id=123456789
Приз: bear
Gift ID: 5170233102089322756

💰 Пополните баланс Stars для продолжения доставки.
Подарок останется в очереди.
```

#### Как пополнить Stars
1. Откройте Telegram
2. Перейдите в @PremiumBot или любой бот продажи Stars
3. Купите необходимое количество Stars
4. Worker автоматически продолжит доставку при следующей попытке

### 4. 🔧 Конфигурационные ошибки

#### Gift ID not configured
- **Причина**: В .env не указан GIFT_ID для приза
- **Действие**: status = failed
- **Решение**: Добавить Gift ID в .env

#### Session not authorized
- **Причина**: Session файл не существует или истек
- **Действие**: Worker не запускается
- **Решение**: Запустить `python auth_session.py`

## Логирование

### Уровни логов

#### INFO
```
✅ Delivery 15 успешно доставлен! User 123456 получил bear
```

#### WARNING
```
⏳ Delivery 20: FloodWait: need to wait 60 seconds
💰 Delivery 25: Insufficient Stars balance
⏸️  Подарок останется в очереди до пополнения баланса Stars
```

#### ERROR
```
❌ Delivery 30: UserIdInvalidError: User not found
❌ Неверный user_id=999999: User does not exist
```

## Мониторинг

### Команда /deliveries (для админа)

Показывает текущий статус очереди:
```
📦 Очередь доставок

Всего в очереди: 5

1. Delivery #15
2. Delivery #20
3. Delivery #25
...

💡 Проверьте:
• Gift Worker запущен?
• Session файл существует?
• Gift IDs настроены в .env?
```

### База данных

Проверить доставки с ошибками:
```sql
-- Доставки с недостатком Stars
SELECT * FROM prize_deliveries 
WHERE status = 'pending' 
  AND last_error LIKE '%Insufficient Stars%';

-- Доставки с исчерпанными попытками
SELECT * FROM prize_deliveries 
WHERE status = 'failed' 
  AND attempts >= 3;
```

## Диагностика проблем

### Подарки не доставляются

1. **Проверить логи worker:**
   ```bash
   python -m gift_worker.worker
   ```

2. **Проверить очередь:**
   - Команда `/deliveries` в боте (для админа)
   - Или SQL: `SELECT * FROM prize_deliveries WHERE status = 'pending'`

3. **Проверить баланс Stars:**
   - Если видите `Insufficient Stars` → пополните баланс

4. **Проверить Gift IDs:**
   - Запустить: `python test_gifts.py`
   - Сравнить с .env

### Worker падает

1. **Session проблемы:**
   ```bash
   python auth_session.py
   ```

2. **API credentials:**
   - Проверить TELEGRAM_API_ID и TELEGRAM_API_HASH в .env

3. **База данных:**
   - Проверить DATABASE_URL
   - Убедиться что PostgreSQL запущен

## Статистика ошибок

### По типам
```python
# В логах worker показывает:
📋 Cycle #100: Found 3 pending deliveries
✅ 2 успешно доставлено
⏳ 1 FloodWait (повтор через 60 сек)
💰 0 Insufficient Stars
```

### В базе данных
```sql
-- Статистика по статусам
SELECT status, COUNT(*) as count 
FROM prize_deliveries 
GROUP BY status;

-- Топ ошибок
SELECT last_error, COUNT(*) as count 
FROM prize_deliveries 
WHERE status = 'failed' 
GROUP BY last_error 
ORDER BY count DESC 
LIMIT 10;
```

---

**📌 Важно:** Ошибка "Insufficient Stars" НЕ исчерпывает попытки доставки. Подарок всегда остается в очереди и будет доставлен после пополнения баланса.
