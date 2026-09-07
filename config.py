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
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

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
