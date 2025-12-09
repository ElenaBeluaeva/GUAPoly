from typing import Dict, Optional, List, Any
import random
import string
from datetime import datetime

from config import Config
from game import Game, GameState
from database import GameDatabase
from player import Player

class GameManager:
    """Полный менеджер игр - работает для всех пользователей"""

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
        try:
            print("✅ Менеджер игр инициализирован")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки игр: {e}")

    def generate_game_id(self) -> str:
        """Сгенерировать уникальный ID игры"""
        while True:
            game_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if game_id not in self.active_games:
                return game_id

    def create_game(self, creator_id: int, username: str, full_name: str) -> Optional[str]:
        """Создать новую игру и сразу добавить создателя"""
        # Проверить, не участвует ли игрок уже в другой игре
        if creator_id in self.player_to_game:
            return None

        game_id = self.generate_game_id()
        game = Game(game_id, creator_id)

        # Добавляем создателя в игру
        if not game.add_player(creator_id, username, full_name):
            return None

        self.active_games[game_id] = game
        self.player_to_game[creator_id] = game_id

        # Сохраняем в БД
        self.db.save_game(game)

        return game_id

    def join_game(self, game_id: str, user_id: int, username: str, full_name: str) -> bool:
        """Присоединиться к игре"""
        # Проверяем, не в игре ли уже
        if user_id in self.player_to_game:
            return False

        game = self.active_games.get(game_id)
        if not game:
            return False

        # Можно присоединиться только в лобби
        if game.state != GameState.LOBBY:
            return False

        # Проверяем лимит игроков
        if len(game.players) >= Config.MAX_PLAYERS:
            return False

        # Добавляем игрока
        if game.add_player(user_id, username, full_name):
            self.player_to_game[user_id] = game_id
            # Сохраняем состояние
            self.db.save_game(game)
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

        # Удаляем связь игрока с игрой
        if user_id in self.player_to_game:
            del self.player_to_game[user_id]

    def get_game(self, game_id: str) -> Optional[Game]:
        """Получить игру по ID"""
        return self.active_games.get(game_id)

    def get_player_game(self, user_id: int) -> Optional[Game]:
        """Получить игру игрока"""
        # Ищем игрока во всех активных играх
        for game in self.active_games.values():
            if user_id in game.players:
                return game
        return None

    def start_game(self, game_id: str) -> bool:
        """Начать игру"""
        game = self.active_games.get(game_id)
        if not game:
            return False

        # Нужно хотя бы 2 игрока
        if len(game.players) < 2:
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
            if game.state == GameState.LOBBY and len(game.players) < Config.MAX_PLAYERS
        ]

    def end_game(self, game_id: str):
        """Завершить игру"""
        game = self.active_games.get(game_id)
        if game:
            game.state = GameState.FINISHED

            # Обновить статистику игроков
            winner = game.get_winner()
            for player in game.players.values():
                stats = {
                    'games_played': 1,
                    'games_won': 1 if winner and player.user_id == winner.user_id else 0,
                    'total_money_earned': player.money,
                }

                # Добавляем статистику если она есть
                if hasattr(player, 'total_rent_paid'):
                    stats['total_rent_paid'] = getattr(player, 'total_rent_paid', 0)
                if hasattr(player, 'total_rent_received'):
                    stats['total_rent_received'] = getattr(player, 'total_rent_received', 0)
                if hasattr(player, 'properties_bought'):
                    stats['properties_bought'] = getattr(player, 'properties_bought', 0)
                if hasattr(player, 'houses_built'):
                    stats['houses_built'] = getattr(player, 'houses_built', 0)
                if hasattr(player, 'hotels_built'):
                    stats['hotels_built'] = getattr(player, 'hotels_built', 0)

                self.db.update_player_stats(
                    player.user_id,
                    player.username,
                    player.full_name,
                    stats
                )

            # Освободить игроков
            for player_id in list(game.players.keys()):
                if player_id in self.player_to_game:
                    del self.player_to_game[player_id]

            # Сохранить и удалить
            self.db.save_game(game)
            self.delete_game(game_id)

    def get_player_stats(self, user_id: int) -> Optional[Dict]:
        """Получить статистику игрока"""
        return self.db.get_player_stats(user_id)

    def get_top_players(self, limit: int = 10) -> List[Dict]:
        """Получить топ игроков"""
        return self.db.get_top_players(limit)

    def cleanup(self):
        """Очистка старых игр"""
        self.db.cleanup_old_games()

    def force_start_game(self, game_id: str, user_id: int) -> bool:
        """Принудительный старт игры (работает для всех создателей)"""
        game = self.active_games.get(game_id)
        if not game:
            return False

        # Только создатель может принудительно стартовать
        if game.creator_id != user_id:
            return False

        # Принудительный старт
        if game.force_start():
            self.db.save_game(game)
            return True

        return False

    def get_all_players_in_game(self, game_id: str) -> Dict[int, Player]:
        """Получить всех игроков в игре"""
        game = self.active_games.get(game_id)
        return game.players if game else {}

    def get_user_by_username(self, username: str) -> Optional[int]:
        """Найти ID пользователя по username"""
        username = username.lower().replace('@', '')
        for game in self.active_games.values():
            for player in game.players.values():
                if player.username and player.username.lower() == username:
                    return player.user_id
        return None

    def is_player_in_game(self, user_id: int) -> bool:
        """Проверить, находится ли игрок в игре"""
        return user_id in self.player_to_game

    def get_player_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию об игроке"""
        game = self.get_player_game(user_id)
        if not game:
            return None

        player = game.players.get(user_id)
        if not player:
            return None

        return {
            'user_id': player.user_id,
            'username': player.username,
            'full_name': player.full_name,
            'position': player.position,
            'money': player.money,
            'game_id': game.game_id,
            'is_creator': player.user_id == game.creator_id,
            'is_current_turn': (game.state == GameState.IN_PROGRESS and
                                game.get_current_player() and
                                game.get_current_player().user_id == user_id)
        }