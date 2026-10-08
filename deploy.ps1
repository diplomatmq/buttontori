# Скрипт автоматического деплоя на сервер

$SERVER = "root@142.248.83.52"
$PATH = "/opt/bots/buttontori"

Write-Host "🚀 Начинаем деплой..." -ForegroundColor Green

Write-Host "`n📤 Загружаем файлы на сервер..." -ForegroundColor Cyan
scp bot.py "${SERVER}:${PATH}/"
scp database/models.py "${SERVER}:${PATH}/database/"
scp database/db.py "${SERVER}:${PATH}/database/"

Write-Host "`n🔄 Перезапускаем контейнеры..." -ForegroundColor Cyan
ssh $SERVER "cd $PATH && docker-compose down && docker-compose up -d --build"

Write-Host "`n⏳ Ожидаем запуска..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "`n📋 Логи бота:" -ForegroundColor Yellow
ssh $SERVER "cd $PATH && docker-compose logs bot --tail 20"

Write-Host "`n📋 Логи worker:" -ForegroundColor Yellow
ssh $SERVER "cd $PATH && docker-compose logs worker --tail 20"

Write-Host "`n✅ Деплой завершен!" -ForegroundColor Green
Write-Host "`nДля просмотра логов в реальном времени используйте:" -ForegroundColor Gray
Write-Host "ssh $SERVER 'cd $PATH && docker-compose logs -f bot worker'" -ForegroundColor White
