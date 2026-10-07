import asyncio
import logging
from telethon.errors import FloodWaitError, UserIdInvalidError, UserNotMutualContactError

from config import (
    DATABASE_URL,
    TELEGRAM_GIFT_MAPPING,
    LOG_LEVEL,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELETHON_SESSION,
    MAX_DELIVERY_ATTEMPTS,
    WORKER_POLL_INTERVAL,
    BOT_TOKEN,
    ADMIN_ID,
)
from database.db import Database
from gift_worker.telegram import GiftTelegram, InsufficientStarsError

# Импортируем aiogram Bot для уведомлений админа
try:
    from aiogram import Bot
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    Bot = None

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_delivery(db: Database, telegram: GiftTelegram, delivery_id: int, bot: Bot = None) -> None:
    """
    Обрабатывает одну доставку подарка из очереди.
    
    Args:
        db: Экземпляр базы данных
        telegram: Клиент Telegram
        delivery_id: ID доставки из очереди
    """
    # Захватываем доставку (claim) с блокировкой для предотвращения дублирования
    delivery = await db.claim_delivery(delivery_id)
    if not delivery:
        # Доставка уже обрабатывается другим воркером или завершена
        return
    
    logger.info(
        f"📦 Обработка delivery_id={delivery.delivery_id}, "
        f"user_id={delivery.user_id}, prize={delivery.prize_type}, "
        f"attempt={delivery.attempts}/{MAX_DELIVERY_ATTEMPTS}"
    )
    
    try:
        # Проверяем наличие gift_id в маппинге
        gift_id = delivery.gift_id or TELEGRAM_GIFT_MAPPING.get(delivery.prize_type)
        
        if not gift_id:
            error_msg = (
                f"Gift ID not configured for prize type '{delivery.prize_type}'. "
                f"Add GIFT_ID_{delivery.prize_type.upper()} to .env"
            )
            logger.error(f"❌ {error_msg}")
            await db.mark_delivery_failed(delivery.delivery_id, error_msg)
            return
        
        # Проверяем существование пользователя перед отправкой
        user_exists = await telegram.check_user_exists(delivery.user_id)
        if not user_exists:
            error_msg = f"User {delivery.user_id} not found or not accessible"
            logger.error(f"❌ {error_msg}")
            await db.mark_delivery_failed(delivery.delivery_id, error_msg)
            return
        
        # Отправляем подарок
        await telegram.send_gift(delivery.user_id, gift_id)
        
        # Помечаем как успешно доставленный
        await db.mark_delivered(delivery.delivery_id)
        logger.info(
            f"✅ Delivery {delivery.delivery_id} успешно доставлен! "
            f"User {delivery.user_id} получил {delivery.prize_type}"
        )
        
        # Уведомляем админа об успешной доставке
        if bot and ADMIN_ID:
            try:
                prize_name = delivery.prize_type.title()
                await bot.send_message(
                    ADMIN_ID,
                    f"✅ <b>Подарок успешно доставлен!</b>\n\n"
                    f"👤 User ID: {delivery.user_id}\n"
                    f"🎁 Приз: {prize_name}\n"
                    f"💎 Gift ID: {gift_id}\n"
                    f"🆔 Delivery ID: {delivery.delivery_id}",
                    parse_mode="HTML"
                )
            except Exception as notify_error:
                logger.error(f"Не удалось уведомить админа об успехе: {notify_error}")
        
    except FloodWaitError as e:
        # Telegram просит подождать - это временная ошибка
        error_msg = f"FloodWait: need to wait {e.seconds} seconds"
        logger.warning(f"⏳ Delivery {delivery.delivery_id}: {error_msg}")
        await db.mark_delivery_failed(delivery.delivery_id, error_msg)
        
        # Можно добавить задержку перед следующей попыткой
        if e.seconds < 300:  # Если меньше 5 минут - ждем
            logger.info(f"⏰ Ожидание {e.seconds} секунд...")
            await asyncio.sleep(e.seconds)
    
    except InsufficientStarsError as e:
        # Недостаточно Stars на балансе - оставляем в очереди
        error_msg = f"Insufficient Stars balance: {str(e)}"
        logger.warning(f"💰 Delivery {delivery.delivery_id}: {error_msg}")
        logger.warning(f"⏸️  Подарок останется в очереди до пополнения баланса Stars")
        
        # НЕ увеличиваем счетчик попыток для этой ошибки (increment_attempts=False)
        # Просто откатываем статус обратно в pending
        await db.mark_delivery_failed(delivery.delivery_id, error_msg, increment_attempts=False)
        
        # Уведомляем админа о недостатке Stars
        if bot and ADMIN_ID:
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ <b>Недостаточно Stars на балансе!</b>\n\n"
                    f"Подарок для user_id={delivery.user_id}\n"
                    f"Приз: {delivery.prize_type}\n"
                    f"Gift ID: {delivery.gift_id or 'не указан'}\n\n"
                    f"💰 Пополните баланс Stars для продолжения доставки.\n"
                    f"Подарок останется в очереди.",
                    parse_mode="HTML"
                )
            except Exception as notify_error:
                logger.error(f"Не удалось уведомить админа: {notify_error}")
        
        # Ждем дольше перед следующей проверкой (30 секунд)
        await asyncio.sleep(30)
    
    except (UserIdInvalidError, UserNotMutualContactError) as e:
        # Пользователь недоступен - это постоянная ошибка
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"❌ Delivery {delivery.delivery_id}: {error_msg}")
        # Помечаем как failed сразу (будет failed после всех attempts)
        await db.mark_delivery_failed(delivery.delivery_id, error_msg)
    
    except Exception as e:
        # Неожиданная ошибка - логируем и повторяем попытку
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.exception(f"❌ Delivery {delivery.delivery_id} failed: {error_msg}")
        await db.mark_delivery_failed(delivery.delivery_id, error_msg)
        
        # Уведомляем админа об ошибке
        if bot and ADMIN_ID:
            try:
                prize_name = delivery.prize_type.title()
                await bot.send_message(
                    ADMIN_ID,
                    f"❌ <b>Ошибка доставки подарка!</b>\n\n"
                    f"👤 User ID: {delivery.user_id}\n"
                    f"🎁 Приз: {prize_name}\n"
                    f"💎 Gift ID: {delivery.gift_id or 'не указан'}\n"
                    f"🆔 Delivery ID: {delivery.delivery_id}\n"
                    f"🔄 Попытка: {delivery.attempts}/{MAX_DELIVERY_ATTEMPTS}\n\n"
                    f"⚠️ Ошибка: {error_msg[:200]}",
                    parse_mode="HTML"
                )
            except Exception as notify_error:
                logger.error(f"Не удалось уведомить админа об ошибке: {notify_error}")


