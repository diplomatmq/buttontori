import asyncio
import ast
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyParameters
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
from database.db import Database
from config import (
    BOT_TOKEN,
    ADMIN_ID,
    DATABASE_URL,
    LOG_LEVEL,
    GAME_ROWS,
    GAME_COLS,
    ALLOWED_CHAT_ID,
    TELEGRAM_GIFT_MAPPING,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database(DATABASE_URL)

PRIZES = {
    "bear": "5280598054901145762",
    "hearts": "5283228279988309088",
    "rose": "5280947338821524402",
    "gift": "5280615440928758599",
    "cake": "5280659198055572187",
    "bouquet": "5280774333243873175",
    "rocket": "5283080528818360566",
    "ring": "5280651583078556009",
    "diamond": "5471952986970267163",
    "cup": "5280769763398671636",
    "nft": "5359622339296256165"
}

PRIZE_VALUES = {
    "bear": 15,
    "hearts": 15,
    "rose": 25,
    "gift": 25,
    "cake": 50,
    "rocket": 50,
    "ring": 100,
    "cup": 100,
    "diamond": 100,
    "nft": 0
}

PRIZE_GROUPS = (
    (1, ("nft",)),
    (1, ("rocket",)),
    (5, ("rose",)),
    (6, ("gift",)),
    (6, ("bear",)),
    (6, ("hearts",)),
)

PRIZE_NAMES = {
    "bear": "Медведь", "hearts": "Сердце", "rose": "Роза", "gift": "Подарок",
    "cake": "Тортик", "rocket": "Ракета", "ring": "Кольцо", "diamond": "Бриллиант",
    "cup": "Кубок", "nft": "NFT"
}
PRIZE_STAGES = (15, 25, 50, 100)
BAR_DICE_VALUES = (1,)
UPGRADE_GROUPS = (
    ("gift", "rose"),
    ("rocket",),
    ("diamond",),
    ("nft",),
)


def generate_game_field(rows=GAME_ROWS, cols=GAME_COLS):
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
    builder = InlineKeyboardBuilder()
    
    for idx in range(rows * cols):
        row = idx // cols
        col = idx % cols
        
        if idx in opened:
            prize = field[idx]
            button = InlineKeyboardButton(
                text="✨",
                callback_data=f"opened_{game_id}_{idx}",
                custom_emoji_id=PRIZES[prize]
            )
        else:
            button = InlineKeyboardButton(
                text="🎁",
                callback_data=f"open_{game_id}_{idx}"
            )
        
        builder.add(button)
    
    builder.adjust(cols)
    return builder.as_markup()


def create_casino_keyboard(game_id: str, field: list, selected_idx: int = -1, user_id: int = 0, rows=5, cols=5):
    builder = InlineKeyboardBuilder()
    
    for idx in range(rows * cols):
        prize = field[idx]
        
        if selected_idx == -1:
            button = InlineKeyboardButton(
                text=" ",
                callback_data=f"casino_{game_id}_{idx}_{user_id}",
                icon_custom_emoji_id="5458713011545986880"
            )
        elif idx == selected_idx:
            button = InlineKeyboardButton(
                text=" ",
                callback_data=f"casino_done_{game_id}",
                icon_custom_emoji_id=PRIZES[prize],
                style="success"
            )
        else:
            button = InlineKeyboardButton(
                text=" ",
                callback_data=f"casino_done_{game_id}",
                icon_custom_emoji_id=PRIZES[prize],
                style="danger"
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
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    await db.add_user(user_id, username)
    
    await message.answer(f"👋 Привет, {username}!")


@dp.message(Command("play"))
async def cmd_play(message: Message):
    user_id = message.from_user.id
    
    field = generate_game_field()
    
    game_id = await db.create_game(user_id, field)
    
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
    data_parts = callback.data.split("_")
    game_id = int(data_parts[1])
    cell_idx = int(data_parts[2])
    user_id = callback.from_user.id
    
    game = await db.get_game(game_id)
    
    if not game:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    if game['user_id'] != user_id:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return
    
    if game['is_finished']:
        await callback.answer("❌ Игра уже завершена!", show_alert=True)
        return
    
    field = eval(game['field'])
    opened = eval(game['opened_cells'])
    
    if cell_idx in opened:
        await callback.answer("❌ Эта ячейка уже открыта!", show_alert=True)
        return
    
    opened.append(cell_idx)
    prize = field[cell_idx]
    prize_value = PRIZE_VALUES[prize]
    
    await db.update_game(game_id, opened)
    
    keyboard = create_game_keyboard(game_id, field, opened)
    
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
    
    prize_text = f"🎉 Ты выиграл: {prize_names[prize]}"
    
    if prize == "nft":
        prize_text += f"\n\n🔥🔥🔥 РЕДКИЙ NFT! Стоимость: {prize_value} 💰"
    elif prize in ["ring", "diamond", "cup"]:
        prize_text += f"\n\n✨ РЕДКИЙ ПРИЗ! Стоимость: {prize_value} 💰"
    else:
        prize_text += f"\n💰 Стоимость: {prize_value}"
    
    await callback.answer(prize_text, show_alert=True)
    
    await callback.message.edit_text(
        "🎮 <b>ДЖЕКПОТ</b> 🎮\n\n"
        f"🎉 Ты открыл: {prize_names[prize]}\n"
        f"💰 Стоимость: {prize_value}\n\n"
        "Открой еще ячейки или используй /play для новой игры!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await db.record_prize(user_id, prize, prize_value)


@dp.callback_query(F.data.startswith("opened_"))
async def process_opened_cell(callback: CallbackQuery):
    await callback.answer("ℹ️ Эта ячейка уже открыта!", show_alert=False)


@dp.message(F.dice)
async def handle_dice(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID:
        return
    
    if message.dice.emoji != "🎰":
        return
    
    if message.forward_from or message.forward_from_chat or message.forward_date:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    dice_value = message.dice.value
    
    logger.info(f"Пользователь {username} (ID: {user_id}) отправил казино, выпало: {dice_value}")
    
    if dice_value == 64:
        field = generate_game_field(rows=5, cols=5)
        game_id = f"{user_id}_{message.message_id}"
        
        await db.create_casino_game(
            game_id=game_id,
            user_id=user_id,
            source_message_id=message.message_id,
            field=field,
            selected=-1,
            finished=False,
        )
        
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
        
        await db.create_casino_game(
            game_id=game_id,
            user_id=user_id,
            source_message_id=message.message_id,
            finished=False,
            bar_bear_index=bear_index,
            bar_selected=-1,
        )
        
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
    
    game = await db.get_casino_game(game_id)
    
    if not game:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    if callback.from_user.id != game["user_id"]:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return

    if game["finished"] and action not in ("claim", "upgrade", "pick", "revealed"):
        await callback.answer("ℹ️ Игра уже завершена!", show_alert=False)
        return

    username_mention = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name

    if action == "barpick":
        if game["bar_revealed"]:
            await callback.answer("Ячейка уже выбрана", show_alert=True)
            return

        bar_revealed = {
            index: "4976609924776724046" if index == game["bar_bear_index"] else "5893163582194978381"
            for index in range(3)
        }
        
        await db.update_casino_game(game_id, bar_selected=cell_idx, bar_revealed=bar_revealed)
        
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=create_bar_keyboard(
                game_id,
                selected=cell_idx,
                revealed=bar_revealed,
            )
        )

        if cell_idx != game["bar_bear_index"]:
            await db.update_casino_game(game_id, finished=True)
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

        await db.update_casino_game(game_id, finished=True)
        
        prize_type = "bear"
        prize_value = PRIZE_VALUES.get(prize_type, 15)
        gift_id = TELEGRAM_GIFT_MAPPING.get(prize_type)
        
        await db.record_prize(game["user_id"], prize_type, prize_value, gift_id)
        
        success_text = (
            '<tg-emoji emoji-id="5159316330310010269">🎉</tg-emoji> Поздравляю! Вы выиграли '
            '<tg-emoji emoji-id="5206502842478638898">🧸</tg-emoji>\n\n'
            'Твой приз уже в пути <tg-emoji emoji-id="5159332079955084776">🎁</tg-emoji>\n'
            + ('<tg-emoji emoji-id="5382360493161725288">✨</tg-emoji>' * 8) + '\n'
            '<tg-emoji emoji-id="5460980668378931880">⭐</tg-emoji> '
            '<a href="https://t.me/toriwmarketbot">Купить звезды</a>'
        )
        
        await callback.message.answer(
            success_text,
            reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        
        if ADMIN_ID:
            admin_text = (
                f"🎁 {username_mention} забрал Медведя\n"
                f"Профиль: <a href=\"tg://user?id={game['user_id']}\">открыть</a>\n"
                f"Сообщение: {message_link(callback.message)}\n"
            )
            if gift_id:
                admin_text += f"\n✅ Подарок добавлен в очередь доставки"
            else:
                admin_text += f"\n⚠️ Gift ID не настроен"
            
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        return

    async def claim_prize(prize: str, preserve_game_message: bool = False):
        await db.update_casino_game(game_id, finished=True)
        
        gift_id = TELEGRAM_GIFT_MAPPING.get(prize)
        
        if prize != "nft":
            await db.record_prize(game["user_id"], prize, PRIZE_VALUES[prize], gift_id)
        else:
            await db.update_user_stats(game["user_id"], PRIZE_VALUES.get(prize, 0))
        
        prize_name = PRIZE_NAMES[prize]
        claim_text = (
            f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} забрал {prize_name}\n\n'
        )
        
        if prize == "nft":
            claim_text += (
                f'<tg-emoji emoji-id="5159316330310010269">🔥</tg-emoji> '
                f'<b>NFT будет выдан администратором вручную!</b>'
            )
        elif gift_id:
            claim_text += (
                f'<tg-emoji emoji-id="5251324597193709038">✅</tg-emoji> Администратор уведомлен.\n'
                f'<tg-emoji emoji-id="5159332079955084776">🎁</tg-emoji> '
                f'<b>Подарок будет доставлен автоматически!</b>'
            )
        else:
            claim_text += (
                f'<tg-emoji emoji-id="5251324597193709038">✅</tg-emoji> Администратор уведомлен.\n'
                f'<tg-emoji emoji-id="5280659198055572187">⚠️</tg-emoji> '
                f'<i>Gift ID для {prize_name} не настроен - выдача вручную</i>'
            )
        
        if preserve_game_message:
            await callback.message.answer(
                claim_text,
                reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(claim_text, parse_mode="HTML")
        
        if ADMIN_ID:
            admin_text = (
                f"🎁 <b>{username_mention} забрал: {prize_name}</b>\n\n"
                f"👤 Профиль: <a href=\"tg://user?id={game['user_id']}\">открыть</a>\n"
                f"💬 Сообщение: {message_link(callback.message)}\n"
            )
            
            if prize == "nft":
                admin_text += f"\n🔥 <b>NFT - требуется ручная выдача!</b>"
            elif gift_id:
                admin_text += f"\n✅ Подарок добавлен в очередь автовыдачи (gift_id={gift_id})"
            else:
                admin_text += f"\n⚠️ Gift ID не настроен - необходима ручная выдача"
            
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    if action == "claim":
        if game.get("prize_claimed"):
            await callback.answer("✅ Приз уже забран!", show_alert=True)
            return
        
        await db.update_casino_game(game_id, prize_claimed=True)
        await callback.answer()
        await claim_prize(game["current_prize"])
        return

    if action == "upgrade":
        if game.get("upgrade_started"):
            await callback.answer("⚠️ Апгрейд уже начат!", show_alert=True)
            return
        
        stage = game["stage"]
        
        if stage == 3:
            upgrade_slots = 5
        else:
            upgrade_slots = 3
            
        upgrade_target = next_prize(stage)
        upgrade_winner = random.randrange(upgrade_slots)
        
        await db.update_casino_game(
            game_id,
            upgrade_started=True,
            upgrade_slots=upgrade_slots,
            upgrade_target=upgrade_target,
            upgrade_winner=upgrade_winner,
            upgrade_revealed={}
        )
        
        await callback.answer()
        target_name = PRIZE_NAMES[upgrade_target]
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f'<tg-emoji emoji-id="5427256683955007067">🎯</tg-emoji> <b>Улучшение приза!</b>\n\n'
            f'<blockquote><b>Приз на кону: {target_name}</b></blockquote>\n'
            f'<tg-emoji emoji-id="5159316330310010269">🔮</tg-emoji> <b>Выбери 1 из {upgrade_slots} ячеек</b>',
            reply_markup=create_upgrade_keyboard(game_id, upgrade_slots),
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
        upgrade_revealed = {
            index: (PRIZES[target] if index == game["upgrade_winner"] else "5893163582194978381")
            for index in range(game["upgrade_slots"])
        }
        
        await db.update_casino_game(game_id, upgrade_revealed=upgrade_revealed)
        
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=create_upgrade_keyboard(
                game_id,
                game["upgrade_slots"],
                upgrade_revealed,
                selected=cell_idx,
            )
        )
        
        if cell_idx != game["upgrade_winner"]:
            await db.update_casino_game(game_id, finished=True)
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

        new_stage = game["stage"] + 1
        
        await db.update_casino_game(
            game_id,
            current_prize=target,
            stage=new_stage,
            upgrade_started=False
        )
        
        if target == "nft":
            await callback.message.answer(
                f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> Поздравляю, {username_mention}! Ты выиграл NFT!',
                reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
                parse_mode="HTML",
            )
            await claim_prize(target, preserve_game_message=True)
            return

        await callback.message.answer(
            f'<tg-emoji emoji-id="5348432081179406377">🎉</tg-emoji> {username_mention} получил {PRIZE_NAMES[target]}\n\n'
            f'<tg-emoji emoji-id="5280598054901145762">✨</tg-emoji> Хочешь улучшить его?',
            reply_markup=create_action_keyboard(game_id),
            reply_parameters=ReplyParameters(message_id=game["source_message_id"]),
            parse_mode="HTML",
        )
        return

    prize = game["field"][cell_idx]
    stage = PRIZE_STAGES.index(PRIZE_VALUES[prize])
    
    await db.update_casino_game(
        game_id,
        finished=False,
        selected=cell_idx,
        current_prize=prize,
        stage=stage
    )
    
    if prize == "nft":
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=create_casino_keyboard(
                game_id, game["field"], selected_idx=cell_idx, user_id=game["user_id"]
            )
        )
        await claim_prize(prize, preserve_game_message=True)
        return
        
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
    user_id = message.from_user.id
    stats = await db.get_user_stats(user_id)
    
    if not stats:
        await message.answer("📊 У тебя пока нет статистики. Сыграй с помощью /play")
        return
    
    delivery_stats = await db.get_delivery_stats(user_id)
    
    stats_text = (
        f"📊 <b>Твоя статистика:</b>\n\n"
        f"🎮 Игр сыграно: {stats['games_played']}\n"
        f"💎 Всего выиграно: {stats['total_winnings']} 💰\n"
        f"📅 В боте с: {stats['created_at'][:10]}\n\n"
        f"<b>🎁 Доставка подарков:</b>\n"
        f"✅ Доставлено: {delivery_stats['delivered']}\n"
        f"⏳ В обработке: {delivery_stats['pending']}\n"
    )
    
    if delivery_stats['failed'] > 0:
        stats_text += f"❌ Ошибки доставки: {delivery_stats['failed']}\n"
    
    await message.answer(stats_text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🎮 <b>Как играть:</b>\n\n"
        "1️⃣ Отправь эмодзи 🎰 казино в чат\n"
        "2️⃣ Если выпадет 777 (64) - получишь поле с призами\n"
        "3️⃣ Выбери любую ячейку - приз гарантирован!\n"
        "4️⃣ Можешь забрать приз или рискнуть и улучшить его\n\n"
        "💎 <b>Призы:</b>\n"
        "• Медведь, Сердце - 15 ⭐\n"
        "• Роза, Подарок - 25 ⭐\n"
        "• Ракета, Тортик - 50 ⭐\n"
        "• Бриллиант, Кольцо, Кубок - 100 ⭐\n"
        "• NFT - эксклюзив! 🔥\n\n"
        "📊 /stats - Твоя статистика\n"
        "🎮 /play - Игра с выбором ячеек"
    )
    await message.answer(help_text, parse_mode="HTML")


async def main():
    await db.init_db()
    logger.info("База данных инициализирована")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
