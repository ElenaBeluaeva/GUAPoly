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
from src.backend.trade_manager import TradeManager
from datetime import datetime, timedelta

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
    JAIL_FINE = 200
    MIN_AUCTION_BID = 10

    # Карточки Шанс
    CHANCE_CARDS = [
        {"text": "Отправляйтесь на клетку 'Старт'", "action": "move_to", "value": 0},
        {"text": "Вы ничего не делали весь семестр и теперь отправляетесь на комиссию", "action": "go_to_jail"},
        {"text": "Получите стипендию 50₽", "action": "add_money", "value": 50},
        {"text": "Заплатите 15₽ за обед в столовой", "action": "deduct_money", "value": 15},
        {"text": "У вас перезачет по предмету, вы можете избежать комиссию, использовав освобождение", "action": "get_out_of_jail"},
        {"text": "Вас оштрафовали за чрезмерные пропуски пар. Заплатите 15₽", "action": "deduct_money", "value": 15},
        {"text": "Вы заняли первое место в конкурсе лучший профорг. Получите 10₽", "action": "add_money", "value": 10},
        {"text": "Оплатите обучение за семестр 150₽", "action": "deduct_money", "value": 150},
    ]

    # Карточки Казна
    CHEST_CARDS = [
        {"text": "Вы выиграли конкурс 'молодёжные лица ГУАП'. Получите 20₽", "action": "add_money", "value": 20},
        {"text": "Оплатите налог на образование 100₽", "action": "deduct_money", "value": 100},
        {"text": "Вы выиграли стипендию профкома получите 100₽", "action": "add_money", "value": 100},
        {"text": "Вы не понравились преподавателю. Отправляйтесь на комиссию. Не проходите через 'Старт'", "action": "go_to_jail"},
        {"text": "ГУАП выдает вам мат.помощь получи 50₽", "action": "add_money", "value": 50},
        {"text": "Вы выиграли грантовую поддержку получите 20₽", "action": "add_money", "value": 20},
        {"text": "Освобождение от комиссии", "action": "get_out_of_jail"},
        {"text": "Оплатите проживание в общежитии 100₽", "action": "deduct_money", "value": 100},
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
        self.jail_attempts = 0
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
        """Отправить игрока в тюрьму"""  # Добавлен docstring
        self.position = 10
        self.in_jail = True
        self.jail_turns = 0
        self.jail_attempts = 0  # <-- ДОБАВЛЕНО
        self.status = PlayerStatus.IN_JAIL

    def skip_jail_attempt(self):
        """Пропустить попытку выхода из тюрьмы"""
        self.jail_turns += 1

        # Проверяем, не отсидел ли уже 3 хода
        if self.jail_turns >= 3:
            self.in_jail = False
            self.jail_turns = 0
            self.jail_attempts = 0
            self.status = PlayerStatus.ACTIVE
            return True  # Освобожден
        return False

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
        from src.backend.trade_manager import TradeManager
        self.trade_manager = TradeManager()

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
        """Передает ход следующему игроку"""
        if not self.player_order:
            return None

        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.turn_count += 1

        # Возвращаем нового текущего игрока
        return self.get_current_player()

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

    def save_state(self):
        """Сохранить состояние игры (для торговли)"""
        try:
            if hasattr(self, 'game_id'):
                # Импортируем game_manager
                from src.backend.game_manager import game_manager
                if hasattr(game_manager, 'save_game_state'):
                    game_manager.save_game_state(self.game_id)
                    print(f"✅ Состояние игры {self.game_id} сохранено")
                else:
                    # Резервный метод сохранения
                    import json
                    import os
                    game_data = self.to_dict()
                    filename = f"data/game_{self.game_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(game_data, f, ensure_ascii=False, indent=2)
                    print(f"✅ Игра {self.game_id} сохранена в файл {filename}")
        except Exception as e:
            print(f"❌ Ошибка сохранения состояния игры {self.game_id}: {e}")
            import traceback
            traceback.print_exc()

    def can_trade_with(self, from_player_id: int, to_player_id: int) -> bool:
        """Проверить, может ли игрок торговать с другим игроком"""
        if from_player_id not in self.players or to_player_id not in self.players:
            return False

        if from_player_id == to_player_id:
            return False

        from_player = self.players[from_player_id]
        to_player = self.players[to_player_id]

        # Оба игрока должны быть активны
        if from_player.status != PlayerStatus.ACTIVE or to_player.status != PlayerStatus.ACTIVE:
            return False

        # Оба игрока не должны быть в тюрьме
        if from_player.in_jail or to_player.in_jail:
            return False

        return True

    # def accept_trade(self, trade_id: str, player_id: int) -> dict:
    #     """Принять сделку"""
    #     if not hasattr(self, 'active_trades') or trade_id not in self.active_trades:
    #         return {"success": False, "error": "Предложение не найдено"}
    #
    #     trade = self.active_trades[trade_id]
    #
    #     # Проверяем, что игрок принимает правильное предложение
    #     if trade['to_player'] != player_id:
    #         return {"success": False, "error": "Это предложение не для вас"}
    #
    #     if trade['status'] != 'pending':
    #         return {"success": False, "error": "Предложение уже обработано"}
    #
    #     if datetime.now() > trade['expires_at']:
    #         return {"success": False, "error": "Предложение истекло"}
    #
    #     # Получаем игроков
    #     from_player = self.players[trade['from_player']]
    #     to_player = self.players[trade['to_player']]
    #
    #     # Проверяем еще раз условия
    #     # Предложение от from_player
    #     if 'money' in trade['offer'] and trade['offer']['money'] > 0:
    #         if from_player.money < trade['offer']['money']:
    #             return {"success": False, "error": "У предлагающего недостаточно денег"}
    #
    #     if 'properties' in trade['offer']:
    #         for prop_id in trade['offer']['properties']:
    #             if not from_player.can_trade_property(prop_id, self.board):
    #                 return {"success": False, "error": f"Собственность {prop_id} больше нельзя обменять"}
    #
    #     # Запрос к to_player
    #     if 'money' in trade['request'] and trade['request']['money'] > 0:
    #         if to_player.money < trade['request']['money']:
    #             return {"success": False, "error": "У вас недостаточно денег"}
    #
    #     if 'properties' in trade['request']:
    #         for prop_id in trade['request']['properties']:
    #             if not to_player.can_trade_property(prop_id, self.board):
    #                 return {"success": False, "error": f"Собственность {prop_id} больше нельзя отдать"}
    #
    #     # Выполняем обмен
    #     try:
    #         # Деньги от from_player к to_player
    #         if 'money' in trade['offer'] and trade['offer']['money'] > 0:
    #             from_player.deduct_money(trade['offer']['money'])
    #             to_player.add_money(trade['offer']['money'])
    #
    #         # Деньги от to_player к from_player
    #         if 'money' in trade['request'] and trade['request']['money'] > 0:
    #             to_player.deduct_money(trade['request']['money'])
    #             from_player.add_money(trade['request']['money'])
    #
    #         # Собственность от from_player к to_player
    #         if 'properties' in trade['offer']:
    #             for prop_id in trade['offer']['properties']:
    #                 cell = self.board.get_cell(prop_id)
    #                 if cell:
    #                     # Удаляем у from_player
    #                     if cell.type == CellType.PROPERTY:
    #                         if prop_id in from_player.properties:
    #                             from_player.properties.remove(prop_id)
    #                             to_player.properties.append(prop_id)
    #                     elif cell.type == CellType.STATION:
    #                         if prop_id in from_player.stations:
    #                             from_player.stations.remove(prop_id)
    #                             to_player.stations.append(prop_id)
    #                     elif cell.type == CellType.UTILITY:
    #                         if prop_id in from_player.utilities:
    #                             from_player.utilities.remove(prop_id)
    #                             to_player.utilities.append(prop_id)
    #
    #                     # Меняем владельца на клетке
    #                     cell.owner_id = to_player.user_id
    #
    #         # Собственность от to_player к from_player
    #         if 'properties' in trade['request']:
    #             for prop_id in trade['request']['properties']:
    #                 cell = self.board.get_cell(prop_id)
    #                 if cell:
    #                     # Удаляем у to_player
    #                     if cell.type == CellType.PROPERTY:
    #                         if prop_id in to_player.properties:
    #                             to_player.properties.remove(prop_id)
    #                             from_player.properties.append(prop_id)
    #                     elif cell.type == CellType.STATION:
    #                         if prop_id in to_player.stations:
    #                             to_player.stations.remove(prop_id)
    #                             from_player.stations.append(prop_id)
    #                     elif cell.type == CellType.UTILITY:
    #                         if prop_id in to_player.utilities:
    #                             to_player.utilities.remove(prop_id)
    #                             from_player.utilities.append(prop_id)
    #
    #                     # Меняем владельца на клетке
    #                     cell.owner_id = from_player.user_id
    #
    #         # Обновляем статус предложения
    #         trade['status'] = 'accepted'
    #         trade['accepted_at'] = datetime.now()
    #
    #         # Удаляем из активных
    #         del self.active_trades[trade_id]
    #
    #         # Добавляем в историю
    #         if not hasattr(self, 'trade_history'):
    #             self.trade_history = []
    #         self.trade_history.append(trade)
    #
    #         return {
    #             "success": True,
    #             "message": "Сделка успешно завершена!"
    #         }
    #
    #     except Exception as e:
    #         return {"success": False, "error": f"Ошибка при выполнении сделки: {str(e)}"}

    def reject_trade(self, trade_id: str, player_id: int) -> dict:
        """Отклонить сделку"""
        if not hasattr(self, 'active_trades') or trade_id not in self.active_trades:
            return {"success": False, "error": "Предложение не найдено"}

        trade = self.active_trades[trade_id]

        # Проверяем, что игрок отклоняет правильное предложение
        if trade['to_player'] != player_id:
            return {"success": False, "error": "Это предложение не для вас"}

        if trade['status'] != 'pending':
            return {"success": False, "error": "Предложение уже обработано"}

        # Обновляем статус
        trade['status'] = 'rejected'
        trade['rejected_at'] = datetime.now()

        # Удаляем из активных
        del self.active_trades[trade_id]

        return {
            "success": True,
            "message": "Вы отклонили предложение"
        }

    def cancel_trade(self, trade_id: str, player_id: int) -> dict:
        """Отменить предложение сделки"""
        if not hasattr(self, 'active_trades') or trade_id not in self.active_trades:
            return {"success": False, "error": "Предложение не найдено"}

        trade = self.active_trades[trade_id]

        # Проверяем, что игрок отменяет свое предложение
        if trade['from_player'] != player_id:
            return {"success": False, "error": "Вы не можете отменить чужое предложение"}

        if trade['status'] != 'pending':
            return {"success": False, "error": "Предложение уже обработано"}

        # Обновляем статус
        trade['status'] = 'cancelled'
        trade['cancelled_at'] = datetime.now()

        # Удаляем из активных
        del self.active_trades[trade_id]

        return {
            "success": True,
            "message": "Предложение отменено"
        }

    def get_player_trades(self, player_id: int) -> list:
        """Получить активные предложения для игрока"""
        if not hasattr(self, 'active_trades'):
            return []

        player_trades = []
        for trade_id, trade in self.active_trades.items():
            if trade['status'] == 'pending' and (
                    trade['from_player'] == player_id or
                    trade['to_player'] == player_id
            ):
                player_trades.append(trade)

        return player_trades

        # Здесь НИЧЕГО не должно быть на этом уровне отступа!
        # Следующий метод начинается с отступа в 4 пробела

    def some_other_method(self):
        pass

    def propose_trade(self, from_player_id: int, to_player_id: int,
                      offer: dict, request: dict) -> dict:
        """Предложить сделку - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            if from_player_id not in self.players or to_player_id not in self.players:
                return {"success": False, "error": "Игрок не найден"}

            if from_player_id == to_player_id:
                return {"success": False, "error": "Нельзя торговать с самим собой"}

            from_player = self.players[from_player_id]
            to_player = self.players[to_player_id]

            # Проверяем статус игроков (более безопасная проверка)
            from_player_status = getattr(from_player, 'status', None)
            to_player_status = getattr(to_player, 'status', None)

            # Проверяем статус разными способами
            is_from_active = False
            is_to_active = False

            if hasattr(from_player_status, 'value'):
                is_from_active = from_player_status.value == 'active'
            elif isinstance(from_player_status, str):
                is_from_active = from_player_status == 'active'
            elif from_player_status is None:
                # Если статус не установлен, считаем активным
                is_from_active = True

            if hasattr(to_player_status, 'value'):
                is_to_active = to_player_status.value == 'active'
            elif isinstance(to_player_status, str):
                is_to_active = to_player_status == 'active'
            elif to_player_status is None:
                is_to_active = True

            if not is_from_active or not is_to_active:
                return {"success": False, "error": "Игрок неактивен"}

            # Проверяем тюрьму
            if getattr(from_player, 'in_jail', False) or getattr(to_player, 'in_jail', False):
                return {"success": False, "error": "Игрок в тюрьме"}

            # Проверяем предложение
            if 'money' in offer and offer['money'] > 0:
                if from_player.money < offer['money']:
                    return {"success": False, "error": "Недостаточно денег для предложения"}

            # Проверяем запрос
            if 'money' in request and request['money'] > 0:
                if to_player.money < request['money']:
                    return {"success": False, "error": "У другого игрока недостаточно денег"}

            # ПРОВЕРКА СОБСТВЕННОСТИ
            # Проверяем, что предлагаемая собственность принадлежит игроку
            if 'properties' in offer:
                for prop_id in offer['properties']:
                    cell = self.board.get_cell(prop_id)
                    if not cell:
                        return {"success": False, "error": f"Собственность {prop_id} не найдена"}
                    if cell.owner_id != from_player_id:
                        return {"success": False, "error": f"Собственность {prop_id} вам не принадлежит"}
                    # Проверяем, не заложена ли собственность
                    if hasattr(cell, 'mortgaged') and cell.mortgaged:
                        return {"success": False, "error": f"Собственность {prop_id} в залоге"}

            # Проверяем, что запрашиваемая собственность принадлежит другому игроку
            if 'properties' in request:
                for prop_id in request['properties']:
                    cell = self.board.get_cell(prop_id)
                    if not cell:
                        return {"success": False, "error": f"Собственность {prop_id} не найдена"}
                    if cell.owner_id != to_player_id:
                        return {"success": False, "error": f"Собственность {prop_id} не принадлежит игроку"}
                    # Проверяем, не заложена ли собственность
                    if hasattr(cell, 'mortgaged') and cell.mortgaged:
                        return {"success": False, "error": f"Собственность {prop_id} в залоге"}

            # Используем TradeManager для создания предложения
            if hasattr(self.trade_manager, 'create_trade_offer'):
                # Если метод называется create_trade_offer
                trade_id = self.trade_manager.create_trade_offer(
                    from_player_id=from_player_id,
                    to_player_id=to_player_id,
                    offer=offer,
                    request=request,
                    game_id=self.game_id
                )
            elif hasattr(self.trade_manager, 'create_trade'):
                # Если метод называется create_trade
                trade_id = self.trade_manager.create_trade(
                    from_player_id=from_player_id,
                    to_player_id=to_player_id,
                    offer=offer,
                    request=request
                )
            else:
                # Резервный метод создания
                import uuid
                from datetime import datetime, timedelta
                trade_id = f"trade_{from_player_id}_{to_player_id}_{uuid.uuid4().hex[:8]}"

                if not hasattr(self.trade_manager, 'active_trades'):
                    self.trade_manager.active_trades = {}

                self.trade_manager.active_trades[trade_id] = {
                    'trade_id': trade_id,
                    'from_player_id': from_player_id,
                    'to_player_id': to_player_id,
                    'offer': offer,
                    'request': request,
                    'status': 'pending',
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(minutes=5)
                }

            if trade_id:
                print(f"✅ Предложение создано: {trade_id}")
                print(f"   От: {from_player.full_name} (ID: {from_player_id})")
                print(f"   Кому: {to_player.full_name} (ID: {to_player_id})")
                print(f"   Предложение: {offer}")
                print(f"   Запрос: {request}")

                # Сохраняем состояние игры
                if hasattr(self, 'save_state'):
                    self.save_state()
                elif hasattr(self, 'game_id'):
                    # Используем game_manager если есть
                    from src.backend.game_manager import game_manager
                    if hasattr(game_manager, 'save_game_state'):
                        game_manager.save_game_state(self.game_id)

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "message": "Предложение отправлено"
                }
            else:
                return {"success": False, "error": "Не удалось создать предложение"}

        except Exception as e:
            print(f"❌ Ошибка в propose_trade: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Системная ошибка: {str(e)}"}

    def accept_trade(self, trade_id: str, player_id: int) -> dict:
        """Принять сделку - РАБОЧАЯ ВЕРСИЯ С ОБМЕНОМ СОБСТВЕННОСТИ"""
        print(f"\n🎯 ========== ACCEPT_TRADE CALLED ==========")
        print(f"📊 trade_id: {trade_id}")
        print(f"👤 player_id: {player_id}")

        # Проверяем TradeManager
        if not hasattr(self, 'trade_manager'):
            print("❌ ERROR: Нет trade_manager в игре")
            return {"success": False, "error": "Системная ошибка торговли"}

        print(f"✅ TradeManager найден")

        # Проверяем, есть ли метод get_trade
        if not hasattr(self.trade_manager, 'get_trade'):
            print("❌ ERROR: У trade_manager нет метода get_trade")
            # Ищем вручную
            if hasattr(self.trade_manager, 'active_trades'):
                trade = self.trade_manager.active_trades.get(trade_id)
            else:
                trade = None
        else:
            trade = self.trade_manager.get_trade(trade_id)

        if not trade:
            print(f"❌ ERROR: Предложение {trade_id} не найдено в TradeManager")
            return {"success": False, "error": "Предложение не найдено или истекло"}

        print(f"✅ Предложение найдено:")
        print(f"   От: {trade.from_player_id}")
        print(f"   Кому: {trade.to_player_id}")
        print(f"   Статус: {trade.status}")

        # Проверяем, правильный ли игрок
        if trade.to_player_id != player_id:
            print(f"❌ ERROR: Игрок {player_id} пытается принять предложение для {trade.to_player_id}")
            return {"success": False, "error": "Это предложение не для вас"}

        # Проверяем статус
        if trade.status != "pending":
            print(f"❌ ERROR: Предложение уже обработано, статус: {trade.status}")
            return {"success": False, "error": "Предложение уже обработано"}

        # Проверяем время
        from datetime import datetime
        if datetime.now() > trade.expires_at:
            print(f"❌ ERROR: Предложение истекло в {trade.expires_at}")
            trade.status = "expired"
            if trade_id in self.trade_manager.active_trades:
                del self.trade_manager.active_trades[trade_id]
            if hasattr(self.trade_manager, 'trade_history'):
                self.trade_manager.trade_history.append(trade)
            return {"success": False, "error": "Время предложения истекло"}

        print(f"✅ Все проверки пройдены, выполняем обмен...")

        try:
            # Получаем игроков
            from_player = self.players.get(trade.from_player_id)
            to_player = self.players.get(trade.to_player_id)

            if not from_player or not to_player:
                print(f"❌ ERROR: Не найден игрок: from={trade.from_player_id}, to={trade.to_player_id}")
                return {"success": False, "error": "Один из игроков не найден"}

            # ========== ВЫПОЛНЯЕМ ОБМЕН ДЕНЬГАМИ ==========
            if trade.offer.get('money', 0) > 0:
                print(f"💰 Передача денег от {from_player.full_name} к {to_player.full_name}: ${trade.offer['money']}")
                if not from_player.deduct_money(trade.offer['money']):
                    return {"success": False, "error": f"У {from_player.full_name} недостаточно денег"}
                to_player.add_money(trade.offer['money'])

            if trade.request.get('money', 0) > 0:
                print(f"💰 Передача денег от {to_player.full_name} к {from_player.full_name}: ${trade.request['money']}")
                if not to_player.deduct_money(trade.request['money']):
                    return {"success": False, "error": f"У {to_player.full_name} недостаточно денег"}
                from_player.add_money(trade.request['money'])

            # ========== ВЫПОЛНЯЕМ ОБМЕН СОБСТВЕННОСТЬЮ ==========
            # Предложение: от from_player к to_player
            if trade.offer.get('properties'):
                print(
                    f"🏠 Передача {len(trade.offer['properties'])} свойств от {from_player.full_name} к {to_player.full_name}")
                for prop_id in trade.offer['properties']:
                    cell = self.board.get_cell(prop_id)
                    if cell:
                        print(f"   → Собственность: {getattr(cell, 'name', prop_id)}")

                        # Проверяем, что собственность принадлежит отправителю
                        if cell.owner_id != from_player.user_id:
                            return {"success": False,
                                    "error": f"Собственность {cell.name} не принадлежит {from_player.full_name}"}

                        # Определяем тип клетки и удаляем у отправителя
                        if cell.type == CellType.PROPERTY:
                            if prop_id in from_player.properties:
                                from_player.properties.remove(prop_id)
                                to_player.properties.append(prop_id)
                                print(f"      Улица передана")
                        elif cell.type == CellType.STATION:
                            if prop_id in from_player.stations:
                                from_player.stations.remove(prop_id)
                                to_player.stations.append(prop_id)
                                print(f"      Вокзал передан")
                        elif cell.type == CellType.UTILITY:
                            if prop_id in from_player.utilities:
                                from_player.utilities.remove(prop_id)
                                to_player.utilities.append(prop_id)
                                print(f"      Предприятие передано")

                        # Меняем владельца на клетке
                        cell.owner_id = to_player.user_id
                        print(f"      Владелец изменен на {to_player.full_name}")

            # Запрос: от to_player к from_player
            if trade.request.get('properties'):
                print(
                    f"🏠 Передача {len(trade.request['properties'])} свойств от {to_player.full_name} к {from_player.full_name}")
                for prop_id in trade.request['properties']:
                    cell = self.board.get_cell(prop_id)
                    if cell:
                        print(f"   → Собственность: {getattr(cell, 'name', prop_id)}")

                        # Проверяем, что собственность принадлежит получателю
                        if cell.owner_id != to_player.user_id:
                            return {"success": False,
                                    "error": f"Собственность {cell.name} не принадлежит {to_player.full_name}"}

                        # Определяем тип клетки и удаляем у получателя
                        if cell.type == CellType.PROPERTY:
                            if prop_id in to_player.properties:
                                to_player.properties.remove(prop_id)
                                from_player.properties.append(prop_id)
                                print(f"      Улица передана")
                        elif cell.type == CellType.STATION:
                            if prop_id in to_player.stations:
                                to_player.stations.remove(prop_id)
                                from_player.stations.append(prop_id)
                                print(f"      Вокзал передан")
                        elif cell.type == CellType.UTILITY:
                            if prop_id in to_player.utilities:
                                to_player.utilities.remove(prop_id)
                                from_player.utilities.append(prop_id)
                                print(f"      Предприятие передано")

                        # Меняем владельца на клетке
                        cell.owner_id = from_player.user_id
                        print(f"      Владелец изменен на {from_player.full_name}")

            # ========== ОБНОВЛЯЕМ СТАТУС ==========
            trade.status = "accepted"
            trade.processed_at = datetime.now()
            print(f"✅ Статус предложения изменен на: accepted")

            # Перемещаем в историю
            if hasattr(self.trade_manager, 'trade_history'):
                self.trade_manager.trade_history.append(trade)

            # Удаляем из активных
            if hasattr(self.trade_manager, 'active_trades') and trade_id in self.trade_manager.active_trades:
                del self.trade_manager.active_trades[trade_id]
                print(f"✅ Предложение удалено из активных")

            # Сохраняем состояние игры
            self.save_state()

            print(f"🎉 Сделка успешно завершена!")
            print(f"========================================\n")

            return {
                "success": True,
                "message": "✅ Сделка успешно завершена! Деньги и собственность обменяны."
            }

        except Exception as e:
            print(f"❌ ERROR: Ошибка выполнения сделки: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Ошибка при выполнении: {str(e)}"}

    def reject_trade(self, trade_id: str, player_id: int) -> dict:
        """Отклонить сделку - УПРОЩЕННАЯ ВЕРСИЯ"""
        print(f"\n🎯 ========== REJECT_TRADE CALLED ==========")
        print(f"📊 trade_id: {trade_id}")
        print(f"👤 player_id: {player_id}")

        if not hasattr(self, 'trade_manager'):
            return {"success": False, "error": "Системная ошибка"}

        trade = self.trade_manager.get_trade(trade_id)
        if not trade:
            return {"success": False, "error": "Предложение не найдено"}

        if trade.to_player_id != player_id:
            return {"success": False, "error": "Это предложение не для вас"}

        # Просто меняем статус на отклоненный
        trade.status = "rejected"

        # Удаляем из активных
        if trade_id in self.trade_manager.active_trades:
            del self.trade_manager.active_trades[trade_id]

        # Добавляем в историю
        if hasattr(self.trade_manager, 'trade_history'):
            self.trade_manager.trade_history.append(trade)

        print(f"✅ Предложение отклонено")
        print(f"========================================\n")

        return {
            "success": True,
            "message": "❌ Предложение отклонено"
        }

    def cancel_trade(self, trade_id: str, player_id: int) -> dict:
        """Отменить предложение сделки"""
        return self.trade_manager.cancel_trade(trade_id, player_id)

    # def get_player_trades(self, player_id: int) -> list:
    #     """Получить активные предложения для игрока"""
    #     return self.trade_manager.get_player_trades(player_id)

    def get_player_available_properties(self, player_id: int) -> list:
        """Получить доступные для торговли свойства игрока"""
        player = self.players.get(player_id)
        if not player:
            return []

        available = []

        # Улицы
        for prop_id in player.properties:
            cell = self.board.get_cell(prop_id)
            if cell and not getattr(cell, 'mortgaged', False):
                if getattr(cell, 'houses', 0) == 0 and not getattr(cell, 'hotel', False):
                    available.append({
                        'type': 'property',
                        'id': prop_id,
                        'name': cell.name,
                        'value': cell.price,
                        'color_group': getattr(cell, 'color_group', None)
                    })

        # Вокзалы
        for station_id in player.stations:
            cell = self.board.get_cell(station_id)
            if cell and not getattr(cell, 'mortgaged', False):
                available.append({
                    'type': 'station',
                    'id': station_id,
                    'name': cell.name,
                    'value': cell.price
                })

        # Предприятия
        for util_id in player.utilities:
            cell = self.board.get_cell(util_id)
            if cell and not getattr(cell, 'mortgaged', False):
                available.append({
                    'type': 'utility',
                    'id': util_id,
                    'name': cell.name,
                    'value': cell.price
                })

        return available

    def cleanup_expired_trades(self):
        """Очистить истекшие предложения"""
        self.trade_manager.cleanup_expired_trades()

    @classmethod
    def from_dict(cls, data):
        game = cls(
            game_id=data['game_id'],
            creator_id=data['creator_id'],
            creator_username=data['creator_username'],
            creator_full_name=data['creator_full_name']
        )
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

        if 'trade_manager' in data:
            game.trade_manager.load_state(data['trade_manager'])

        return game