#!/bin/bash

SERVER="root@142.248.83.52"
PATH="/opt/bots/buttontori"

echo "🚀 Начинаем деплой..."

echo ""
echo "📤 Загружаем файлы на сервер..."
scp bot.py ${SERVER}:${PATH}/
scp database/models.py ${SERVER}:${PATH}/database/
scp database/db.py ${SERVER}:${PATH}/database/

echo ""
echo "🔄 Перезапускаем контейнеры..."
ssh $SERVER "cd $PATH && docker-compose down && docker-compose up -d --build"

echo ""
echo "⏳ Ожидаем запуска..."
sleep 5

echo ""
echo "📋 Логи бота:"
ssh $SERVER "cd $PATH && docker-compose logs bot --tail 20"

echo ""
echo "📋 Логи worker:"
ssh $SERVER "cd $PATH && docker-compose logs worker --tail 20"

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "Для просмотра логов в реальном времени используйте:"
echo "ssh $SERVER 'cd $PATH && docker-compose logs -f bot worker'"