async def main() -> None:
    """Основной цикл обработки очереди доставок"""
    
    logger.info("=" * 60)
    logger.info("🎁 GIFT DELIVERY WORKER STARTED")
    logger.info("=" * 60)
    
    # Проверяем конфигурацию
    if not TELEGRAM_API_ID or TELEGRAM_API_ID == 0:
        logger.error("❌ TELEGRAM_API_ID не указан в .env!")
        logger.error("📝 Получите API_ID на https://my.telegram.org")
        return
    
    if not TELEGRAM_API_HASH:
        logger.error("❌ TELEGRAM_API_HASH не указан в .env!")
        return
    
    logger.info(f"📁 Session file: {TELETHON_SESSION}.session")
    logger.info(f"⚙️  Max attempts: {MAX_DELIVERY_ATTEMPTS}")
    logger.info(f"⏱️  Poll interval: {WORKER_POLL_INTERVAL}s")
    logger.info(f"🔧 Configured prizes: {', '.join(TELEGRAM_GIFT_MAPPING.keys())}")
    
    # Инициализируем БД
    db = Database(DATABASE_URL)
    await db.init_db()
    logger.info("✅ Database connected")
    
    # Инициализируем Bot для уведомлений админа (опционально)
    bot = None
    if AIOGRAM_AVAILABLE and BOT_TOKEN and ADMIN_ID:
        try:
            bot = Bot(token=BOT_TOKEN)
            logger.info("✅ Admin notification bot initialized")
        except Exception as e:
            logger.warning(f"⚠️  Could not initialize admin bot: {e}")
    
    # Инициализируем Telegram клиент
    telegram = GiftTelegram(TELEGRAM_API_ID, TELEGRAM_API_HASH, TELETHON_SESSION)
    
    try:
        await telegram.connect()
        logger.info("✅ Telegram connected")
        
        # Опционально: показываем доступные подарки при старте
        try:
            gifts = await telegram.get_available_gifts()
            if gifts:
                logger.info(f"📦 Available gifts: {len(gifts)}")
                for gift in gifts[:5]:  # Показываем первые 5
                    logger.debug(f"   Gift ID: {gift['id']}, Stars: {gift['stars']}")
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch available gifts: {e}")
        
        logger.info("🚀 Worker ready! Waiting for deliveries...")
        logger.info("=" * 60 + "\n")
        
        # Основной цикл обработки
        cycle_count = 0
        while True:
            cycle_count += 1
            
            # Получаем список pending доставок
            delivery_ids = await db.pending_delivery_ids()
            
            if delivery_ids:
                logger.info(f"📋 Cycle #{cycle_count}: Found {len(delivery_ids)} pending deliveries")
                
                # Обрабатываем каждую доставку
                for delivery_id in delivery_ids:
                    await process_delivery(db, telegram, delivery_id, bot)
                    
                    # Небольшая задержка между доставками чтобы не флудить
                    await asyncio.sleep(0.5)
            else:
                # Нет доставок - просто логируем раз в 10 циклов
                if cycle_count % 10 == 0:
                    logger.debug(f"💤 Cycle #{cycle_count}: No pending deliveries")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(WORKER_POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Received interrupt signal")
    except Exception as e:
        logger.exception(f"❌ Fatal error in main loop: {e}")
    finally:
        await telegram.close()
        if bot:
            await bot.session.close()
        logger.info("👋 Gift delivery worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete")
