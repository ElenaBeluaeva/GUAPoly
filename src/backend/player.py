from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class PlayerStatus(Enum):
    ACTIVE = "active"
    BANKRUPT = "bankrupt"
    IN_JAIL = "in_jail"
    JAIL_VISITING = "visiting"


@dataclass
class Player:
    """Класс игрока"""
    user_id: int
    username: str
    full_name: str

    # Игровые характеристики
    position: int = 0
    money: int = 1500
    status: PlayerStatus = PlayerStatus.ACTIVE
    properties: List[int] = field(default_factory=list)  # Индексы клеток
    stations: List[int] = field(default_factory=list)  # Вокзалы
    utilities: List[int] = field(default_factory=list)  # Коммунальные предприятия
    jail_turns: int = 0  # Сколько ходов в тюрьме
    get_out_of_jail_cards: int = 0  # Карты "Освобождение из тюрьмы"
    color: str = field(default_factory=lambda: "red")  # Цвет фишки

    # Торговля
    trade_offers: Dict[int, Dict] = field(default_factory=dict)  # Предложения торговли

    def __post_init__(self):
        if not self.color:
            colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "brown"]
            self.color = colors[self.user_id % len(colors)]

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
        self.position = 10  # Позиция тюрьмы
        self.status = PlayerStatus.IN_JAIL
        self.jail_turns = 0

    def release_from_jail(self):
        """Освободить из тюрьмы"""
        self.status = PlayerStatus.ACTIVE
        self.jail_turns = 0

    def is_bankrupt(self) -> bool:
        """Проверить банкротство"""
        return self.status == PlayerStatus.BANKRUPT or self.money < 0

    def get_total_assets(self, board) -> int:
        """Получить общую стоимость активов"""
        total = self.money

        # Добавить стоимость недвижимости
        for prop_id in self.properties:
            cell = board.get_cell(prop_id)
            if hasattr(cell, 'price'):
                total += cell.price
                # Добавить стоимость домов/отелей
                if hasattr(cell, 'houses') and cell.houses > 0:
                    total += cell.house_price * cell.houses

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
