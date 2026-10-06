"""
Скрипт для первичной авторизации в Telegram через MTProto.
Создает session файл для автоматической работы gift worker.

ВАЖНО: Запускайте этот скрипт только один раз для авторизации!
После создания session файла, он будет использоваться автоматически.
"""
import asyncio
import os
from pathlib import Path
from telethon import TelegramClient
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_PATH = os.getenv("TELETHON_SESSION", "sessions/owner")


async def main():
    """Авторизация в Telegram и создание session файла"""
    
    print("=" * 60)
    print("🔐 АВТОРИЗАЦИЯ В TELEGRAM")
    print("=" * 60)
    
    # Проверяем настройки
    if not API_ID or API_ID == 0:
        print("❌ ОШИБКА: TELEGRAM_API_ID не указан в .env файле!")
        print("\n📝 Инструкция:")
        print("1. Откройте https://my.telegram.org")
        print("2. Войдите в свой аккаунт Telegram")
        print("3. Перейдите в 'API development tools'")
        print("4. Создайте приложение и скопируйте API_ID и API_HASH")
        print("5. Добавьте их в .env файл:")
        print("   TELEGRAM_API_ID=your_api_id")
        print("   TELEGRAM_API_HASH=your_api_hash")
        return
    
    if not API_HASH:
        print("❌ ОШИБКА: TELEGRAM_API_HASH не указан в .env файле!")
        return
    
    # Создаем директорию для сессий
    session_dir = Path(SESSION_PATH).parent
    session_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 Директория сессий: {session_dir}")
    print(f"📄 Файл сессии: {SESSION_PATH}.session\n")
    
    # Создаем клиент
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    
    print("🔌 Подключение к Telegram...\n")
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Вы уже авторизованы как: {me.first_name} (@{me.username})")
            print(f"   User ID: {me.id}")
            print(f"\n✨ Session файл готов к использованию!")
        else:
            print("📱 Для авторизации потребуется:")
            print("   1. Номер телефона (в международном формате)")
            print("   2. Код из Telegram")
            print("   3. Пароль 2FA (если включен)\n")
            
            # Запрашиваем номер телефона
            phone = input("Введите номер телефона (например: +79991234567): ")
            
            await client.send_code_request(phone)
            print("\n✉️  Код отправлен в Telegram!")
            
            code = input("Введите код из Telegram: ")
            
            try:
                await client.sign_in(phone, code)
                
            except Exception as e:
                if "password" in str(e).lower() or "2fa" in str(e).lower():
                    print("\n🔒 Требуется пароль двухфакторной аутентификации")
                    password = input("Введите пароль 2FA: ")
                    await client.sign_in(password=password)
                else:
                    raise
            
            me = await client.get_me()
            print(f"\n✅ Успешная авторизация!")
            print(f"   Имя: {me.first_name}")
            print(f"   Username: @{me.username}")
            print(f"   User ID: {me.id}")
            print(f"\n✨ Session файл создан: {SESSION_PATH}.session")
        
        print("\n" + "=" * 60)
        print("🎉 ГОТОВО!")
        print("=" * 60)
        print("\n📋 Следующие шаги:")
        print("1. Убедитесь что .env содержит все настройки")
        print("2. Запустите gift worker: python -m gift_worker.worker")
        print("3. Запустите бота: python bot.py")
        print("\n⚠️  ВАЖНО: Не удаляйте .session файл!")
        print("   Он нужен для автоматической работы без повторной авторизации.\n")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\n💡 Попробуйте:")
        print("1. Проверить правильность API_ID и API_HASH")
        print("2. Убедиться что номер телефона в международном формате")
        print("3. Проверить код из Telegram (он действителен несколько минут)")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
