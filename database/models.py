from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255))
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    total_winnings: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    field: Mapped[str] = mapped_column(Text)
    opened_cells: Mapped[str] = mapped_column(Text, default="[]")
    is_finished: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Win(Base):
    __tablename__ = "wins"

    win_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.game_id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    prize_type: Mapped[str] = mapped_column(String(32))
    prize_value: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrizeDelivery(Base):
    __tablename__ = "prize_deliveries"

    delivery_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    prize_type: Mapped[str] = mapped_column(String(32))
    prize_value: Mapped[int] = mapped_column(Integer)
    gift_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CasinoGame(Base):
    __tablename__ = "casino_games"

    game_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    source_message_id: Mapped[int] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(Text)
    selected: Mapped[int] = mapped_column(Integer, default=-1)
    finished: Mapped[bool] = mapped_column(default=False)
    current_prize: Mapped[str | None] = mapped_column(String(32))
    stage: Mapped[int | None] = mapped_column(Integer)
    upgrade_target: Mapped[str | None] = mapped_column(String(32))
    upgrade_winner: Mapped[int | None] = mapped_column(Integer)
    upgrade_slots: Mapped[int] = mapped_column(Integer, default=0)
    upgrade_revealed: Mapped[str] = mapped_column(Text, default="{}")
    upgrade_started: Mapped[bool] = mapped_column(default=False)
    prize_claimed: Mapped[bool] = mapped_column(default=False)
    bar_bear_index: Mapped[int | None] = mapped_column(Integer)
    bar_selected: Mapped[int] = mapped_column(Integer, default=-1)
    bar_revealed: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
