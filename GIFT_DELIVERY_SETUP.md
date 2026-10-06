# 🎁 Система автоматической выдачи Telegram Star Gifts

## 📋 Описание

Автоматическая система выдачи подарков победителям игры 777 через Telegram MTProto API.

**Логика работы:**
```
Игрок выигрывает 777
  ↓
Получает приз (bear, heart, rose, gift, rocket, etc.)
  ↓
Приз добавляется в очередь доставки (БД: status=pending)
  ↓
Gift Worker обрабатывает очередь
  ↓
Отправляет подарок через MTProto API (sendGift)
  ↓
Подарок доставлен (БД: status=delivered)
```

## ✅ Возможности

- ✨ **Автоматическая выдача** подарков без ручной работы
- 🔄 **Повторные попытки** при временных ошибках (FloodWait)
- 📊 **Статистика доставок** для пользователей и админа
- 🛡️ **Защита от дублирования** через database locking
- 📝 **Подробное логирование** всех операций
- 🔐 **Безопасное хранение сессии** - авторизация только один раз
- ⚠️ **Обработка ошибок** с пометкой failed после 3 попыток

## 📦 Требования

- Python 3.11+
- PostgreSQL база данных
- Telegram Bot Token (от @BotFather)
- Telegram API_ID и API_HASH (от https://my.telegram.org)

## 🚀 Установка и настройка

### Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 2: Получение Telegram API credentials

1. Откройте https://my.telegram.org
2. Войдите в свой Telegram аккаунт (используйте аккаунт владельца бота)
3. Перейдите в раздел **"API development tools"**
4. Создайте новое приложение:
   - **App title**: Gift Delivery Bot (любое название)
   - **Short name**: giftbot (любое)
   - **Platform**: Other
5. Скопируйте `api_id` и `api_hash`

### Шаг 3: Настройка .env файла

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Обязательные параметры:
```env
# Основные
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_ID=ваш_telegram_id
ALLOWED_CHAT_ID=id_чата_где_работает_бот

# MTProto API
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELETHON_SESSION=sessions/owner

# База данных
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/database
```

### Шаг 4: Получение Gift IDs

Есть два способа:

#### Способ А: Через логи worker

1. Временно установите в `.env`:
   ```env
   LOG_LEVEL=DEBUG
   ```

2. Запустите авторизацию (только первый раз):
   ```bash
   python auth_session.py
   ```

3. Запустите worker:
   ```bash
   python -m gift_worker.worker
   ```

4. В логах увидите список доступных подарков:
   ```
   📦 Available gifts: 25
      Gift ID: 5170233102089322756, Stars: 15
      Gift ID: 5170145012310081615, Stars: 15
      ...
   ```

5. Добавьте нужные Gift IDs в `.env`:
   ```env
   GIFT_ID_BEAR=5170233102089322756
   GIFT_ID_HEARTS=5170145012310081615
   GIFT_ID_ROSE=5168103777563050263
   GIFT_ID_GIFT=5170250947678437525
   GIFT_ID_ROCKET=5170564780938756245
   ```

#### Способ Б: Использовать существующие IDs

Используйте IDs из `.env.example` (могут устареть со временем).

### Шаг 5: Первичная авторизация в Telegram

**⚠️ ВАЖНО: Запускается только ОДИН РАЗ!**

```bash
python auth_session.py
```

Скрипт попросит:
1. Номер телефона (в международном формате, например: +79991234567)
2. Код подтверждения из Telegram
3. Пароль 2FA (если включен)

После успешной авторизации создастся файл `sessions/owner.session`.

**🔒 Этот файл нужно сохранить!** Он содержит вашу сессию и позволяет работать без повторной авторизации.

### Шаг 6: Миграция базы данных

База данных обновится автоматически при запуске бота или worker.

Если нужно применить миграции вручную:
```bash
python bot.py  # или
python -m gift_worker.worker
```

## 🎮 Запуск системы

### Вариант 1: Раздельный запуск (рекомендуется)

**Терминал 1 - Бот:**
```bash
python bot.py
```

**Терминал 2 - Gift Worker:**
```bash
python -m gift_worker.worker
```

### Вариант 2: Docker Compose

```bash
docker-compose up -d
```

## 📊 Использование

### Команды пользователя

- `/start` - Начать работу с ботом
- `/play` - Начать игру
- `/stats` - Посмотреть статистику (включая доставки)
- `/help` - Справка

### Команды администратора

- `/admin` - Топ-10 игроков
- `/deliveries` - Статус очереди доставок

### Игра 777

1. Пользователь отправляет эмодзи казино 🎰
2. Если выпадает 777 (dice value = 64):
   - Показывается поле 5x5 с закрытыми подарками
   - Пользователь выбирает любую ячейку
   - Получает приз (bear, hearts, rose, gift, rocket, etc.)
   - Приз автоматически добавляется в очередь доставки

3. Gift Worker обрабатывает очередь:
   - Проверяет существование пользователя
   - Отправляет подарок через MTProto API
   - Помечает как delivered или failed

## 🔧 Настройки Worker

В `.env` можно настроить:

```env
# Максимум попыток доставки
MAX_DELIVERY_ATTEMPTS=3

# Интервал проверки очереди (секунды)
WORKER_POLL_INTERVAL=5

# Таймаут захвата задачи (минуты)
DELIVERY_CLAIM_TIMEOUT=5
```

## 🐛 Устранение проблем

### Worker не запускается

**Ошибка: "Telethon session is not authorized"**

Решение:
```bash
python auth_session.py
```

### Подарки не доставляются

1. Проверьте что worker запущен:
   ```bash
   python -m gift_worker.worker
   ```

2. Проверьте логи worker на ошибки

3. Убедитесь что Gift IDs настроены в `.env`

4. Проверьте команду `/deliveries` (для админа)

### FloodWaitError

Worker автоматически ждет нужное время и повторяет попытку.

### UserIdInvalidError

Пользователь недоступен или заблокировал бота. Доставка будет помечена как failed.

## 📁 Структура проекта

```
buttonTori/
├── bot.py                      # Основной бот
├── config.py                   # Конфигурация
├── auth_session.py             # Скрипт авторизации в Telegram
├── database/
│   ├── db.py                   # Работа с БД
│   └── models.py               # Модели SQLAlchemy
├── gift_worker/
│   ├── telegram.py             # MTProto клиент
│   └── worker.py               # Обработчик очереди доставок
├── sessions/
│   └── owner.session           # Telethon сессия (создается при auth)
├── .env                        # Конфигурация (не в git)
└── .env.example                # Пример конфигурации
```

## 🗄️ База данных

### Таблица prize_deliveries

```sql
CREATE TABLE prize_deliveries (
    delivery_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    prize_type VARCHAR(32) NOT NULL,
    prize_value INTEGER NOT NULL,
    gift_id VARCHAR(255),           -- Telegram gift_id
    status VARCHAR(16) DEFAULT 'pending',  -- pending/processing/delivered/failed
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    claimed_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Статусы доставки

- `pending` - Ожидает обработки
- `processing` - В процессе доставки (захвачено worker)
- `delivered` - Успешно доставлено
- `failed` - Не удалось доставить после всех попыток

## 🔐 Безопасность

### ⚠️ Важно!

1. **Не публикуйте .env файл** - он содержит токены и credentials
2. **Храните sessions/owner.session** в безопасности - это ваша авторизация
3. **Используйте ADMIN_ID** для ограничения доступа к админ-командам
4. **Используйте ALLOWED_CHAT_ID** для ограничения работы бота

### Что можно публиковать в Git:

- ✅ `.env.example`
- ✅ Весь исходный код
- ✅ `requirements.txt`

### Что НЕ публиковать:

- ❌ `.env`
- ❌ `sessions/*.session`
- ❌ API_ID и API_HASH

## 📝 Логирование

Worker подробно логирует все операции:

```
🚀 Worker ready! Waiting for deliveries...
📋 Cycle #1: Found 3 pending deliveries
📦 Обработка delivery_id=15, user_id=123456, prize=bear, attempt=1/3
✅ Delivery 15 успешно доставлен! User 123456 получил bear
```

Уровни логирования (`LOG_LEVEL` в `.env`):
- `DEBUG` - Максимум информации (включая Gift IDs)
- `INFO` - Стандартный режим (рекомендуется)
- `WARNING` - Только предупреждения
- `ERROR` - Только ошибки

## 🆘 Поддержка

Если возникли проблемы:

1. Проверьте логи worker и bot
2. Убедитесь что все зависимости установлены
3. Проверьте .env конфигурацию
4. Проверьте что session файл существует
5. Проверьте подключение к базе данных

## 📜 Лицензия

MIT License

---

**Готово! Система автоматической выдачи подарков настроена и готова к работе! 🎉**
