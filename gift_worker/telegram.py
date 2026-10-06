import logging
from telethon import TelegramClient, functions
from telethon.tl import types
from telethon.errors import (
    UserIdInvalidError,
    UserNotMutualContactError,
    FloodWaitError,
    AuthKeyUnregisteredError,
    SessionPasswordNeededError,
)

# Исключение для недостатка Stars
class InsufficientStarsError(Exception):
    """Недостаточно Stars на балансе для покупки подарка"""
    pass

logger = logging.getLogger(__name__)


class GiftTelegram:
    """Класс для отправки Telegram Star Gifts через MTProto API"""

    def __init__(self, api_id: int, api_hash: str, session: str):
        """
        Args:
            api_id: Telegram API ID (получить на https://my.telegram.org)
            api_hash: Telegram API Hash
            session: Путь к файлу сессии (например: "sessions/owner")
        """
        self.client = TelegramClient(session, api_id, api_hash)
        self.is_connected = False

    async def connect(self) -> None:
        """Подключение к Telegram и проверка авторизации"""
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            logger.error("❌ Сессия не авторизована! Необходима первичная авторизация.")
            logger.error("Запустите скрипт auth_session.py для авторизации")
            raise RuntimeError(
                "Telethon session is not authorized. "
                "Run 'python auth_session.py' to authenticate first."
            )
        
        # Получаем информацию о текущем пользователе
        me = await self.client.get_me()
        logger.info(f"✅ Подключен как: {me.first_name} (@{me.username}, ID: {me.id})")
        self.is_connected = True

    async def close(self) -> None:
        """Закрытие соединения"""
        if self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            logger.info("🔌 Соединение закрыто")

    async def get_available_gifts(self) -> list[dict]:
        """
        Получить список доступных подарков через getAvailableGifts
        
        Returns:
            Список словарей с информацией о доступных подарках
        """
        try:
            result = await self.client(functions.payments.GetStarGiftsRequest(hash=0))
            gifts = []
            
            if hasattr(result, 'gifts'):
                for gift in result.gifts:
                    gifts.append({
                        "id": gift.id,
                        "sticker": gift.sticker if hasattr(gift, 'sticker') else None,
                        "stars": gift.stars,
                        "availability_remains": getattr(gift, "availability_remains", None),
                        "availability_total": getattr(gift, "availability_total", None),
                    })
            
            logger.info(f"📦 Доступно подарков: {len(gifts)}")
            return gifts
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка подарков: {e}")
            raise

    async def send_gift(self, user_id: int, gift_id: str) -> None:
        """
        Отправить подарок пользователю через sendGift API
        
        Args:
            user_id: Telegram ID получателя
            gift_id: ID подарка из getAvailableGifts
            
        Raises:
            RuntimeError: Если gift_id не указан
            UserIdInvalidError: Если user_id недействителен
            UserNotMutualContactError: Если пользователь недоступен
            FloodWaitError: Если нужно подождать из-за лимитов
            InsufficientStarsError: Если недостаточно Stars на балансе
        """
        if not gift_id:
            raise RuntimeError("Gift ID is not configured. Check TELEGRAM_GIFT_MAPPING in config.")
        
        if not self.is_connected:
            raise RuntimeError("Client is not connected. Call connect() first.")
        
        try:
            # Получаем InputUser получателя
            try:
                recipient = await self.client.get_input_entity(user_id)
            except ValueError as e:
                logger.error(f"❌ Не удалось найти пользователя {user_id}: {e}")
                raise UserIdInvalidError(f"User {user_id} not found")
            
            # Отправляем подарок через sendGift API
            # Этот метод должен автоматически списать Stars и отправить подарок
            result = await self.client(
                functions.payments.SendStarGiftRequest(
                    user_id=recipient,
                    gift_id=int(gift_id),
                    hide_name=False,  # Показываем имя отправителя
                    message="",  # Можно добавить текст
                )
            )
            
            logger.info(f"✅ Подарок {gift_id} успешно отправлен пользователю {user_id}")
            return result
            
        except FloodWaitError as e:
            logger.warning(f"⏳ Flood wait {e.seconds} секунд для user_id={user_id}")
            raise
            
        except UserIdInvalidError as e:
            logger.error(f"❌ Неверный user_id={user_id}: {e}")
            raise
            
        except UserNotMutualContactError as e:
            logger.error(f"❌ Пользователь {user_id} недоступен (не mutual contact): {e}")
            raise
        
        except Exception as e:
            error_msg = str(e).lower()
            
            # Проверяем ошибки связанные с недостатком Stars
            if any(keyword in error_msg for keyword in [
                "insufficient", 
                "not enough", 
                "balance",
                "stars",
                "purchase_failed",
                "payment_required",
                "star_gift_not_available"
            ]):
                logger.error(
                    f"💰 Недостаточно Stars для отправки подарка user_id={user_id}, gift_id={gift_id}"
                )
                raise InsufficientStarsError(
                    f"Insufficient Stars balance to send gift. Error: {e}"
                )
            
            # Другие неожиданные ошибки
            logger.exception(f"❌ Неожиданная ошибка при отправке подарка user_id={user_id}, gift_id={gift_id}")
            raise

    async def check_user_exists(self, user_id: int) -> bool:
        """
        Проверить существование пользователя
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            True если пользователь существует и доступен
        """
        try:
            user = await self.client.get_entity(user_id)
            return user is not None
        except (ValueError, UserIdInvalidError):
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка проверки пользователя {user_id}: {e}")
            return False
