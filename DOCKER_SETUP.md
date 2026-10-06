# 🐳 Docker Setup - Gift Delivery System

## Быстрый старт с Docker

### 1. Подготовка на локальной машине

**⚠️ ВАЖНО: Авторизацию нужно делать ДО загрузки на сервер!**

```bash
# 1. Клонируйте репозиторий
git clone <your-repo>
cd buttonTori

# 2. Создайте .env файл
cp .env.example .env
# Заполните все необходимые параметры

# 3. Установите зависимости локально
pip install -r requirements.txt

# 4. АВТОРИЗАЦИЯ в Telegram (создание session файла)
python auth_session.py
```

После авторизации будет создан файл `sessions/owner.session` - **это ключевой файл!**

### 2. Получение Gift IDs (опционально)

```bash
python test_gifts.py
```

Скопируйте Gift IDs в `.env` файл.

### 3. Загрузка на сервер

Загрузите весь проект на сервер, **включая session файл**:

```bash
# Пример с scp
scp -r buttonTori/ user@server:/path/to/project/

# Или через git (но НЕ коммитьте .env и sessions!)
```

**📁 Что нужно загрузить:**
- ✅ Весь код проекта
- ✅ `.env` файл (с вашими настройками)
- ✅ `sessions/owner.session` файл (ВАЖНО!)
- ❌ НЕ загружайте `venv/`, `__pycache__/`, `.git/` (если через scp)

### 4. Запуск на сервере

```bash
# Подключитесь к серверу
ssh user@server
cd /path/to/project/buttonTori

# Запустите Docker Compose
docker-compose up -d --build
```

### 5. Проверка работы

```bash
# Просмотр логов
docker-compose logs -f

# Или отдельно для каждого сервиса
docker-compose logs -f bot      # Логи бота
docker-compose logs -f worker   # Логи gift worker
docker-compose logs -f postgres # Логи БД
```

## Управление контейнерами

### Основные команды

```bash
# Запуск (пересборка образов)
docker-compose up -d --build

# Запуск (без пересборки)
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Перезапуск конкретного сервиса
docker-compose restart bot
docker-compose restart worker

# Остановка с удалением volumes (ОСТОРОЖНО - удалит БД!)
docker-compose down -v
```

### Логи

```bash
# Все логи в реальном времени
docker-compose logs -f

# Последние 100 строк логов bot
docker-compose logs --tail=100 bot

# Последние 100 строк логов worker
docker-compose logs --tail=100 worker

# Логи без follow (просто вывод)
docker-compose logs bot
docker-compose logs worker
```

### Статус контейнеров

```bash
# Список запущенных контейнеров
docker-compose ps

# Подробная информация
docker ps
```

## Структура Docker Compose

```yaml
services:
  postgres:   # База данных PostgreSQL
  bot:        # Telegram бот (основной)
  worker:     # Gift delivery worker
```

### Volumes

- `postgres_data` - данные PostgreSQL (персистентные)
- `./sessions:/app/sessions` - session файлы Telethon (монтируются с хоста)

**⚠️ ВАЖНО:** Sessions должны быть на хосте, чтобы сохраниться при пересборке контейнеров!

## Обновление кода

```bash
# 1. Остановите контейнеры
docker-compose down

# 2. Обновите код (git pull или загрузите новые файлы)
git pull

# 3. Пересоберите и запустите
docker-compose up -d --build

# 4. Проверьте логи
docker-compose logs -f
```

## Бэкап session файла

**🔒 КРИТИЧЕСКИ ВАЖНО сохранить session файл!**

```bash
# Создайте бэкап
cp sessions/owner.session sessions/owner.session.backup

# Или скачайте на локальную машину
scp user@server:/path/to/buttonTori/sessions/owner.session ./backup/
```

Если потеряете session файл - придется авторизовываться заново через `auth_session.py`.

## Переменные окружения в Docker

Docker Compose автоматически использует `.env` файл из корня проекта.

**Обязательные переменные:**
```env
BOT_TOKEN=...
ADMIN_ID=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELETHON_SESSION=sessions/owner  # Путь внутри контейнера
```

`DATABASE_URL` переопределяется в docker-compose.yml для использования контейнера postgres.

## Решение проблем

### Worker не может авторизоваться

**Ошибка:** "Telethon session is not authorized"

**Причина:** Session файл не найден или не скопирован в контейнер

**Решение:**
1. Убедитесь что `sessions/owner.session` существует на хосте
2. Проверьте что он примонтирован: `docker-compose config | grep sessions`
3. Пересоберите контейнеры: `docker-compose up -d --build`

### Подарки не доставляются

```bash
# 1. Проверьте что worker запущен
docker-compose ps

# 2. Проверьте логи worker
docker-compose logs -f worker

# 3. Проверьте что session файл примонтирован
docker exec gift_caps_worker ls -la sessions/

# 4. Проверьте Gift IDs в .env
cat .env | grep GIFT_ID
```

### База данных не подключается

**Ошибка:** "could not connect to server"

**Решение:**
```bash
# Проверьте что postgres запущен
docker-compose ps postgres

# Перезапустите postgres
docker-compose restart postgres

# Проверьте логи
docker-compose logs postgres
```

### Контейнер постоянно перезапускается

```bash
# Проверьте логи для выявления ошибки
docker-compose logs --tail=50 worker

# Запустите контейнер в интерактивном режиме для отладки
docker-compose run --rm worker python -m gift_worker.worker
```

## Мониторинг

### Использование ресурсов

```bash
# Статистика в реальном времени
docker stats

# Использование дискового пространства
docker system df
```

### Health check (опционально)

Можно добавить в docker-compose.yml:

```yaml
services:
  bot:
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Продакшн советы

### 1. Используйте Docker secrets для чувствительных данных

Вместо .env файла:
```yaml
secrets:
  bot_token:
    file: ./secrets/bot_token.txt
```

### 2. Настройте автоматический рестарт

Уже настроено: `restart: unless-stopped`

### 3. Ограничьте ресурсы

```yaml
services:
  worker:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### 4. Используйте внешнюю БД

Для продакшна лучше использовать внешнюю managed PostgreSQL:

```yaml
services:
  bot:
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@external-db:5432/bot
  # Удалите сервис postgres
```

## Полный пример запуска с нуля

```bash
# ============ НА ЛОКАЛЬНОЙ МАШИНЕ ============

# 1. Клонируем и настраиваем
git clone <repo>
cd buttonTori
cp .env.example .env
nano .env  # Заполняем настройки

# 2. Авторизация (создание session)
pip install -r requirements.txt
python auth_session.py

# 3. Получаем Gift IDs
python test_gifts.py
nano .env  # Добавляем Gift IDs

# 4. Загружаем на сервер
scp -r buttonTori/ user@server:/opt/

# ============ НА СЕРВЕРЕ ============

ssh user@server
cd /opt/buttonTori

# 5. Запускаем через Docker
docker-compose up -d --build

# 6. Проверяем
docker-compose ps
docker-compose logs -f

# 7. Тестируем бота в Telegram
# Отправьте /start боту
```

---

**🎉 Готово!** Бот и worker работают в Docker на сервере.

Для просмотра логов: `docker-compose logs -f`
Для остановки: `docker-compose down`
