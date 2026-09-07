import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
from database import Database
from config import BOT_TOKEN, ADMIN_ID, DB_PATH, LOG_LEVEL, GAME_ROWS, GAME_COLS, ALLOWED_CHAT_ID

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database(db_path=DB_PATH)

# Эмодзи для призов (кастомные Telegram эмодзи)
PRIZES = {
    "bear": "5280598054901145762",        # Медведь - самый частый
    "hearts": "5283228279988309088",     # Сердечко - самый частый
    "rose": "5280947338821524402",       # Роза - менее частый
    "gift": "5280615440928758599",       # Подарок - менее частый
    "cake": "5280659198055572187",       # Тортик - еще менее частый
    "bouquet": "5280774333243873175",    # Букет - еще менее частый
    "rocket": "5283080528818360566",     # Ракета - еще менее частый
    "ring": "5280651583078556009",       # Кольцо - редкий
    "diamond": "5280922999241859582",    # Бриллиант - редкий
    "cup": "5280769763398671636",        # Кубок - редкий
    "nft": "5359622339296256165"         # NFT - самый редкий
}

# Стоимость призов
PRIZE_VALUES = {
    "bear": 15,
    "hearts": 15,
    "rose": 25,
    "gift": 30,
    "cake": 40,
    "bouquet": 50,
    "rocket": 75,
    "ring": 100,
    "diamond": 150,
    "cup": 200,
    "nft": 1000
}

# Вероятности выпадения (вес)
PRIZE_WEIGHTS = {
    "bear": 25,      # Самый частый
    "hearts": 25,    # Самый частый
    "rose": 15,      # Менее частый
    "gift": 15,      # Менее частый
    "cake": 8,       # Еще менее частый
    "bouquet": 8,    # Еще менее частый
    "rocket": 8,     # Еще менее частый
    "ring": 3,       # Редкий
    "diamond": 3,    # Редкий
    "cup": 3,        # Редкий
    "nft": 1         # Самый редкий
}

# Хранилище для игр казино (в памяти)
casino_games = {}


def generate_game_field(rows=GAME_ROWS, cols=GAME_COLS):
    """Генерирует игровое поле с призами с учетом вероятностей"""
    total_cells = rows * cols
    
    # Создаем список призов без NFT
    prize_keys_without_nft = [k for k in PRIZE_WEIGHTS.keys() if k != "nft"]
    weights_without_nft = [PRIZE_WEIGHTS[k] for k in prize_keys_without_nft]
    
    # Генерируем поле без NFT (всего ячеек - 1)
    field = []
    for _ in range(total_cells - 1):
        prize = random.choices(prize_keys_without_nft, weights=weights_without_nft, k=1)[0]
        field.append(prize)
    
    # Добавляем РОВНО ОДИН NFT в случайную позицию
    field.append("nft")
    
    # Перемешиваем
    random.shuffle(field)
    
    return field


def create_game_keyboard(game_id: int, field: list, opened: list, rows=GAME_ROWS, cols=GAME_COLS):
    """Создает клавиатуру с кнопками (обычная игра)"""
    builder = InlineKeyboardBuilder()
    
    for idx in range(rows * cols):
        row = idx // cols
        col = idx % cols
        
        if idx in opened:
            # Открытая кнопка - показываем кастомное эмодзи
            prize = field[idx]
            button = InlineKeyboardButton(
                text="✨",  # Fallback текст
                callback_data=f"opened_{game_id}_{idx}",
                custom_emoji_id=PRIZES[prize]
            )
        else:
            # Закрытая кнопка - показываем placeholder
            button = InlineKeyboardButton(
                text="🎁",
                callback_data=f"open_{game_id}_{idx}"
            )
        
        builder.add(button)
    
    builder.adjust(cols)
    return builder.as_markup()


