import random
import string
import logging

# В начале класса или файла
logger = logging.getLogger(__name__)
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
# В game.py убедитесь, что у вас нет импорта Player в самом начале
# Вместо этого используйте только:
from config import Config
from board import Board, BoardCell, PropertyCell, StationCell, UtilityCell

# Сначала определяем базовые классы и константы
class GameState(Enum):
    LOBBY = "lobby"
    IN_PROGRESS = "in_game"  # <-- вот это значение!
    AUCTION = "auction"
    TRADE = "trade"
    FINISHED = "finished"


# Конфигурация (если Config не импортируется)
class GameConfig:
    START_MONEY = 1500
    MAX_PLAYERS = 8
    BOARD_SIZE = 40
    SALARY = 200
    JAIL_FINE = 50
    MIN_AUCTION_BID = 10

    # Карточки Шанс
    CHANCE_CARDS = [
        {"text": "Отправляйтесь на клетку 'Старт'", "action": "move_to", "value": 0},
        {"text": "Отправляйтесь в тюрьму", "action": "go_to_jail"},
        {"text": "Получите $50", "action": "add_money", "value": 50},
        {"text": "Заплатите $15", "action": "deduct_money", "value": 15},
        {"text": "Освобождение из тюрьмы", "action": "get_out_of_jail"},
    ]

    # Карточки Казна
    CHEST_CARDS = [
        {"text": "Вы выиграли конкурс красоты. Получите $20", "action": "add_money", "value": 20},
        {"text": "Оплатите налог на образование $100", "action": "deduct_money", "value": 100},
        {"text": "Вы получили наследство $100", "action": "add_money", "value": 100},
    ]


# Сначала определяем Player внутри, чтобы избежать круговых импортов
class PlayerStatus(Enum):
    ACTIVE = "active"
    BANKRUPT = "bankrupt"
    IN_JAIL = "in_jail"


class SimplePlayer:
    """Упрощенный класс игрока для использования в Game"""
    def __init__(self, user_id: int, username: str, full_name: str):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.position = 0
        self.money = Config.START_MONEY  # или GameConfig.START_MONEY
        self.properties = []
        self.stations = []
        self.utilities = []
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        self.color = "🔴"
        self.status = PlayerStatus.ACTIVE  # Убедитесь, что PlayerStatus определен
        self.double_count = 0
        self.total_rent_received = 0
        self.user_id = user_id
        # Основные атрибуты
        self.position = 0  # текущая позиция на поле
        self.money = 1500  # стартовый капитал
        self.in_jail = False
        self.get_out_of_jail_cards = 0  # карточки "Выход из тюрьмы"

        # Статистика
        self.total_rent_received = 0  # получено ренты
        self.total_rent_paid = 0  # уплачено ренты
        self.total_salary = 0  # получено зарплаты
        self.total_taxes_paid = 0  # уплачено налогов
        self.turns_played = 0  # сыграно ходов

        # Временные состояния
        self.doubles_count = 0  # счетчик дублей
        self.is_bankrupt = False
        self.is_ai = False


    def add_money(self, amount: int) -> bool:
        self.money += amount
        return True

    def deduct_money(self, amount: int) -> bool:
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    def can_afford(self, amount: int) -> bool:
        return self.money >= amount

    def go_to_jail(self):
        self.position = 10
        self.in_jail = True
        self.jail_turns = 0
        self.status = PlayerStatus.IN_JAIL

    def release_from_jail(self):
        self.in_jail = False
        self.jail_turns = 0
        self.status = PlayerStatus.ACTIVE

    def is_bankrupt(self) -> bool:
        return self.status == PlayerStatus.BANKRUPT or self.money < 0


# Упрощенная версия Board
class SimpleBoard:
    def __init__(self):
        self.cells = []
        self._init_board()

    def _init_board(self):
        """Создаем упрощенное поле"""
        # Базовые клетки
        for i in range(40):
            self.cells.append({
                'id': i,
                'name': f'Клетка {i}',
                'price': 0,
                'owner_id': None,
                'type': 'street' if i % 2 == 0 else 'other'
            })

    def get_cell(self, position: int):
        return self.cells[position % len(self.cells)]

    def get_rent_for_cell(self, position: int, dice_roll: int = 0) -> int:
        """Простой расчет ренты"""
        cell = self.get_cell(position)
        if not cell.get('owner_id'):
            return 0
        return 50  # Фиксированная рента для теста


