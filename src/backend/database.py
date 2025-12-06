import sqlite3
import json
from typing import Optional, Dict, Any
from datetime import datetime
import os

from .game import Game


class GameDatabase:
    """База данных для сохранения игр"""

    def __init__(self, db_path: str = "data/games.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Инициализировать базу данных"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица игр
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                game_data TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # Таблица игроков в играх (для быстрого поиска игр по player_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_players (
                game_id TEXT,
                player_id INTEGER,
                FOREIGN KEY (game_id) REFERENCES games (game_id)
            )
        ''')

        conn.commit()
        conn.close()

    def save_game(self, game: Game):
        """Сохранить игру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        game_data = json.dumps(game.to_dict())

        # Проверить, существует ли уже игра
        cursor.execute(
            "SELECT COUNT(*) FROM games WHERE game_id = ?",
            (game.game_id,)
        )
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Обновить существующую запись
            cursor.execute('''
                UPDATE games 
                SET game_data = ?, updated_at = ?, is_active = ?
                WHERE game_id = ?
            ''', (
                game_data,
                datetime.now().isoformat(),
                1 if game.state.value != "finished" else 0,
                game.game_id
            ))

            # Удалить старых игроков
            cursor.execute(
                "DELETE FROM game_players WHERE game_id = ?",
                (game.game_id,)
            )
        else:
            # Вставить новую запись
            cursor.execute('''
                INSERT INTO games (game_id, creator_id, created_at, updated_at, game_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                game.game_id,
                game.creator_id,
                game.created_at.isoformat(),
                datetime.now().isoformat(),
                game_data
            ))

        # Добавить игроков
        for player_id in game.players.keys():
            cursor.execute('''
                INSERT INTO game_players (game_id, player_id)
                VALUES (?, ?)
            ''', (game.game_id, player_id))

        conn.commit()
        conn.close()

    def load_game(self, game_id: str) -> Optional[Game]:
        """Загрузить игру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT game_data FROM games WHERE game_id = ? AND is_active = 1",
            (game_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                game_dict = json.loads(row[0])
                return Game.from_dict(game_dict)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Ошибка загрузки игры: {e}")
                return None

        return None

    def get_player_games(self, player_id: int) -> list:
        """Получить все активные игры игрока"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT g.game_data 
            FROM games g
            JOIN game_players gp ON g.game_id = gp.game_id
            WHERE gp.player_id = ? AND g.is_active = 1
            ORDER BY g.updated_at DESC
        ''', (player_id,))

        games = []
        for row in cursor.fetchall():
            try:
                game_dict = json.loads(row[0])
                games.append(Game.from_dict(game_dict))
            except (json.JSONDecodeError, KeyError):
                continue

        conn.close()
        return games

    def delete_game(self, game_id: str):
        """Удалить игру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE games SET is_active = 0 WHERE game_id = ?",
            (game_id,)
        )

        conn.commit()
        conn.close()

    def cleanup_old_games(self, days_old: int = 7):
        """Очистить старые завершенные игры"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute('''
            UPDATE games 
            SET is_active = 0 
            WHERE updated_at < ? AND is_active = 1
        ''', (cutoff_date.isoformat(),))

        conn.commit()
        conn.close()