def create_casino_keyboard(game_id: str, field: list, selected_idx: int = -1, user_id: int = 0, rows=5, cols=5):
    """Создает инлайн-клавиатуру для казино игры (5x5) с кастомными эмодзи"""
    builder = InlineKeyboardBuilder()
    
    for idx in range(rows * cols):
        prize = field[idx]
        
        if selected_idx == -1:
            # Игра еще не началась - все кнопки закрыты
            button = InlineKeyboardButton(
                text=" ",  # Пустой текст, будет только эмодзи
                callback_data=f"casino_{game_id}_{idx}_{user_id}",
                icon_custom_emoji_id="5458713011545986880"  # Закрытый подарок
            )
        elif idx == selected_idx:
            # Выбранная кнопка - ЗЕЛЕНАЯ (success)
            button = InlineKeyboardButton(
                text=" ",
                callback_data=f"casino_done_{game_id}",
                icon_custom_emoji_id=PRIZES[prize],
                style="success"  # Зеленый фон
            )
        else:
            # Все остальные неоткрытые - КРАСНЫЕ (danger)
            button = InlineKeyboardButton(
                text=" ",
                callback_data=f"casino_done_{game_id}",
                icon_custom_emoji_id=PRIZES[prize],
                style="danger"  # Красный фон
            )
        
        builder.add(button)
    
    builder.adjust(cols)
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Добавляем пользователя в БД
    db.add_user(user_id, username)
    
    await message.answer(
        f"👋 Привет, {username}!\n\n"
        "🎮 Добро пожаловать в игру Gift Caps!\n\n"
        "🎰 Отправь эмодзи казино и если выпадет 777 - получи приз!\n\n"
        "Используй команды:\n"
        "/play - Начать новую игру\n"
        "/stats - Твоя статистика\n"
        "/help - Помощь"
    )


