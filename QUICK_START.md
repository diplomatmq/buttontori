# 🚀 Быстрый старт - Gift Delivery System

## 📋 Минимальные шаги для запуска

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Создание .env файла
```bash
cp .env.example .env
```

Заполните обязательные поля в `.env`:
```env
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_ID=ваш_telegram_id
TELEGRAM_API_ID=12345678                        # с https://my.telegram.org
TELEGRAM_API_HASH=abcdef1234567890abcdef123456  # с https://my.telegram.org
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
```

### 3. Авторизация в Telegram (ОДИН РАЗ!)
```bash
python auth_session.py
```

Введите:
- Номер телефона (+79991234567)
- Код из Telegram
- Пароль 2FA (если есть)

✅ Создастся файл `sessions/owner.session` - сохраните его!

### 4. Получение Gift IDs

**Вариант A** (рекомендуется):
```bash
# Установите LOG_LEVEL=DEBUG в .env
python -m gift_worker.worker
# Скопируйте Gift IDs из логов в .env
```

**Вариант B**: Используйте IDs из `.env.example`

### 5. Запуск системы

**Терминал 1:**
```bash
python bot.py
```

**Терминал 2:**
```bash
python -m gift_worker.worker
```

## ✅ Проверка работы

1. Отправьте боту команду `/start`
2. Отправьте эмодзи казино 🎰 в разрешенный чат
3. Если выпадет 777 - выберите приз
4. Проверьте очередь: `/deliveries` (для админа)
5. Worker автоматически доставит подарок

## 🐳 Запуск через Docker

Если у вас на сервере один терминал и Docker:

```bash
# 1. Подготовка на локальной машине (создание session)
pip install -r requirements.txt
python auth_session.py  # Создаст sessions/owner.session

# 2. Загрузите проект на сервер (включая .env и sessions/)
scp -r buttonTori/ user@server:/path/to/

# 3. На сервере запустите Docker
ssh user@server
cd /path/to/buttonTori
docker-compose up -d --build

# 4. Проверьте логи
docker-compose logs -f          # Все логи
docker-compose logs -f worker   # Только worker
docker-compose logs -f bot      # Только bot
```

**📖 Подробная инструкция:** См. [DOCKER_SETUP.md](DOCKER_SETUP.md)

## 📊 Полезные команды

```bash
# Посмотреть статус очереди доставок (для админа в боте)
/deliveries

# Посмотреть свою статистику (в боте)
/stats

# Перезапустить worker
Ctrl+C  # остановить
python -m gift_worker.worker  # запустить снова
```

## 🐛 Проблемы?

| Проблема | Решение |
|----------|---------|
| Worker не запускается | `python auth_session.py` |
| Подарки не доставляются | Проверьте Gift IDs в `.env` |
| FloodWaitError | Worker автоматически ждет |
| **💰 Insufficient Stars** | **Пополните баланс - подарок останется в очереди** |
| Session expired | Удалите `sessions/*.session` и запустите `auth_session.py` |

### ⚠️ Недостаточно Stars?

Если worker выдает ошибку "Insufficient Stars balance":

1. **Админ получит уведомление** в боте
2. **Подарок останется в очереди** (не будет удален!)
3. **Пополните баланс Stars** в Telegram
4. **Worker автоматически продолжит** доставку при следующей попытке

Эта ошибка НЕ исчерпывает попытки доставки - подарок будет ждать пополнения баланса.

## 📖 Полная документация

Смотрите [GIFT_DELIVERY_SETUP.md](GIFT_DELIVERY_SETUP.md)

---

**Готово! 🎉** Система работает автоматически после первой настройки.
