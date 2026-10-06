"""
Тестовый скрипт для получения списка доступных Telegram Star Gifts.
Используется для получения актуальных Gift IDs для .env конфигурации.

Использование:
    python test_gifts.py
"""
import asyncio
import os
from dotenv import load_dotenv
from gift_worker.telegram import GiftTelegram

# Загружаем .env
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_PATH = os.getenv("TELETHON_SESSION", "sessions/owner")


async def main():
    """Получить и вывести список доступных подарков"""
    
    print("=" * 80)
    print("🎁 ПОЛУЧЕНИЕ СПИСКА ДОСТУПНЫХ TELEGRAM STAR GIFTS")
    print("=" * 80)
    
    if not API_ID or API_ID == 0:
        print("\n❌ ОШИБКА: TELEGRAM_API_ID не указан в .env файле!")
        return
    
    if not API_HASH:
        print("\n❌ ОШИБКА: TELEGRAM_API_HASH не указан в .env файле!")
        return
    
    print(f"\n📁 Session: {SESSION_PATH}.session")
    print("🔌 Подключение к Telegram...\n")
    
    # Создаем клиент
    telegram = GiftTelegram(API_ID, API_HASH, SESSION_PATH)
    
    try:
        await telegram.connect()
        print("✅ Подключено!\n")
        
        # Получаем список доступных подарков
        print("📦 Загрузка списка подарков...\n")
        gifts = await telegram.get_available_gifts()
        
        if not gifts:
            print("⚠️  Список подарков пуст или недоступен")
            return
        
        print(f"Найдено подарков: {len(gifts)}\n")
        print("=" * 80)
        print("ID подарка".ljust(25) + "Stars".ljust(15) + "Availability")
        print("=" * 80)
        
        # Выводим подарки
        for gift in gifts:
            gift_id = str(gift['id']).ljust(25)
            stars = str(gift['stars']).ljust(15)
            
            if gift['availability_total']:
                availability = f"{gift['availability_remains']}/{gift['availability_total']}"
            else:
                availability = "Unlimited"
            
            print(f"{gift_id}{stars}{availability}")
        
        print("=" * 80)
        print("\n💡 ИНСТРУКЦИЯ:")
        print("\n1. Выберите подарки которые хотите выдавать игрокам")
        print("2. Скопируйте их ID")
        print("3. Добавьте в .env файл:")
        print("\n   Например:")
        print("   GIFT_ID_BEAR=5170233102089322756")
        print("   GIFT_ID_HEARTS=5170145012310081615")
        print("   GIFT_ID_ROSE=5168103777563050263")
        print("\n4. Перезапустите gift worker")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\n💡 Возможные причины:")
        print("1. Session файл не существует - запустите: python auth_session.py")
        print("2. Session истек - удалите .session файл и авторизуйтесь снова")
        print("3. Проблемы с подключением к Telegram")
        
    finally:
        await telegram.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")