@dp.message(Command("play"))
async def cmd_play(message: Message):
    """Создает новую игру"""
    user_id = message.from_user.id
    
    # Генерируем игровое поле
    field = generate_game_field()
    
    # Создаем игру в БД
    game_id = db.create_game(user_id, field)
    
    # Отправляем сообщение с клавиатурой
    keyboard = create_game_keyboard(game_id, field, [])
    
    await message.answer(
        "🎮 <b>ДЖЕКПОТ</b> 🎮\n\n"
        f"🎯 Перед тобой {len(field)} ячеек.\n"
        "Выбери одну и гарантированно забери свои призы:\n"
        "💎 обычные до 100 💰 или редкие NFT 🚀\n\n"
        "⬇️ Нажми на любую кнопку:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("open_"))
async def process_open_cell(callback: CallbackQuery):
    """Обработка открытия ячейки"""
    data_parts = callback.data.split("_")
    game_id = int(data_parts[1])
    cell_idx = int(data_parts[2])
    user_id = callback.from_user.id
    
    # Получаем игру из БД
    game = db.get_game(game_id)
    
    if not game:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    if game['user_id'] != user_id:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return
    
    if game['is_finished']:
        await callback.answer("❌ Игра уже завершена!", show_alert=True)
        return
    
    # Открываем ячейку
    field = eval(game['field'])
    opened = eval(game['opened_cells'])
    
    if cell_idx in opened:
        await callback.answer("❌ Эта ячейка уже открыта!", show_alert=True)
        return
    
    # Добавляем ячейку в открытые
    opened.append(cell_idx)
    prize = field[cell_idx]
    prize_value = PRIZE_VALUES[prize]
    
    # Обновляем игру в БД
    db.update_game(game_id, opened)
    
    # Обновляем клавиатуру
    keyboard = create_game_keyboard(game_id, field, opened)
    
    # Названия призов для сообщения
    prize_names = {
        "bear": "Медведь",
        "hearts": "Сердечко",
        "rose": "Роза",
        "gift": "Подарок",
        "cake": "Тортик",
        "bouquet": "Букет",
        "rocket": "Ракета",
        "ring": "Кольцо",
        "diamond": "Бриллиант",
        "cup": "Кубок",
        "nft": "NFT"
    }
    
    # Формируем сообщение о выигрыше
    prize_text = f"🎉 Ты выиграл: {prize_names[prize]}"
    
    if prize == "nft":
        prize_text += f"\n\n🔥🔥🔥 РЕДКИЙ NFT! Стоимость: {prize_value} 💰"
    elif prize in ["ring", "diamond", "cup"]:
        prize_text += f"\n\n✨ РЕДКИЙ ПРИЗ! Стоимость: {prize_value} 💰"
    else:
        prize_text += f"\n💰 Стоимость: {prize_value}"
    
    # Показываем уведомление
    await callback.answer(prize_text, show_alert=True)
    
    # Названия призов
    prize_names = {
        "bear": "Медведь",
        "hearts": "Сердечко",
        "rose": "Роза",
        "gift": "Подарок",
        "cake": "Тортик",
        "bouquet": "Букет",
        "rocket": "Ракета",
        "ring": "Кольцо",
        "diamond": "Бриллиант",
        "cup": "Кубок",
        "nft": "NFT"
    }
    
    # Обновляем сообщение
    await callback.message.edit_text(
        "🎮 <b>ДЖЕКПОТ</b> 🎮\n\n"
        f"🎉 Ты открыл: {prize_names[prize]}\n"
        f"💰 Стоимость: {prize_value}\n\n"
        "Открой еще ячейки или используй /play для новой игры!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Обновляем статистику пользователя
    db.update_user_stats(user_id, prize_value)


@dp.callback_query(F.data.startswith("opened_"))
async def process_opened_cell(callback: CallbackQuery):
    """Обработка нажатия на уже открытую ячейку"""
    await callback.answer("ℹ️ Эта ячейка уже открыта!", show_alert=False)


@dp.message(F.dice)
async def handle_dice(message: Message):
    """Обработка отправки эмодзи казино"""
    # Проверяем что это разрешенный чат
    if message.chat.id != ALLOWED_CHAT_ID:
        return
    
    # Проверяем что это именно казино (slot machine)
    if message.dice.emoji != "🎰":
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    dice_value = message.dice.value
    
    logger.info(f"Пользователь {username} (ID: {user_id}) отправил казино, выпало: {dice_value}")
    
    # Проверяем джекпот (777 = значение 64)
    if dice_value == 64:
        # Генерируем поле 5x5
        field = generate_game_field(rows=5, cols=5)
        
        # Создаем уникальный ID игры
        game_id = f"{user_id}_{message.message_id}"
        
        # Сохраняем игру в памяти
        casino_games[game_id] = {
            "user_id": user_id,
            "field": field,
            "selected": -1,
            "finished": False
        }
        
        # Создаем клавиатуру
        keyboard = create_casino_keyboard(game_id, field, user_id=user_id)
        
        # Получаем username с @ если есть, иначе имя
        username_mention = f"@{message.from_user.username}" if message.from_user.username else username
        
        # Отправляем с кастомными эмодзи через HTML тег <tg-emoji>
        await message.reply(
            f'<tg-emoji emoji-id="5373346752671804066">🎉</tg-emoji> Поздравляю, {username_mention}! '
            f'Перед тобой 25 ячеек, открыв любую ты гарантировано забираешь приз '
            f'<tg-emoji emoji-id="5190581652115449511">💎</tg-emoji>',
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@dp.callback_query(F.data.startswith("casino_"))
async def process_casino_cell(callback: CallbackQuery):
    """Обработка выбора ячейки в казино игре"""
    # Проверяем что это разрешенный чат
    if callback.message.chat.id != ALLOWED_CHAT_ID:
        await callback.answer("❌ Бот работает только в определенном чате!", show_alert=True)
        return
    
    data_parts = callback.data.split("_")
    
    # Если игра завершена
    if data_parts[1] == "done":
        await callback.answer("ℹ️ Игра завершена!", show_alert=False)
        return
    
    # Парсим: casino_{user_id}_{message_id}_{cell_idx}_{expected_user_id}
    game_id = f"{data_parts[1]}_{data_parts[2]}"  # user_id_message_id
    cell_idx = int(data_parts[3])
    expected_user_id = int(data_parts[4])
    
    # Защита от чужих нажатий
    if callback.from_user.id != expected_user_id:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return
    
    # Проверяем существование игры
    if game_id not in casino_games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = casino_games[game_id]
    
    # Проверяем что игра еще не завершена
    if game["finished"]:
        await callback.answer("ℹ️ Игра уже завершена!", show_alert=False)
        return
    
    # Помечаем игру как завершенную
    game["finished"] = True
    game["selected"] = cell_idx
    
    # Получаем выбранный приз
    prize = game["field"][cell_idx]
    prize_value = PRIZE_VALUES[prize]
    
    # Обновляем клавиатуру - показываем все ячейки
    keyboard = create_casino_keyboard(game_id, game["field"], selected_idx=cell_idx, user_id=expected_user_id)
    
    # Обновляем статистику
    db.update_user_stats(expected_user_id, prize_value)
    
    # Названия призов
    prize_names = {
        "bear": "Медведь",
        "hearts": "Сердечко",
        "rose": "Роза",
        "gift": "Подарок",
        "cake": "Тортик",
        "bouquet": "Букет",
        "rocket": "Ракета",
        "ring": "Кольцо",
        "diamond": "Бриллиант",
        "cup": "Кубок",
        "nft": "NFT"
    }
    
    # Формируем сообщение (без алерта)
    await callback.answer()
    
    # Обновляем сообщение
    username_mention = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name
    
    await callback.message.edit_text(
        f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} забрал {prize_names[prize]}\n'
        f'<tg-emoji emoji-id="5348267231744652656">✅</tg-emoji> Подарок уже в пути!\n'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>'
        f'<tg-emoji emoji-id="5332760930927262659">🎰</tg-emoji>\n'
        f'<tg-emoji emoji-id="5235695112419303615">🎁</tg-emoji> <a href="https://t.me/lud777ka">Лудка на NFT</a>\n'
        f'<tg-emoji emoji-id="5460980668378931880">⭐</tg-emoji> <a href="https://t.me/torionnft">Дешевые звезды</a>',
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику пользователя"""
    user_id = message.from_user.id
    stats = db.get_user_stats(user_id)
    
    if not stats:
        await message.answer("📊 У тебя пока нет статистики. Сыграй с помощью /play")
        return
    
    await message.answer(
        f"📊 <b>Твоя статистика:</b>\n\n"
        f"🎮 Игр сыграно: {stats['games_played']}\n"
        f"💎 Всего выиграно: {stats['total_winnings']} 💰\n"
        f"📅 В боте с: {stats['created_at'][:10]}",
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Показывает справку"""
    await message.answer(
        "ℹ️ <b>Как играть:</b>\n\n"
        "<b>Режим 1: Казино 🎰</b>\n"
        "1. Отправь эмодзи казино 🎰\n"
        "2. Если выпадет 777 - поздравляем!\n"
        "3. Выбери одну ячейку из 25 (5x5)\n"
        "4. Твой выбор подсветится 🟢, остальные откроются\n\n"
        "<b>Режим 2: Обычная игра</b>\n"
        "1. Используй /play для начала игры\n"
        "2. Нажми на любую кнопку 🎁\n"
        "3. Открывай сколько хочешь ячеек\n\n"
        "<b>Призы (от частых к редким):</b>\n"
        "🧸 Медведь - 15 💰\n"
        "💕 Сердечко - 15 💰\n"
        "🌹 Роза - 25 💰\n"
        "🎁 Подарок - 30 💰\n"
        "🍰 Тортик - 40 💰\n"
        "💐 Букет - 50 💰\n"
        "🚀 Ракета - 75 💰\n"
        "💍 Кольцо - 100 💰 (редкий!)\n"
        "💎 Бриллиант - 150 💰 (редкий!)\n"
        "🏆 Кубок - 200 💰 (редкий!)\n"
        "🖼 NFT - 1000 💰 (ОЧЕНЬ редкий!)",
        parse_mode="HTML"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель (только для администратора)"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к админ-панели!")
        return
    
    # Получаем статистику
    top_users = db.get_top_users(10)
    
    stats_text = "👑 <b>Топ-10 игроков:</b>\n\n"
    for idx, user in enumerate(top_users, 1):
        username = user['username'] or 'Без имени'
        stats_text += f"{idx}. {username}\n"
        stats_text += f"   💰 Выиграно: {user['total_winnings']}\n"
        stats_text += f"   🎮 Игр: {user['games_played']}\n\n"
    
    await message.answer(stats_text, parse_mode="HTML")


async def main():
    """Запуск бота"""
    try:
        # Проверяем настройки
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ Не указан BOT_TOKEN в .env файле!")
            return
        
        if ADMIN_ID == 0:
            logger.warning("⚠️ Не указан ADMIN_ID в .env файле!")
        
        if ALLOWED_CHAT_ID == 0:
            logger.warning("⚠️ Не указан ALLOWED_CHAT_ID в .env файле!")
        else:
            logger.info(f"✅ Бот будет работать только в чате: {ALLOWED_CHAT_ID}")
        
        # Создаем директорию для БД если нужно
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"✅ Создана директория для БД: {db_dir}")
        
        # Инициализируем БД
        db.init_db()
        logger.info("✅ База данных инициализирована")
        
        # Запускаем бота
        logger.info("🚀 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
