# 🎁 Gift Caps Bot

Telegram бот для игры "Джекпот 777" с **автоматической выдачей Telegram Star Gifts** через MTProto API.

## ✨ Возможности

- 🎰 Игра в казино с выпадением 777
- 🎁 **Автоматическая выдача подарков** победителям
- 🔄 Надежная система очереди с повторными попытками
- 📊 Статистика доставок для пользователей и админа
- 🛡️ Защита от дублирования и ошибок
- 📝 Подробное логирование всех операций

## 🚀 Быстрый старт

### 1. Установка

```bash
pip install -r requirements.txt
cp .env.example .env
```

### 2. Настройка .env

Заполните обязательные поля:
```env
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_ID=ваш_telegram_id
TELEGRAM_API_ID=12345678                        # с https://my.telegram.org
TELEGRAM_API_HASH=abcdef1234567890              # с https://my.telegram.org
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
```

### 3. Авторизация в Telegram (один раз!)

```bash
python auth_session.py
```

Введите номер телефона, код из Telegram и пароль 2FA (если есть).

### 4. Получение Gift IDs

```bash
python test_gifts.py
```

Скопируйте Gift IDs в `.env`:
```env
GIFT_ID_BEAR=5170233102089322756
GIFT_ID_HEARTS=5170145012310081615
GIFT_ID_ROSE=5168103777563050263
...
```

### 5. Запуск

**Без Docker:**
```bash
# Терминал 1
python bot.py

# Терминал 2
python -m gift_worker.worker
```

**С Docker (на сервере):**
```bash
# Сначала на локальной машине создайте session:
python auth_session.py

# Загрузите проект на сервер (включая .env и sessions/)
# Затем на сервере:
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f
```

**📖 Подробно о Docker:** См. [DOCKER_SETUP.md](DOCKER_SETUP.md)

## 📖 Документация

- **[QUICK_START.md](QUICK_START.md)** - Быстрая настройка за 5 минут
- **[GIFT_DELIVERY_SETUP.md](GIFT_DELIVERY_SETUP.md)** - Полная документация системы

## 🎮 Как это работает

```
Пользователь играет в 777
         ↓
    Выпадает приз
         ↓
  Добавляется в очередь (БД)
         ↓
   Gift Worker обрабатывает
         ↓
Отправка через MTProto API (sendGift)
         ↓
   Подарок у победителя!
```

## 📊 Команды

### Для пользователей
- `/start` - Начать работу
- `/play` - Начать игру
- `/stats` - Статистика (включая доставки)
- `/help` - Справка

### Для администратора
- `/admin` - Топ игроков
- `/deliveries` - Статус очереди доставок

## 🔧 Технологии

- **aiogram 3.x** - Telegram Bot API
- **Telethon** - MTProto API для отправки подарков
- **SQLAlchemy + asyncpg** - Асинхронная работа с PostgreSQL
- **PostgreSQL** - Очередь доставок и статистика

## 🛡️ Безопасность

⚠️ **Не публикуйте:**
- `.env` файл
- `sessions/*.session` файлы
- `API_ID` и `API_HASH`

✅ **Можно публиковать:**
- Весь исходный код
- `.env.example`
- `requirements.txt`

## 🐛 Решение проблем

| Проблема | Решение |
|----------|---------|
| Worker не запускается | `python auth_session.py` |
| Подарки не доставляются | Проверьте Gift IDs в `.env` |
| FloodWaitError | Worker автоматически ждет |
| Session expired | Удалите session файл и запустите `auth_session.py` |

## 📁 Структура проекта

```
buttonTori/
├── bot.py                  # Основной бот
├── auth_session.py         # Авторизация в Telegram
├── test_gifts.py           # Получение Gift IDs
├── config.py               # Конфигурация
├── database/
│   ├── db.py              # Работа с БД
│   └── models.py          # Модели
├── gift_worker/
│   ├── telegram.py        # MTProto клиент
│   └── worker.py          # Обработчик очереди
├── sessions/
│   └── owner.session      # Telethon session
├── .env                   # Конфигурация (не в git!)
├── QUICK_START.md         # Быстрый старт
└── GIFT_DELIVERY_SETUP.md # Полная документация
```

## 📜 Лицензия

MIT License

---

**🎉 Готово к запуску!** Следуйте [QUICK_START.md](QUICK_START.md) для начала работы.
