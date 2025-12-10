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
from board import Board, BoardCell, PropertyCell, StationCell, UtilityCell, CellType


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
        {"text": "Вас оштрафовали за превышение скорости. Заплатите $15", "action": "deduct_money", "value": 15},
        {"text": "Вы заняли второе место в конкурсе красоты. Получите $10", "action": "add_money", "value": 10},
        {"text": "Оплатите налог на образование $150", "action": "deduct_money", "value": 150},
    ]

    # Карточки Казна
    CHEST_CARDS = [
        {"text": "Вы выиграли конкурс красоты. Получите $20", "action": "add_money", "value": 20},
        {"text": "Оплатите налог на образование $100", "action": "deduct_money", "value": 100},
        {"text": "Вы получили наследство $100", "action": "add_money", "value": 100},
        {"text": "Отправляйтесь в тюрьму. Не проходите через 'Старт'", "action": "go_to_jail"},
        {"text": "Банк выплачивает вам дивиденды $50", "action": "add_money", "value": 50},
        {"text": "Возврат подоходного налога $20", "action": "add_money", "value": 20},
        {"text": "Освобождение из тюрьмы", "action": "get_out_of_jail"},
        {"text": "Оплатите счет за лечение $100", "action": "deduct_money", "value": 100},
    ]


# Сначала определяем Player внутри, чтобы избежать круговых импортов
class PlayerStatus(Enum):
    ACTIVE = "active"
    BANKRUPT = "bankrupt"
    IN_JAIL = "in_jail"

PLAYER_COLORS = [
        "🔴",  # красный
        "🔵",  # синий
        "🟢",  # зеленый
        "🟡",  # желтый
        "🟣",  # фиолетовый
        "🟠",  # оранжевый
        "⚫",  # черный
        "⚪",  # белый
    ]


class SimplePlayer:
    """Упрощенный класс игрока для использования в Game"""

    def __init__(self, user_id: int, username: str, full_name: str, color_index: int = 0):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.position = 0
        self.money = Config.START_MONEY
        self.properties = []
        self.stations = []
        self.utilities = []
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0

        # Назначаем цвет игроку
        if 0 <= color_index < len(PLAYER_COLORS):
            self.color = PLAYER_COLORS[color_index]
        else:
            self.color = PLAYER_COLORS[color_index % len(PLAYER_COLORS)]

        self.status = PlayerStatus.ACTIVE
        self.double_count = 0
        self.total_rent_received = 0
        self.user_id = user_id
        # Основные атрибуты
        self.position = 0  # текущая позиция на поле
        self.money = 1500  # стартовый капитал
        self.in_jail = False
        self.get_out_of_jail_cards = 0  # карточки "Выход из тюрьмы"
        self.properties_bought = 0  # счетчик купленной недвижимости

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

    def increment_properties_bought(self):
        """Увеличить счетчик купленной недвижимости"""
        self.properties_bought += 1


