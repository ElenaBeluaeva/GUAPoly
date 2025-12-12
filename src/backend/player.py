import random
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field

from config import Config
try:
    from src.backend.board import CellType
except ImportError:
    # Если не удалось импортировать, создаем локальные константы
    class CellType:
        PROPERTY = "property"
        STATION = "station"
        UTILITY = "utility"
        TAX = "tax"
        CHANCE = "chance"
        CHEST = "chest"
        JAIL = "jail"
        GO_TO_JAIL = "go_to_jail"
        FREE_PARKING = "free_parking"
        GO = "go"
        OTHER = "other"


class PlayerStatus(Enum):
    ACTIVE = "active"
    BANKRUPT = "bankrupt"
    IN_JAIL = "in_jail"
    JAIL_VISITING = "visiting"


@dataclass
class Player:
    """Полный класс игрока со всеми методами"""
    user_id: int
    username: str
    full_name: str

    # Игровые характеристики
    position: int = 0
    money: int = Config.START_MONEY
    status: PlayerStatus = PlayerStatus.ACTIVE
    properties: List[int] = field(default_factory=list)
    stations: List[int] = field(default_factory=list)
    utilities: List[int] = field(default_factory=list)
    jail_turns: int = 0
    get_out_of_jail_cards: int = 0
    color: str = field(default_factory=lambda: random.choice(Config.PLAYER_COLORS))
    double_count: int = 0

    # Торговля
    trade_offers: Dict[int, Dict] = field(default_factory=dict)
    trade_proposals: Dict[int, Dict] = field(default_factory=dict)

    # Статистика
    total_rent_paid: int = 0
    total_rent_received: int = 0
    properties_bought: int = 0
    houses_built: int = 0
    hotels_built: int = 0

    # Для аукционов
    auction_bids: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not self.color:
            self.color = random.choice(Config.PLAYER_COLORS)

    def add_money(self, amount: int) -> bool:
        """Добавить деньги игроку"""
        self.money += amount
        return True

    def deduct_money(self, amount: int) -> bool:
        """Списать деньги"""
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    def can_afford(self, amount: int) -> bool:
        """Проверить, может ли игрок заплатить"""
        return self.money >= amount

    def go_to_jail(self):
        """Отправить игрока в тюрьму"""
        self.position = 10
        self.status = PlayerStatus.IN_JAIL
        self.jail_turns = 0

    def release_from_jail(self):
        self.in_jail = False
        self.jail_turns = 0
        self.jail_attempts = 0
        self.status = PlayerStatus.ACTIVE

    def is_bankrupt(self) -> bool:
        """Проверить банкротство"""
        return self.status == PlayerStatus.BANKRUPT or self.money < 0

    # Методы для торговли
    def create_trade_offer(self, target_player_id: int, offer: Dict):
        """Создать предложение обмена"""
        self.trade_offers[target_player_id] = offer

    def receive_trade_proposal(self, from_player_id: int, proposal: Dict):
        """Получить предложение обмена"""
        self.trade_proposals[from_player_id] = proposal

    def accept_trade(self, from_player_id: int) -> bool:
        """Принять предложение обмена"""
        if from_player_id in self.trade_proposals:
            proposal = self.trade_proposals.pop(from_player_id)
            # Здесь будет логика применения обмена
            return True
        return False

    def reject_trade(self, from_player_id: int):
        """Отклонить предложение обмена"""
        self.trade_proposals.pop(from_player_id, None)

    # Методы для аукционов
    def place_bid(self, game_id: str, amount: int) -> bool:
        """Сделать ставку на аукционе"""
        if self.can_afford(amount):
            self.auction_bids[game_id] = amount
            return True
        return False

    def clear_bid(self, game_id: str):
        """Очистить ставку"""
        self.auction_bids.pop(game_id, None)

    # Методы для статистики
    def add_rent_paid(self, amount: int):
        """Добавить в статистику уплаченную ренту"""
        self.total_rent_paid += amount

    def add_rent_received(self, amount: int):
        """Добавить в статистику полученную ренту"""
        self.total_rent_received += amount

    def increment_properties_bought(self):
        """Увеличить счетчик купленных свойств"""
        self.properties_bought += 1

    def increment_houses_built(self):
        """Увеличить счетчик построенных домов"""
        self.houses_built += 1

    def increment_hotels_built(self):
        """Увеличить счетчик построенных отелей"""
        self.hotels_built += 1

    def get_net_worth(self, board) -> int:
        """Рассчитать общую стоимость активов"""
        total = self.money

        # Добавить стоимость недвижимости
        for prop_id in self.properties:
            cell = board.get_cell(prop_id)
            if hasattr(cell, 'price'):
                total += cell.price
                # Добавить стоимость домов/отелей
                if hasattr(cell, 'houses') and cell.houses > 0:
                    total += getattr(cell, 'house_price', 50) * cell.houses

        # Добавить стоимость вокзалов и предприятий
        for station_id in self.stations:
            cell = board.get_cell(station_id)
            if hasattr(cell, 'price'):
                total += cell.price

        for util_id in self.utilities:
            cell = board.get_cell(util_id)
            if hasattr(cell, 'price'):
                total += cell.price

        return total

    def to_dict(self) -> Dict:
        """Конвертировать в словарь для сохранения"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "position": self.position,
            "money": self.money,
            "status": self.status.value,
            "properties": self.properties,
            "stations": self.stations,
            "utilities": self.utilities,
            "jail_turns": self.jail_turns,
            "get_out_of_jail_cards": self.get_out_of_jail_cards,
            "color": self.color,
            "double_count": self.double_count,
        }

    def get_available_properties_for_trade(self, game_board) -> list:
        """Получить доступные для торговли свойства"""
        available = []

        # Улицы
        for prop_id in self.properties:
            cell = game_board.get_cell(prop_id)
            if cell and not getattr(cell, 'mortgaged', False):
                # Проверяем, нет ли построенных домов
                if getattr(cell, 'houses', 0) == 0 and not getattr(cell, 'hotel', False):
                    available.append({
                        'type': 'property',
                        'id': prop_id,
                        'name': cell.name,
                        'value': cell.price,
                        'color_group': getattr(cell, 'color_group', None)
                    })

        # Вокзалы
        for station_id in self.stations:
            cell = game_board.get_cell(station_id)
            if cell and not getattr(cell, 'mortgaged', False):
                available.append({
                    'type': 'station',
                    'id': station_id,
                    'name': cell.name,
                    'value': cell.price
                })

        # Предприятия
        for util_id in self.utilities:
            cell = game_board.get_cell(util_id)
            if cell and not getattr(cell, 'mortgaged', False):
                available.append({
                    'type': 'utility',
                    'id': util_id,
                    'name': cell.name,
                    'value': cell.price
                })

        return available

    def can_trade_property(self, property_id: int, game_board) -> bool:
        """Можно ли торговать этой собственностью"""
        cell = game_board.get_cell(property_id)
        if not cell:
            return False

        # Проверяем, что собственность принадлежит игроку
        if getattr(cell, 'owner_id', None) != self.user_id:
            return False

        # Проверяем, что не заложена
        if getattr(cell, 'mortgaged', False):
            return False

        # Для улиц: проверяем, что нет домов
        if cell.type == CellType.PROPERTY:
            if getattr(cell, 'houses', 0) > 0 or getattr(cell, 'hotel', False):
                return False

        return True
    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        """Создать игрока из словаря"""
        from config import Config

        player = cls(
            user_id=data["user_id"],
            username=data["username"],
            full_name=data["full_name"]
        )

        player.position = data.get("position", 0)
        player.money = data.get("money", Config.START_MONEY)
        player.status = PlayerStatus(data.get("status", "active"))
        player.properties = data.get("properties", [])
        player.stations = data.get("stations", [])
        player.utilities = data.get("utilities", [])
        player.jail_turns = data.get("jail_turns", 0)
        player.get_out_of_jail_cards = data.get("get_out_of_jail_cards", 0)
        player.color = data.get("color", random.choice(Config.PLAYER_COLORS))
        player.double_count = data.get("double_count", 0)

        return player