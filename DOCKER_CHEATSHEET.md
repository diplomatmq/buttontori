# 🐳 Docker Команды - Шпаргалка

## Запуск и остановка

```bash
# Запуск (с пересборкой)
docker-compose up -d --build

# Запуск (без пересборки)
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Перезапуск worker
docker-compose restart worker
```

## Логи

```bash
# Все логи в реальном времени
docker-compose logs -f

# Логи только worker
docker-compose logs -f worker

# Логи только bot
docker-compose logs -f bot

# Последние 50 строк
docker-compose logs --tail=50 worker
```

## Статус

```bash
# Список контейнеров
docker-compose ps

# Детальная информация
docker ps

# Использование ресурсов
docker stats
```

## Отладка

```bash
# Зайти внутрь контейнера
docker exec -it gift_caps_worker bash

# Проверить session файл
docker exec gift_caps_worker ls -la sessions/

# Запустить команду в контейнере
docker exec gift_caps_worker python test_gifts.py
```

## Очистка

```bash
# Остановить и удалить контейнеры
docker-compose down

# Удалить volumes (БД будет очищена!)
docker-compose down -v

# Удалить неиспользуемые образы
docker image prune -a

# Полная очистка Docker
docker system prune -a --volumes
```

## Быстрый workflow

```bash
# 1. Обновление кода
git pull
docker-compose down
docker-compose up -d --build
docker-compose logs -f

# 2. Только перезапуск worker
docker-compose restart worker
docker-compose logs -f worker

# 3. Проверка проблем
docker-compose logs --tail=100 worker
docker-compose ps
```
