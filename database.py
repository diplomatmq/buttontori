import sqlite3
from datetime import datetime
from typing import Optional, List


class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Создает подключение к БД с включенным WAL"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Включаем WAL режим для лучшей производительности
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def init_db(self):
        """Инициализирует базу данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                games_played INTEGER DEFAULT 0,
                total_winnings INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица игр
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                field TEXT,
                opened_cells TEXT DEFAULT '[]',
                is_finished INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица выигрышей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wins (
                win_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                user_id INTEGER,
                prize_type TEXT,
                prize_value INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games (game_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_user 
            ON games(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wins_user 
            ON wins(user_id)
        """)
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: str):
        """Добавляет пользователя или обновляет его данные"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, username) 
            VALUES (?, ?)
            ON CONFLICT(user_id) 
            DO UPDATE SET username = excluded.username
        """, (user_id, username))
        
        conn.commit()
        conn.close()
    
    def create_game(self, user_id: int, field: list) -> int:
        """Создает новую игру и возвращает её ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Сохраняем поле как строку
        field_str = str(field)
        
        cursor.execute("""
            INSERT INTO games (user_id, field)
            VALUES (?, ?)
        """, (user_id, field_str))
        
        game_id = cursor.lastrowid
        
        # Увеличиваем счетчик игр у пользователя
        cursor.execute("""
            UPDATE users 
            SET games_played = games_played + 1
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        return game_id
    
    def get_game(self, game_id: int) -> Optional[dict]:
        """Получает данные игры по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM games WHERE game_id = ?
        """, (game_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_game(self, game_id: int, opened_cells: list):
        """Обновляет список открытых ячеек в игре"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        opened_str = str(opened_cells)
        
        cursor.execute("""
            UPDATE games 
            SET opened_cells = ?
            WHERE game_id = ?
        """, (opened_str, game_id))
        
        conn.commit()
        conn.close()
    
    def finish_game(self, game_id: int):
        """Помечает игру как завершенную"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE games 
            SET is_finished = 1
            WHERE game_id = ?
        """, (game_id,))
        
        conn.commit()
        conn.close()
    
    def add_win(self, game_id: int, user_id: int, prize_type: str, prize_value: int):
        """Добавляет запись о выигрыше"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO wins (game_id, user_id, prize_type, prize_value)
            VALUES (?, ?, ?, ?)
        """, (game_id, user_id, prize_type, prize_value))
        
        conn.commit()
        conn.close()
    
    def update_user_stats(self, user_id: int, winnings: int):
        """Обновляет статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET total_winnings = total_winnings + ?
            WHERE user_id = ?
        """, (winnings, user_id))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Получает статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_top_users(self, limit: int = 10) -> List[dict]:
        """Получает топ пользователей по выигрышам"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, total_winnings, games_played
            FROM users
            ORDER BY total_winnings DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