# Теперь класс Game
class Game:
    """Класс игры с привязанной доской"""

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
        self.board = Board()  # Используем полную доску из board.py
        self.free_parking_pot = 0
        self.auction_data: Optional[Dict] = None
        self.trade_data: Optional[Dict] = None
        self.chance_deck: List[Dict] = GameConfig.CHANCE_CARDS.copy()
        self.chest_deck: List[Dict] = GameConfig.CHEST_CARDS.copy()
        random.shuffle(self.chance_deck)
        random.shuffle(self.chest_deck)
        self.used_colors = set()

    def add_player(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить игрока в игру"""
        if user_id in self.players:
            return False
        if self.state != GameState.LOBBY:
            return False
        if len(self.players) >= GameConfig.MAX_PLAYERS:
            return False

        # Находим свободный цвет
        available_colors = [i for i in range(len(PLAYER_COLORS))
                            if i not in self.used_colors]

        if available_colors:
            color_index = random.choice(available_colors)
        else:
            # Если все цвета заняты, используем любой
            color_index = random.randint(0, len(PLAYER_COLORS) - 1)

        self.used_colors.add(color_index)

        player = SimplePlayer(user_id, username, full_name, color_index)
        self.players[user_id] = player
        return True

    def remove_player(self, user_id: int):
        """Удалить игрока из игры"""
        if user_id in self.players:
            player = self.players[user_id]
            # Освобождаем цвет
            if hasattr(player, 'color'):
                for i, color in enumerate(PLAYER_COLORS):
                    if color == player.color:
                        if i in self.used_colors:
                            self.used_colors.remove(i)
                        break

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
        new_position = (old_position + steps) % len(self.board.cells)
        player.position = new_position

        passed_start = (old_position + steps) >= len(self.board.cells)
        salary = Config.SALARY if passed_start else 0

        if passed_start:
            player.add_money(salary)
            player.total_salary += salary

        return {
            "old_position": old_position,
            "new_position": new_position,
            "passed_start": passed_start,
            "salary": salary
        }

    def process_cell_action(self, player: SimplePlayer, dice_roll: int = 0) -> Dict[str, Any]:
        """Обработать действие клетки, на которой стоит игрок"""
        cell = self.board.get_cell(player.position)
        result = {
            "cell": cell,
            "action": None,
            "message": "",
            "owner_id": None,
            "rent": 0,
            "amount": 0,
            "card": None
        }

        # Обработка разных типов клеток
        if cell.type == CellType.GO:
            result["action"] = "pass_go"
            result["message"] = "Стартовая клетка!"

        elif cell.type == CellType.PROPERTY:
            if not cell.owner_id:
                result["action"] = "buy_property"
                result["message"] = f"Свободная улица: {cell.name}! Цена: ${cell.price}"
            elif cell.owner_id == player.user_id:
                result["action"] = "own_property"
                result["message"] = f"Это ваша собственность: {cell.name}"
            else:
                owner = self.players.get(cell.owner_id)
                if owner:
                    rent = cell.get_rent(dice_roll, self.board.get_owner_assets(cell.owner_id))
                    result["action"] = "pay_rent"
                    result["owner_id"] = cell.owner_id
                    result["rent"] = rent
                    result["message"] = f"Чужая собственность! Рента {owner.full_name}: ${rent}"

        elif cell.type == CellType.STATION:
            if not cell.owner_id:
                result["action"] = "buy_property"
                result["message"] = f"Свободный вокзал: {cell.name}! Цена: ${cell.price}"
            elif cell.owner_id == player.user_id:
                result["action"] = "own_property"
                result["message"] = f"Это ваш вокзал: {cell.name}"
            else:
                owner = self.players.get(cell.owner_id)
                if owner:
                    rent = cell.get_rent(dice_roll, self.board.get_owner_assets(cell.owner_id))
                    result["action"] = "pay_rent"
                    result["owner_id"] = cell.owner_id
                    result["rent"] = rent
                    result["message"] = f"Чужой вокзал! Рента {owner.full_name}: ${rent}"

        elif cell.type == CellType.UTILITY:
            if not cell.owner_id:
                result["action"] = "buy_property"
                result["message"] = f"Свободное предприятие: {cell.name}! Цена: ${cell.price}"
            elif cell.owner_id == player.user_id:
                result["action"] = "own_property"
                result["message"] = f"Это ваше предприятие: {cell.name}"
            else:
                owner = self.players.get(cell.owner_id)
                if owner:
                    rent = cell.get_rent(dice_roll, self.board.get_owner_assets(cell.owner_id))
                    result["action"] = "pay_rent"
                    result["owner_id"] = cell.owner_id
                    result["rent"] = rent
                    result["message"] = f"Чужое предприятие! Рента {owner.full_name}: ${rent}"

        elif cell.type == CellType.TAX:
            result["action"] = "pay_tax"
            result["amount"] = cell.price
            result["message"] = f"Налог: {cell.description}. Заплатите ${cell.price}"

        elif cell.type == CellType.CHANCE:
            card = self.draw_card("chance")
            result["action"] = "chance_card"
            result["card"] = card
            result["message"] = f"Шанс: {card['text']}"

        elif cell.type == CellType.CHEST:
            card = self.draw_card("chest")
            result["action"] = "chest_card"
            result["card"] = card
            result["message"] = f"Казна: {card['text']}"

        elif cell.type == CellType.JAIL:
            result["action"] = "jail_visit"
            result["message"] = "Тюрьма (просто посещение)"

        elif cell.type == CellType.GO_TO_JAIL:
            result["action"] = "go_to_jail"
            result["message"] = "Отправляйтесь в тюрьму!"

        elif cell.type == CellType.FREE_PARKING:
            result["action"] = "free_parking"
            result["message"] = "Бесплатная стоянка!"

        else:
            result["action"] = "other"
            result["message"] = f"Клетка {cell.name}"

        return result

    def apply_cell_action(self, player: SimplePlayer, action_result: Dict[str, Any], dice_roll: int = 0) -> Dict[
        str, Any]:
        """Применить действие клетки"""
        result = {
            "success": True,
            "message": "",
            "player_money_changed": False,
            "amount": 0
        }

        action = action_result.get("action")

        if action == "pay_rent":
            rent = action_result.get("rent", 0)
            owner_id = action_result.get("owner_id")

            if player.deduct_money(rent):
                owner = self.players.get(owner_id)
                if owner:
                    owner.add_money(rent)
                    owner.total_rent_received += rent
                    player.total_rent_paid += rent

                result["message"] = f"Уплачена рента: ${rent}"
                result["player_money_changed"] = True
                result["amount"] = rent
            else:
                result["success"] = False
                result["message"] = f"Недостаточно денег для уплаты ренты: ${rent}"

        elif action == "pay_tax":
            amount = action_result.get("amount", 0)

            if player.deduct_money(amount):
                self.free_parking_pot += amount
                player.total_taxes_paid += amount

                result["message"] = f"Уплачен налог: ${amount}"
                result["player_money_changed"] = True
                result["amount"] = amount
            else:
                result["success"] = False
                result["message"] = f"Недостаточно денег для уплаты налога: ${amount}"

        elif action == "chance_card" or action == "chest_card":
            card = action_result.get("card")
            if card:
                card_result = self.apply_card_action(player, card)
                result["message"] = card_result.get("message", "")

        elif action == "go_to_jail":
            player.go_to_jail()
            result["message"] = "Вы отправлены в тюрьму!"

        elif action == "free_parking":
            if self.free_parking_pot > 0:
                amount = self.free_parking_pot
                player.add_money(amount)
                self.free_parking_pot = 0

                result["message"] = f"🎉 Вы получаете все деньги с бесплатной парковки: ${amount}!"
                result["player_money_changed"] = True
                result["amount"] = amount
            else:
                result["message"] = "На бесплатной парковке пока нет денег"

        return result

    def buy_property(self, player: SimplePlayer, position: int) -> bool:
        """Купить собственность на текущей позиции"""
        return self.board.buy_property(player, position)

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
            "applied": True,
            "new_position": None
        }

        action = card.get("action")
        value = card.get("value")

        if action == "move_to":
            if isinstance(value, int):
                player.position = value
                result["new_position"] = value
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
        if not hasattr(game, 'used_colors'):
            game.used_colors = set()
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