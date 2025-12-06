from typing import Dict, Optional, List
import random
import string
from datetime import datetime

from .game import Game, GameState
from .database import GameDatabase


class GameManager:
    """Менеджер игр (синглтон)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.active_games: Dict[str, Game] = {}
        self.player_to_game: Dict[int, str] = {}  # player_id -> game_id
        self.db = GameDatabase()

        # Загрузить активные игры из БД
        self._load_active_games()

        self._initialized = True

    def _load_active_games(self):
        """Загрузить активные игры из базы данных"""
        # Этот метод можно расширить для загрузки игр при старте
        pass

    def generate_game_id(self) -> str:
        """Сгенерировать уникальный ID игры"""
        while True:
            game_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if game_id not in self.active_games:
                return game_id

    def create_game(self, creator_id: int) -> Optional[str]:
        """Создать новую игру"""
        # Проверить, не участвует ли игрок уже в другой игре
        if creator_id in self.player_to_game:
            return None

        game_id = self.generate_game_id()
        game = Game(game_id, creator_id)

        self.active_games[game_id] = game
        return game_id

    def join_game(self, game_id: str, user_id: int, username: str, full_name: str) -> bool:
        """Присоединиться к игре"""
        if user_id in self.player_to_game:
            return False

        game = self.active_games.get(game_id)
        if not game or game.state != GameState.LOBBY:
            return False

        if game.add_player(user_id, username, full_name):
            self.player_to_game[user_id] = game_id
            return True

        return False

    def leave_game(self, user_id: int):
        """Покинуть игру"""
        game_id = self.player_to_game.get(user_id)
        if not game_id:
            return

        game = self.active_games.get(game_id)
        if game:
            game.remove_player(user_id)

            # Если в лобби не осталось игроков, удалить игру
            if not game.players:
                self.delete_game(game_id)
            else:
                # Сохранить состояние
                self.db.save_game(game)

        if user_id in self.player_to_game:
            del self.player_to_game[user_id]

    def get_game(self, game_id: str) -> Optional[Game]:
        """Получить игру по ID"""
        return self.active_games.get(game_id)

    def get_player_game(self, user_id: int) -> Optional[Game]:
        """Получить игру игрока"""
        game_id = self.player_to_game.get(user_id)
        if game_id:
            return self.active_games.get(game_id)
        return None

    def start_game(self, game_id: str) -> bool:
        """Начать игру"""
        game = self.active_games.get(game_id)
        if not game:
            return False

        if game.start_game():
            # Сохранить в БД
            self.db.save_game(game)
            return True

        return False

    def save_game_state(self, game_id: str):
        """Сохранить состояние игры"""
        game = self.active_games.get(game_id)
        if game:
            self.db.save_game(game)

    def delete_game(self, game_id: str):
        """Удалить игру"""
        game = self.active_games.get(game_id)
        if game:
            # Удалить связи игроков
            for player_id in list(self.player_to_game.keys()):
                if self.player_to_game[player_id] == game_id:
                    del self.player_to_game[player_id]

            # Удалить игру из активных
            del self.active_games[game_id]

            # Пометить как неактивную в БД
            self.db.delete_game(game_id)

    def get_available_games(self) -> List[Game]:
        """Получить список доступных игр в лобби"""
        return [
            game for game in self.active_games.values()
            if game.state == GameState.LOBBY and len(game.players) < 8
        ]

    def end_game(self, game_id: str):
        """Завершить игру"""
        game = self.active_games.get(game_id)
        if game:
            game.state = GameState.FINISHED

            # Освободить игроков
            for player_id in list(game.players.keys()):
                if player_id in self.player_to_game:
                    del self.player_to_game[player_id]

            # Сохранить и удалить
            self.db.save_game(game)
            self.delete_game(game_id)