# Теперь класс Game
class Game:
    """Класс игры с упрощенными зависимостями"""

    def __init__(self, game_id: str, creator_id: int):
        self.game_id = game_id
        self.creator_id = creator_id
        self.players: Dict[int, SimplePlayer] = {}
        self.player_order: List[int] = []
        self.current_player_index = 0
        self.state = GameState.LOBBY
        self.created_at = datetime.now()
        self.double_count = 0
        self.turn_count = 0
        self.board = SimpleBoard()
        self.free_parking_pot = 0
        self.auction_data: Optional[Dict] = None
        self.trade_data: Optional[Dict] = None
        self.chance_deck: List[Dict] = GameConfig.CHANCE_CARDS.copy()
        self.chest_deck: List[Dict] = GameConfig.CHEST_CARDS.copy()
        random.shuffle(self.chance_deck)
        random.shuffle(self.chest_deck)

    def add_player(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить игрока в игру"""
        if user_id in self.players:
            return False
        if self.state != GameState.LOBBY:
            return False
        if len(self.players) >= GameConfig.MAX_PLAYERS:
            return False

        player = SimplePlayer(user_id, username, full_name)
        self.players[user_id] = player
        return True

    def remove_player(self, user_id: int):
        """Удалить игрока из игры"""
        if user_id in self.players:
            if user_id in self.player_order:
                self.player_order.remove(user_id)
                if self.current_player_index >= len(self.player_order):
                    self.current_player_index = 0
            del self.players[user_id]

    def start_game(self) -> bool:
        """Начать игру"""
        logger.info(f"Starting game. Current state: {self.state}, Players: {len(self.players)}")

        if len(self.players) < 2:
            logger.warning("Not enough players to start")
            return False

        if self.state != GameState.LOBBY:
            logger.warning(f"Cannot start game. Current state is {self.state}, not LOBBY")
            return False

        self.state = GameState.IN_PROGRESS
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.current_player_index = 0
        self.turn_count = 1

        logger.info(f"Game started successfully. New state: {self.state}")
        return True

    def get_current_player(self) -> Optional[SimplePlayer]:
        """Получить текущего игрока"""
        if not self.player_order:
            return None
        current_id = self.player_order[self.current_player_index]
        return self.players.get(current_id)

    def next_turn(self):
        """Передать ход следующему игроку"""
        if not self.player_order:
            return

        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.double_count = 0
        self.turn_count += 1

    def roll_dice(self) -> Tuple[int, int, int]:
        """Бросить кубики"""
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        if dice1 == dice2:
            self.double_count += 1
        else:
            self.double_count = 0

        return dice1, dice2, total

    def move_player(self, player: SimplePlayer, steps: int) -> Dict[str, Any]:
        """Переместить игрока"""
        old_position = player.position
        new_position = (old_position + steps) % GameConfig.BOARD_SIZE
        player.position = new_position

        passed_start = (old_position + steps) >= GameConfig.BOARD_SIZE
        salary = GameConfig.SALARY if passed_start else 0

        if passed_start:
            player.add_money(salary)

        return {
            "old_position": old_position,
            "new_position": new_position,
            "passed_start": passed_start,
            "salary": salary
        }

    def process_cell_action(self, player: SimplePlayer, dice_roll: int = 0) -> Dict[str, Any]:
        """Обработать действие клетки"""
        cell = self.board.get_cell(player.position)
        result = {
            "cell": cell,
            "action": None,
            "message": "",
            "owner_id": None,
            "rent": 0
        }

        # Простая логика для разных типов клеток
        if cell['type'] == 'street':
            if not cell['owner_id']:
                result["action"] = "buy_property"
                result["message"] = f"Свободная улица! Цена: $100"
            elif cell['owner_id'] == player.user_id:
                result["action"] = "own_property"
                result["message"] = "Это ваша собственность!"
            else:
                result["action"] = "pay_rent"
                result["owner_id"] = cell['owner_id']
                result["rent"] = 50
                result["message"] = f"Чужая собственность! Рента: $50"
        else:
            result["action"] = "other"
            result["message"] = f"Клетка {cell['name']}"

        return result

    def buy_property(self, player: SimplePlayer, position: int) -> bool:
        """Купить собственность"""
        cell = self.board.get_cell(position)

        if cell['owner_id'] is not None:
            return False

        if player.money < 100:  # Простая цена
            return False

        player.deduct_money(100)
        cell['owner_id'] = player.user_id
        player.properties.append(position)
        return True

    def force_start(self) -> bool:
        """Принудительный старт игры (для админов)"""
        if len(self.players) < 1:  # Можно начать даже с одним игроком
            return False

        self.state = GameState.IN_PROGRESS
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.current_player_index = 0
        self.turn_count = 1

        # Если только один игрок - автоматически ходит
        if len(self.players) == 1:
            player = self.get_current_player()
            if player:
                player.money = Config.START_MONEY

        return True

    def can_join(self) -> bool:
        """Может ли игрок присоединиться сейчас"""
        return self.state == GameState.LOBBY and len(self.players) < Config.MAX_PLAYERS

    def is_player_in_game(self, user_id: int) -> bool:
        """Проверить, находится ли игрок в игре"""
        return user_id in self.players

    def draw_card(self, deck_type: str) -> Dict:
        """Вытянуть карточку"""
        if deck_type == "chance":
            deck = self.chance_deck
        else:
            deck = self.chest_deck

        if not deck:
            if deck_type == "chance":
                deck = GameConfig.CHANCE_CARDS.copy()
                random.shuffle(deck)
                self.chance_deck = deck
            else:
                deck = GameConfig.CHEST_CARDS.copy()
                random.shuffle(deck)
                self.chest_deck = deck

        card = deck.pop(0)
        return card

    def apply_card_action(self, player: SimplePlayer, card: Dict) -> Dict[str, Any]:
        """Применить действие карточки"""
        result = {
            "message": card.get("text", ""),
            "applied": True
        }

        action = card.get("action")
        value = card.get("value")

        if action == "move_to":
            if isinstance(value, int):
                player.position = value
                result["message"] += f"\n📍 Перемещены на клетку {value}"

        elif action == "go_to_jail":
            player.go_to_jail()
            result["message"] += "\n🔒 Отправлены в тюрьму!"

        elif action == "add_money":
            if isinstance(value, int):
                player.add_money(value)
                result["message"] += f"\n💰 Получено ${value}"

        elif action == "deduct_money":
            if isinstance(value, int):
                if player.deduct_money(value):
                    self.free_parking_pot += value
                    result["message"] += f"\n💸 Уплачено ${value}"
                else:
                    result["message"] += f"\n💥 Недостаточно денег!"
                    result["applied"] = False

        elif action == "get_out_of_jail":
            player.get_out_of_jail_cards += 1
            result["message"] += f"\n🎫 Получена карта освобождения!"

        return result

    def get_winner(self) -> Optional[SimplePlayer]:
        """Получить победителя"""
        active_players = [p for p in self.players.values() if not p.is_bankrupt()]

        if len(active_players) == 1:
            return active_players[0]

        # Если несколько игроков, выбираем самого богатого
        if active_players:
            return max(active_players, key=lambda p: p.money)

        return None

    def to_dict(self) -> Dict:
        """Конвертировать в словарь для сохранения"""
        print(f"🔍 DEBUG to_dict: Конвертирую игру {self.game_id}")

        try:
            result = {
                "game_id": self.game_id,
                "creator_id": self.creator_id,
                "players": {},
                "player_order": self.player_order,
                "current_player_index": self.current_player_index,
                "state": self.state.value,
                "created_at": self.created_at.isoformat(),
                "double_count": self.double_count,
                "turn_count": self.turn_count,
                "free_parking_pot": self.free_parking_pot
            }

            print(f"🔍 DEBUG: Добавляю {len(self.players)} игроков...")
            for k, v in self.players.items():
                result["players"][str(k)] = self._player_to_dict(v)

            print(f"✅ DEBUG to_dict: Успешно")
            return result

        except Exception as e:
            print(f"❌ ОШИБКА в to_dict: {e}")
            raise

    def _player_to_dict(self, player: SimplePlayer) -> Dict:
        """Конвертировать игрока в словарь"""
        try:
            # Проверяем наличие всех атрибутов
            player_data = {
                "user_id": player.user_id,
                "username": player.username if hasattr(player, 'username') else "",
                "full_name": player.full_name if hasattr(player, 'full_name') else "",
                "position": player.position if hasattr(player, 'position') else 0,
                "money": player.money if hasattr(player, 'money') else 0,
                "properties": player.properties if hasattr(player, 'properties') else [],
                "stations": player.stations if hasattr(player, 'stations') else [],
                "utilities": player.utilities if hasattr(player, 'utilities') else [],
                "in_jail": player.in_jail if hasattr(player, 'in_jail') else False,
                "jail_turns": player.jail_turns if hasattr(player, 'jail_turns') else 0,
                "get_out_of_jail_cards": player.get_out_of_jail_cards if hasattr(player,
                                                                                 'get_out_of_jail_cards') else 0,
                "color": player.color if hasattr(player, 'color') else "",
                "status": player.status.value if hasattr(player, 'status') else "active",
                "double_count": player.double_count if hasattr(player, 'double_count') else 0
            }
            return player_data
        except Exception as e:
            print(f"❌ ОШИБКА в _player_to_dict для игрока {getattr(player, 'user_id', 'unknown')}: {e}")
            raise

    @classmethod
    def from_dict(cls, data: Dict) -> 'Game':
        """Создать игру из словаря"""
        game = cls(data["game_id"], data["creator_id"])

        game.players = {}
        for user_id_str, player_data in data["players"].items():
            user_id = int(user_id_str)
            player = SimplePlayer(
                player_data["user_id"],
                player_data["username"],
                player_data["full_name"]
            )
            player.position = player_data.get("position", 0)
            player.money = player_data.get("money", GameConfig.START_MONEY)
            player.properties = player_data.get("properties", [])
            player.stations = player_data.get("stations", [])
            player.utilities = player_data.get("utilities", [])
            player.in_jail = player_data.get("in_jail", False)
            player.jail_turns = player_data.get("jail_turns", 0)
            player.get_out_of_jail_cards = player_data.get("get_out_of_jail_cards", 0)
            player.color = player_data.get("color", "🔴")
            player.status = PlayerStatus(player_data.get("status", "active"))
            player.double_count = player_data.get("double_count", 0)

            game.players[user_id] = player

        game.player_order = data.get("player_order", [])
        game.current_player_index = data.get("current_player_index", 0)
        game.state = GameState(data.get("state", "lobby"))
        game.created_at = datetime.fromisoformat(data["created_at"])
        game.double_count = data.get("double_count", 0)
        game.turn_count = data.get("turn_count", 0)
        game.free_parking_pot = data.get("free_parking_pot", 0)

        return game