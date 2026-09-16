import asyncio
import ast
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyParameters
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
    "gift": 25,
    "cake": 50,
    "rocket": 50,
    "ring": 100,
    "cup": 100,
    "nft": 0
}

# Точный состав поля 5x5. Порядок кнопок каждый раз случайно перемешивается.
PRIZE_GROUPS = (
    (1, ("nft",)),
    (1, ("cup",)),
    (1, ("ring",)),
    (2, ("rocket",)),
    (2, ("cake",)),
    (4, ("rose",)),
    (4, ("gift",)),
    (5, ("bear",)),
    (5, ("hearts",)),
)

PRIZE_NAMES = {
    "bear": "Медведь", "hearts": "Сердце", "rose": "Роза", "gift": "Подарок",
    "cake": "Тортик", "rocket": "Ракета", "ring": "Кольцо", "cup": "Кубок", "nft": "NFT"
}
PRIZE_STAGES = (15, 25, 50, 100)
BAR_DICE_VALUES = (1,)
UPGRADE_GROUPS = (
    ("rose", "gift"),
    ("cake", "rocket"),
    ("cup", "ring"),
    ("nft",),
)

# Хранилище для игр казино (в памяти)
casino_games = {}


def generate_game_field(rows=GAME_ROWS, cols=GAME_COLS):
    """Генерирует случайно перемешанное поле 5x5 с фиксированным составом."""
    total_cells = rows * cols

    expected_cells = sum(count for count, _ in PRIZE_GROUPS)
    if total_cells != expected_cells:
        raise ValueError(f"Игровое поле должно содержать {expected_cells} ячеек")

    field = []
    for count, prize_options in PRIZE_GROUPS:
        for _ in range(count):
            field.append(random.choice(prize_options))

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


def create_action_keyboard(game_id: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Забрать", callback_data=f"casino_claim_{game_id}", icon_custom_emoji_id="5465262274031659421"),
        InlineKeyboardButton(text="Апгрейд", callback_data=f"casino_upgrade_{game_id}", icon_custom_emoji_id="5463122435425448565"),
    )
    return builder.as_markup()


def create_upgrade_keyboard(game_id: str, slots: int = 3, revealed: dict | None = None, selected: int = -1):
    builder = InlineKeyboardBuilder()
    revealed = revealed or {}
    for index in range(slots):
        if index in revealed:
            icon = revealed[index]
            callback_data = f"casino_revealed_{game_id}"
            style = "success" if index == selected else "danger"
        else:
            icon = "5359628193336669414"
            callback_data = f"casino_pick_{game_id}_{index}"
            style = None
        builder.add(InlineKeyboardButton(
            text=" ",
            callback_data=callback_data,
            icon_custom_emoji_id=icon,
            style=style,
        ))
    builder.adjust(slots)
    return builder.as_markup()


def create_bar_keyboard(game_id: str, selected: int = -1, revealed: dict | None = None):
    builder = InlineKeyboardBuilder()
    revealed = revealed or {}
    for index in range(3):
        if index in revealed:
            icon = revealed[index]
            callback_data = f"casino_revealed_{game_id}"
            style = "success" if index == selected else "danger"
        else:
            icon = "5359628193336669414"
            callback_data = f"casino_barpick_{game_id}_{index}"
            style = None
        builder.add(InlineKeyboardButton(
            text=" ",
            callback_data=callback_data,
            icon_custom_emoji_id=icon,
            style=style,
        ))
    builder.adjust(3)
    return builder.as_markup()


def next_prize(stage: int):
    if stage >= len(UPGRADE_GROUPS):
        return "nft"
    return random.choice(UPGRADE_GROUPS[stage])


