"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ID разрешенного чата
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

# Настройки игры
GAME_ROWS = int(os.getenv("GAME_ROWS", "5"))  # Количество рядов
GAME_COLS = int(os.getenv("GAME_COLS", "5"))  # Количество колонок

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bot:bot@localhost:5432/bot")

# Настройки MTProto для выдачи подарков
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELETHON_SESSION = os.getenv("TELETHON_SESSION", "sessions/owner")

# Маппинг призов игры на Telegram Star Gifts
# Эти ID получаются через getAvailableGifts API
# Владелец должен указать актуальные gift_id из своего Telegram
TELEGRAM_GIFT_MAPPING = {
    "bear": os.getenv("GIFT_ID_BEAR", ""),        # Медведь - обычный подарок
    "hearts": os.getenv("GIFT_ID_HEARTS", ""),    # Сердце - обычный подарок
    "rose": os.getenv("GIFT_ID_ROSE", ""),        # Роза - обычный подарок
    "gift": os.getenv("GIFT_ID_GIFT", ""),        # Подарок - обычный подарок
    "cake": os.getenv("GIFT_ID_CAKE", ""),        # Тортик - обычный подарок
    "bouquet": os.getenv("GIFT_ID_BOUQUET", ""),  # Букет - обычный подарок
    "rocket": os.getenv("GIFT_ID_ROCKET", ""),    # Ракета - обычный подарок
    "ring": os.getenv("GIFT_ID_RING", ""),        # Кольцо - редкий подарок
    "diamond": os.getenv("GIFT_ID_DIAMOND", ""),  # Бриллиант - редкий подарок
    "cup": os.getenv("GIFT_ID_CUP", ""),          # Кубок - редкий подарок
}

# Максимальное количество попыток выдачи подарка
MAX_DELIVERY_ATTEMPTS = int(os.getenv("MAX_DELIVERY_ATTEMPTS", "3"))

# Интервал между проверками очереди (секунды)
WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))

# Таймаут для захвата задачи в обработку (минуты)
DELIVERY_CLAIM_TIMEOUT = int(os.getenv("DELIVERY_CLAIM_TIMEOUT", "5"))

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Эмодзи для призов
PRIZES = {
    "diamond": "💎",
    "rose": "🌹",
    "rocket": "🚀",
    "bear": "🧸",
    "hearts": "💕",
    "bottle": "🍾",
    "gift": "🎁",
    "nft": "NFT"
}

# Стоимость призов
PRIZE_VALUES = {
    "diamond": 100,
    "rose": 10,
    "rocket": 50,
    "bear": 25,
    "hearts": 15,
    "bottle": 30,
    "gift": 75,
    "nft": 500
}

# Вероятности появления призов (0-100)
PRIZE_WEIGHTS = {
    "diamond": 5,
    "rose": 20,
    "rocket": 10,
    "bear": 15,
    "hearts": 20,
    "bottle": 10,
    "gift": 8,
    "nft": 2
}
