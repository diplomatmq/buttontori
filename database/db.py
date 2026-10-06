from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, Game, PrizeDelivery, User


class Database:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_db(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def add_user(self, user_id: int, username: str) -> None:
        async with self.session_factory() as session:
            user = await session.get(User, user_id)
            if user:
                user.username = username
            else:
                session.add(User(user_id=user_id, username=username))
            await session.commit()

    async def create_game(self, user_id: int, field: list[str]) -> int:
        async with self.session_factory() as session:
            game = Game(user_id=user_id, field=repr(field))
            session.add(game)
            await session.execute(
                update(User).where(User.user_id == user_id).values(games_played=User.games_played + 1)
            )
            await session.commit()
            await session.refresh(game)
            return game.game_id

    async def get_game(self, game_id: int) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            game = await session.get(Game, game_id)
            if not game:
                return None
            return {
                "game_id": game.game_id,
                "user_id": game.user_id,
                "field": game.field,
                "opened_cells": game.opened_cells,
                "is_finished": game.is_finished,
            }

    async def update_game(self, game_id: int, opened_cells: list[int]) -> None:
        async with self.session_factory() as session:
            game = await session.get(Game, game_id)
            if game:
                game.opened_cells = repr(opened_cells)
                await session.commit()

    async def update_user_stats(self, user_id: int, winnings: int) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(User).where(User.user_id == user_id).values(total_winnings=User.total_winnings + winnings)
            )
            await session.commit()

    async def record_prize(self, user_id: int, prize_type: str, prize_value: int, gift_id: str | None = None) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(User).where(User.user_id == user_id).values(total_winnings=User.total_winnings + prize_value)
            )
            if prize_type != "nft":
                session.add(
                    PrizeDelivery(
                        user_id=user_id,
                        prize_type=prize_type,
                        prize_value=prize_value,
                        gift_id=gift_id,
                    )
                )
            await session.commit()

    async def enqueue_delivery(self, user_id: int, prize_type: str, prize_value: int, gift_id: str | None = None) -> int:
        async with self.session_factory() as session:
            delivery = PrizeDelivery(
                user_id=user_id, 
                prize_type=prize_type, 
                prize_value=prize_value,
                gift_id=gift_id,
            )
            session.add(delivery)
            await session.commit()
            await session.refresh(delivery)
            return delivery.delivery_id

    async def claim_delivery(self, delivery_id: int) -> PrizeDelivery | None:
        async with self.session_factory() as session:
            delivery = await session.scalar(
                select(PrizeDelivery)
                .where(
                    PrizeDelivery.delivery_id == delivery_id,
                    (PrizeDelivery.status == "pending")
                    | (
                        (PrizeDelivery.status == "processing")
                        & (
                            PrizeDelivery.claimed_at
                            < datetime.now(timezone.utc) - timedelta(minutes=5)
                        )
                    ),
                )
                .with_for_update(skip_locked=True)
            )
            if not delivery:
                return None
            delivery.status = "processing"
            delivery.attempts += 1
            delivery.claimed_at = datetime.now(timezone.utc)
            await session.commit()
            return delivery

    async def pending_delivery_ids(self) -> list[int]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(PrizeDelivery.delivery_id)
                .where(PrizeDelivery.status.in_(("pending", "processing")))
                .order_by(PrizeDelivery.delivery_id)
            )
            return list(result)

    async def mark_delivered(self, delivery_id: int) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(PrizeDelivery)
                .where(PrizeDelivery.delivery_id == delivery_id)
                .values(
                    status="delivered",
                    delivered_at=datetime.now(timezone.utc),
                    claimed_at=None,
                    last_error=None,
                )
            )
            await session.commit()

    async def mark_delivery_failed(self, delivery_id: int, error: str, increment_attempts: bool = True) -> None:
        """
        Помечает доставку как failed или возвращает в pending для повторной попытки.
        
        Args:
            delivery_id: ID доставки
            error: Текст ошибки
            increment_attempts: Учитывать ли эту попытку в счетчике (False для временных ошибок типа недостатка Stars)
        """
        async with self.session_factory() as session:
            delivery = await session.get(PrizeDelivery, delivery_id)
            
            if not delivery:
                return
            
            # Проверяем счетчик попыток только если мы учитываем попытки
            if increment_attempts and delivery.attempts >= 3:
                # Если исчерпаны попытки - помечаем как failed навсегда
                await session.execute(
                    update(PrizeDelivery)
                    .where(PrizeDelivery.delivery_id == delivery_id)
                    .values(status="failed", claimed_at=None, last_error=error[:4000])
                )
            else:
                # Иначе возвращаем в pending для повторной попытки
                await session.execute(
                    update(PrizeDelivery)
                    .where(PrizeDelivery.delivery_id == delivery_id)
                    .values(status="pending", claimed_at=None, last_error=error[:4000])
                )
            
            await session.commit()

    async def get_delivery_stats(self, user_id: int) -> dict[str, Any]:
        """Получить статистику доставок для пользователя"""
        async with self.session_factory() as session:
            pending = await session.scalar(
                select(func.count()).select_from(PrizeDelivery).where(
                    PrizeDelivery.user_id == user_id,
                    PrizeDelivery.status == "pending"
                )
            )
            delivered = await session.scalar(
                select(func.count()).select_from(PrizeDelivery).where(
                    PrizeDelivery.user_id == user_id,
                    PrizeDelivery.status == "delivered"
                )
            )
            failed = await session.scalar(
                select(func.count()).select_from(PrizeDelivery).where(
                    PrizeDelivery.user_id == user_id,
                    PrizeDelivery.status == "failed"
                )
            )
            return {
                "pending": pending or 0,
                "delivered": delivered or 0,
                "failed": failed or 0,
            }

    async def get_user_stats(self, user_id: int) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return None
            return {
                "games_played": user.games_played,
                "total_winnings": user.total_winnings,
                "created_at": user.created_at.isoformat() if user.created_at else "",
            }

    async def get_top_users(self, limit: int = 10) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            users = await session.scalars(select(User).order_by(desc(User.total_winnings)).limit(limit))
            return [
                {
                    "username": user.username,
                    "total_winnings": user.total_winnings,
                    "games_played": user.games_played,
                }
                for user in users
            ]