def message_link(message: Message):
    if message.chat.username:
        return f"https://t.me/{message.chat.username}/{message.message_id}"
    return f"https://t.me/c/{str(message.chat.id).replace('-', '')[3:]}/{message.message_id}"


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Добавляем пользователя в БД
    db.add_user(user_id, username)
    
    await message.answer(
        f"👋 Привет, {username}!\n\n"
        "🎮 Добро пожаловать в игру!\n\n"
        "🎰 Отправь эмодзи казино и если выпадет 777 - получи приз!\n\n"
        "Используй команды:\n"
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
    
    # Игнорируем пересланные сообщения
    if message.forward_from or message.forward_from_chat or message.forward_date:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    dice_value = message.dice.value
    
    logger.info(f"Пользователь {username} (ID: {user_id}) отправил казино, выпало: {dice_value}")
    
    # Значение 64 - отдельный джекпот 777.
    if dice_value == 64:
        field = generate_game_field(rows=5, cols=5)
        game_id = f"{user_id}_{message.message_id}"
        casino_games[game_id] = {
            "user_id": user_id,
            "source_message_id": message.message_id,
            "field": field,
            "selected": -1,
            "finished": False,
            "current_prize": None,
            "stage": None,
            "upgrade_target": None,
            "upgrade_winner": None,
            "upgrade_slots": 0,
            "upgrade_revealed": {}
        }
        keyboard = create_casino_keyboard(game_id, field, user_id=user_id)
        username_mention = f"@{message.from_user.username}" if message.from_user.username else username
        await message.reply(
            f'<tg-emoji emoji-id="5373346752671804066">🎉</tg-emoji> Поздравляю, {username_mention}! '
            f'Перед тобой 25 ячеек, открыв любую ты гарантировано забираешь приз '
            f'<tg-emoji emoji-id="5190581652115449511">💎</tg-emoji>',
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif dice_value in BAR_DICE_VALUES:
        game_id = f"bar_{user_id}_{message.message_id}"
        bear_index = random.randrange(3)
        casino_games[game_id] = {
            "user_id": user_id,
            "source_message_id": message.message_id,
            "finished": False,
            "bar_bear_index": bear_index,
            "bar_selected": -1,
            "bar_revealed": {},
        }
        username_mention = f"@{message.from_user.username}" if message.from_user.username else username
        await message.reply(
            f'<tg-emoji emoji-id="4976672970601662075">🎰</tg-emoji> {username_mention} поймал три BAR!\n\n'
            f'<blockquote><tg-emoji emoji-id="4976609924776724046">🎁</tg-emoji> '
            f'Выпал шанс на фриспины <tg-emoji emoji-id="4976609924776724046">🎁</tg-emoji></blockquote>\n\n'
            f'В одной из ячеек спрятан мишка <tg-emoji emoji-id="5235695112419303615">🧸</tg-emoji>\n'
            '<b>3 ячейки в одной из которых мишка</b>',
            reply_markup=create_bar_keyboard(game_id),
            parse_mode="HTML",
        )


@dp.callback_query(F.data.startswith("casino_"))
async def process_casino_cell(callback: CallbackQuery):
    """Обработка выбора ячейки в казино игре"""
    # Проверяем что это разрешенный чат
    if callback.message.chat.id != ALLOWED_CHAT_ID:
        await callback.answer("❌ Бот работает только в определенном чате!", show_alert=True)
        return
    
    data = callback.data
    action, payload = data.split("_", 2)[1:]

    if action == "done":
        await callback.answer("ℹ️ Эта ячейка уже открыта!", show_alert=False)
        return

    if action in {"claim", "upgrade", "revealed"}:
        game_id = payload
    elif action == "pick":
        game_id, index_text = payload.rsplit("_", 1)
        cell_idx = int(index_text)
    elif action == "barpick":
        game_id, index_text = payload.rsplit("_", 1)
        cell_idx = int(index_text)
    else:
        game_id = f"{data.split('_')[1]}_{data.split('_')[2]}"
        cell_idx = int(data.split("_")[3])
        expected_user_id = int(data.split("_")[4])
        if callback.from_user.id != expected_user_id:
            await callback.answer("❌ Это не твоя игра!", show_alert=True)
            return
    
    # Проверяем существование игры
    if game_id not in casino_games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = casino_games[game_id]
    
    if callback.from_user.id != game["user_id"]:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return

    if game["finished"]:
        await callback.answer("ℹ️ Игра уже завершена!", show_alert=False)
        return

    username_mention = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name

    if action == "barpick":
        if game["bar_revealed"]:
            await callback.answer("Ячейка уже выбрана", show_alert=True)
            return

        game["bar_selected"] = cell_idx
        game["bar_revealed"] = {
            index: "4976609924776724046" if index == game["bar_bear_index"] else "5893163582194978381"
            for index in range(3)
        }
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=create_bar_keyboard(
                game_id,
                selected=cell_idx,
                revealed=game["bar_revealed"],
            )
        )

        if cell_idx != game["bar_bear_index"]:
            game["finished"] = True
            await callback.message.answer(
                'В этот раз не повезло <tg-emoji emoji-id="5157000668627600960">😔</tg-emoji>\n\n'
                'Повезет в следующий <tg-emoji emoji-id="5258090944506387855">🍀</tg-emoji>\n'
                + ('<tg-emoji emoji-id="5382360493161725288">✨</tg-emoji>' * 8) + '\n'
                '<tg-emoji emoji-id="5460980668378931880">⭐</tg-emoji> '
                '<a href="https://t.me/toriwmarketbot">Купить звезды</a>',
                reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return

        game["finished"] = True
        await callback.message.answer(
            '<tg-emoji emoji-id="5159316330310010269">🎉</tg-emoji> Поздравляю! Вы выиграли '
            '<tg-emoji emoji-id="5206502842478638898">🧸</tg-emoji>\n\n'
            'Твой приз уже в пути <tg-emoji emoji-id="5159332079955084776">🎁</tg-emoji>\n'
            + ('<tg-emoji emoji-id="5382360493161725288">✨</tg-emoji>' * 8) + '\n'
            '<tg-emoji emoji-id="5460980668378931880">⭐</tg-emoji> '
            '<a href="https://t.me/toriwmarketbot">Купить звезды</a>',
            reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🎁 {username_mention} забрал Медведя\n"
                f"Профиль: <a href=\"tg://user?id={game['user_id']}\">открыть</a>\n"
                f"Сообщение: {message_link(callback.message)}",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        return

    async def claim_prize(prize: str):
        game["finished"] = True
        db.update_user_stats(game["user_id"], PRIZE_VALUES[prize])
        prize_name = PRIZE_NAMES[prize]
        claim_text = (
            f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} забрал {prize_name}\n\n'
            f'<tg-emoji emoji-id="5251324597193709038">✅</tg-emoji> Администратор уведомлен.'
        )
        await callback.message.edit_text(claim_text, parse_mode="HTML")
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🎁 {username_mention} забрал: {prize_name}\n"
                f"Профиль: <a href=\"tg://user?id={game['user_id']}\">открыть</a>\n"
                f"Сообщение: {message_link(callback.message)}",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    if action == "claim":
        await callback.answer()
        await claim_prize(game["current_prize"])
        return

    if action == "upgrade":
        stage = game["stage"]
        game["upgrade_slots"] = 5 if stage == 3 else 3
        game["upgrade_target"] = next_prize(stage)
        game["upgrade_winner"] = random.randrange(game["upgrade_slots"])
        game["upgrade_revealed"] = {}
        await callback.answer()
        target_name = PRIZE_NAMES[game["upgrade_target"]]
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f'<tg-emoji emoji-id="5427256683955007067">🎯</tg-emoji> <b>Улучшение приза!</b>\n\n'
            f'<blockquote><b>Приз на кону: {target_name}</b></blockquote>\n'
            f'<tg-emoji emoji-id="5159316330310010269">🔮</tg-emoji> <b>Выбери 1 из {game["upgrade_slots"]} ячеек</b>',
            reply_markup=create_upgrade_keyboard(game_id, game["upgrade_slots"]),
            reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
            parse_mode="HTML",
        )
        return

    if action == "revealed":
        await callback.answer("Эта ячейка уже открыта")
        return

    if action == "pick":
        if game["upgrade_revealed"]:
            await callback.answer("Ячейка уже выбрана", show_alert=True)
            return
        target = game["upgrade_target"]
        game["upgrade_revealed"] = {
            index: (PRIZES[target] if index == game["upgrade_winner"] else "5893163582194978381")
            for index in range(game["upgrade_slots"])
        }
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=create_upgrade_keyboard(
                game_id,
                game["upgrade_slots"],
                game["upgrade_revealed"],
                selected=cell_idx,
            )
        )
        if cell_idx != game["upgrade_winner"]:
            game["finished"] = True
            await callback.message.answer(
                '<tg-emoji emoji-id="5157000668627600960">😔</tg-emoji> В этот раз не повезло\n\n'
                '<tg-emoji emoji-id="5258090944506387855">🍀</tg-emoji> Повезет в следующий раз\n\n'
                '<tg-emoji emoji-id="5460980668378931880">⭐</tg-emoji> '
                '<a href="https://t.me/toriwmarketbot">Купить звезды</a>',
                reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return

        game["current_prize"] = target
        game["stage"] += 1
        if target == "nft":
            await callback.message.answer(
                f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> Поздравляю, {username_mention}! Ты выиграл NFT!',
                reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
                parse_mode="HTML",
            )
            await claim_prize(target)
            return

        await callback.message.answer(
            f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} получил {PRIZE_NAMES[target]}\n\n'
            f'<tg-emoji emoji-id="5280598054901145762">✨</tg-emoji> Хочешь улучшить его?',
            reply_markup=create_action_keyboard(game_id),
            reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
            parse_mode="HTML",
        )
        return

    # Первый выбор после выпадения 777: приз еще не считается забранным.
    game["finished"] = False
    game["selected"] = cell_idx
    prize = game["field"][cell_idx]
    game["current_prize"] = prize
    if prize == "nft":
        await claim_prize(prize)
        return
    game["stage"] = PRIZE_STAGES.index(PRIZE_VALUES[prize])
    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=create_casino_keyboard(game_id, game["field"], selected_idx=cell_idx, user_id=game["user_id"])
    )
    await callback.message.answer(
        f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} получил {PRIZE_NAMES[prize]}\n\n'
        f'<tg-emoji emoji-id="5280598054901145762">✨</tg-emoji> Хочешь улучшить его?',
        reply_markup=create_action_keyboard(game_id),
        reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
        parse_mode="HTML",
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
        "💕 Сердце - 15 💰\n"
        "🌹 Роза - 25 💰\n"
        "🎁 Подарок - 25 💰\n"
        "🍰 Тортик - 50 💰\n"
        "🚀 Ракета - 50 💰\n"
        "💍 Кольцо - 100 💰 (редкий!)\n"
        "🏆 Кубок - 100 💰 (редкий!)\n"
        "🖼 NFT - финальный приз",
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
