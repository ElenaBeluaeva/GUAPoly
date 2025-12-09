from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import random


class CellType(Enum):
    PROPERTY = "property"
    STATION = "station"
    UTILITY = "utility"
    CHANCE = "chance"
    CHEST = "chest"
    TAX = "tax"
    JAIL = "jail"
    GO_TO_JAIL = "go_to_jail"
    FREE_PARKING = "free_parking"
    GO = "go"


@dataclass
class BoardCell:
    """Базовый класс клетки"""
    id: int
    name: str
    type: CellType
    description: str = ""
    price: int = 0
    owner_id: Optional[int] = None
    mortgaged: bool = False

    def get_rent(self, dice_roll: int = 0, owner_assets: Dict = None) -> int:
        """Получить стоимость ренты"""
        return 0


@dataclass
class PropertyCell(BoardCell):
    """Клетка улицы (недвижимость)"""
    color_group: str = ""
    house_price: int = 0
    hotel_price: int = 0
    rent: List[int] = field(default_factory=list)
    houses: int = 0
    hotel: bool = False

    def __post_init__(self):
        self.type = CellType.PROPERTY

    def get_rent(self, dice_roll: int = 0, owner_assets: Dict = None) -> int:
        if not self.owner_id or self.mortgaged:
            return 0

        if self.hotel:
            return self.rent[5] if len(self.rent) > 5 else self.rent[-1]
        elif self.houses > 0:
            return self.rent[self.houses] if self.houses < len(self.rent) else self.rent[-1]
        else:
            # Если владелец имеет все улицы группы цветов, рента удваивается
            if owner_assets and len(owner_assets.get(self.color_group, [])) == self._get_group_size():
                return self.rent[0] * 2
            return self.rent[0]

    def _get_group_size(self) -> int:
        """Получить размер группы цветов"""
        group_sizes = {
            "brown": 2, "light_blue": 3, "pink": 3, "orange": 3,
            "red": 3, "yellow": 3, "green": 3, "dark_blue": 2
        }
        return group_sizes.get(self.color_group, 2)

    def can_build_house(self, owner_properties: Dict[str, List]) -> bool:
        """Можно ли построить дом"""
        if self.mortgaged or self.hotel:
            return False

        # Проверка владения всей группой
        group_props = owner_properties.get(self.color_group, [])
        if len(group_props) != self._get_group_size():
            return False

        # Проверка равномерности застройки
        group_houses = [prop.houses for prop in group_props if hasattr(prop, 'houses')]
        if not group_houses:
            return False

        min_houses = min(group_houses)
        return self.houses <= min_houses and self.houses < 5

    def build_house(self) -> bool:
        """Построить дом"""
        if self.houses < 4:
            self.houses += 1
            return True
        elif self.houses == 4 and not self.hotel:
            self.houses = 0
            self.hotel = True
            return True
        return False

    def sell_house(self) -> bool:
        """Продать дом"""
        if self.hotel:
            self.hotel = False
            self.houses = 4
            return True
        elif self.houses > 0:
            self.houses -= 1
            return True
        return False


@dataclass
class StationCell(BoardCell):
    """Клетка вокзала"""

    def __post_init__(self):
        self.type = CellType.STATION
        self.price = 200

    def get_rent(self, dice_roll: int = 0, owner_assets: Dict = None) -> int:
        if not self.owner_id or self.mortgaged:
            return 0

        # Рента зависит от количества вокзалов у владельца
        station_count = len(owner_assets.get('stations', [])) if owner_assets else 1
        rents = [25, 50, 100, 200]
        return rents[min(station_count - 1, 3)]


@dataclass
class UtilityCell(BoardCell):
    """Клетка коммунального предприятия"""

    def __post_init__(self):
        self.type = CellType.UTILITY
        self.price = 150

    def get_rent(self, dice_roll: int = 0, owner_assets: Dict = None) -> int:
        if not self.owner_id or self.mortgaged:
            return 0

        # Рента = множитель × результат броска кубиков
        util_count = len(owner_assets.get('utilities', [])) if owner_assets else 1
        multiplier = 4 if util_count == 1 else 10
        return dice_roll * multiplier


class Board:
    """Полное игровое поле"""

    def __init__(self):
        self.cells: List[BoardCell] = []
        self._init_board()

    def _init_board(self):
        """Инициализация поля Монополии"""
        self.cells = [
            BoardCell(0, "Старт", CellType.GO, "Получите 200$ при прохождении"),

            PropertyCell(1, "Старая дорога", "brown", 60, 50, 50, [2, 10, 30, 90, 160, 250]),
            BoardCell(2, "Казна", CellType.CHEST),
            PropertyCell(3, "Белый переулок", "brown", 60, 50, 50, [4, 20, 60, 180, 320, 450]),
            BoardCell(4, "Подоходный налог", CellType.TAX, "Заплатите 200$", 200),
            StationCell(5, "Курский вокзал"),

            PropertyCell(6, "Сенная площадь", "light_blue", 100, 50, 50, [6, 30, 90, 270, 400, 550]),
            BoardCell(7, "Шанс", CellType.CHANCE),
            PropertyCell(8, "Пушкинская улица", "light_blue", 100, 50, 50, [6, 30, 90, 270, 400, 550]),
            PropertyCell(9, "Гоголевский бульвар", "light_blue", 120, 50, 50, [8, 40, 100, 300, 450, 600]),

            BoardCell(10, "Тюрьма", CellType.JAIL, "Просто посещение"),

            PropertyCell(11, "Смоленский рынок", "pink", 140, 100, 100, [10, 50, 150, 450, 625, 750]),
            UtilityCell(12, "Электростанция"),
            PropertyCell(13, "Манежная площадь", "pink", 140, 100, 100, [10, 50, 150, 450, 625, 750]),
            PropertyCell(14, "Тверская улица", "pink", 160, 100, 100, [12, 60, 180, 500, 700, 900]),
            StationCell(15, "Белорусский вокзал"),

            PropertyCell(16, "Патриаршие пруды", "orange", 180, 100, 100, [14, 70, 200, 550, 750, 950]),
            BoardCell(17, "Казна", CellType.CHEST),
            PropertyCell(18, "Столешников переулок", "orange", 180, 100, 100, [14, 70, 200, 550, 750, 950]),
            PropertyCell(19, "Кузнецкий мост", "orange", 200, 100, 100, [16, 80, 220, 600, 800, 1000]),

            BoardCell(20, "Бесплатная стоянка", CellType.FREE_PARKING),

            PropertyCell(21, "Улица Кирова", "red", 220, 150, 150, [18, 90, 250, 700, 875, 1050]),
            BoardCell(22, "Шанс", CellType.CHANCE),
            PropertyCell(23, "Театральный проезд", "red", 220, 150, 150, [18, 90, 250, 700, 875, 1050]),
            PropertyCell(24, "Лубянская площадь", "red", 240, 150, 150, [20, 100, 300, 750, 925, 1100]),
            StationCell(25, "Казанский вокзал"),

            PropertyCell(26, "Комсомольская площадь", "yellow", 260, 150, 150, [22, 110, 330, 800, 975, 1150]),
            PropertyCell(27, "Сретенский бульвар", "yellow", 260, 150, 150, [22, 110, 330, 800, 975, 1150]),
            UtilityCell(28, "Водопровод"),
            PropertyCell(29, "Рождественка", "yellow", 280, 150, 150, [24, 120, 360, 850, 1025, 1200]),

            BoardCell(30, "Отправляйтесь в тюрьму", CellType.GO_TO_JAIL),

            PropertyCell(31, "Проспект Маркса", "green", 300, 200, 200, [26, 130, 390, 900, 1100, 1275]),
            PropertyCell(32, "Улица Горького", "green", 300, 200, 200, [26, 130, 390, 900, 1100, 1275]),
            BoardCell(33, "Казна", CellType.CHEST),
            PropertyCell(34, "Маяковская площадь", "green", 320, 200, 200, [28, 150, 450, 1000, 1200, 1400]),
            StationCell(35, "Киевский вокзал"),

            BoardCell(36, "Шанс", CellType.CHANCE),
            PropertyCell(37, "Арбат", "dark_blue", 350, 200, 200, [35, 175, 500, 1100, 1300, 1500]),
            BoardCell(38, "Налог на роскошь", CellType.TAX, "Заплатите 100$", 100),
            PropertyCell(39, "Грузинский вал", "dark_blue", 400, 200, 200, [50, 200, 600, 1400, 1700, 2000])
        ]

    def get_cell(self, position: int) -> BoardCell:
        """Получить клетку по позиции"""
        return self.cells[position % len(self.cells)]

    def get_property_cells(self) -> List[PropertyCell]:
        """Получить все клетки недвижимости"""
        return [cell for cell in self.cells if isinstance(cell, PropertyCell)]

    def get_station_cells(self) -> List[StationCell]:
        """Получить все вокзалы"""
        return [cell for cell in self.cells if isinstance(cell, StationCell)]

    def get_utility_cells(self) -> List[UtilityCell]:
        """Получить все предприятия"""
        return [cell for cell in self.cells if isinstance(cell, UtilityCell)]

    def get_owner_assets(self, owner_id: int) -> Dict[str, List]:
        """Получить активы владельца по категориям"""
        assets = {
            'properties': [],
            'stations': [],
            'utilities': []
        }

        for cell in self.cells:
            if hasattr(cell, 'owner_id') and cell.owner_id == owner_id:
                if isinstance(cell, PropertyCell):
                    if cell.color_group not in assets:
                        assets[cell.color_group] = []
                    assets[cell.color_group].append(cell)
                    assets['properties'].append(cell)
                elif isinstance(cell, StationCell):
                    assets['stations'].append(cell)
                elif isinstance(cell, UtilityCell):
                    assets['utilities'].append(cell)

        return assets

    def can_build_on_property(self, property_id: int, owner_id: int) -> bool:
        """Можно ли строить на недвижимости"""
        cell = self.get_cell(property_id)
        if not isinstance(cell, PropertyCell):
            return False

        owner_assets = self.get_owner_assets(owner_id)
        return cell.can_build_house(owner_assets)

    def buy_property(self, player, position: int) -> bool:
        """Купить собственность"""
        cell = self.get_cell(position)

        if not hasattr(cell, 'price') or cell.price == 0:
            return False

        if cell.owner_id is not None:
            return False

        if player.money < cell.price:
            return False

        # Списание денег
        player.deduct_money(cell.price)

        # Назначение владельца
        cell.owner_id = player.user_id

        # Добавление в список собственности игрока
        if isinstance(cell, PropertyCell):
            player.properties.append(position)
        elif isinstance(cell, StationCell):
            player.stations.append(position)
        elif isinstance(cell, UtilityCell):
            player.utilities.append(position)

        player.increment_properties_bought()
        return True

    def mortgage_property(self, position: int) -> bool:
        """Заложить собственность"""
        cell = self.get_cell(position)

        if not hasattr(cell, 'owner_id') or cell.owner_id is None:
            return False

        if cell.mortgaged:
            return False

        cell.mortgaged = True
        return True

    def unmortgage_property(self, position: int) -> bool:
        """Снять залог с собственности"""
        cell = self.get_cell(position)

        if not hasattr(cell, 'owner_id') or cell.owner_id is None:
            return False

        if not cell.mortgaged:
            return False

        cell.mortgaged = False
        return True

    def get_rent_for_cell(self, position: int, dice_roll: int = 0, owner_id: int = None) -> int:
        """Получить ренту для клетки"""
        cell = self.get_cell(position)

        if not hasattr(cell, 'owner_id') or cell.owner_id is None:
            return 0

        owner_assets = self.get_owner_assets(cell.owner_id) if owner_id is None else self.get_owner_assets(owner_id)
        return cell.get_rent(dice_roll, owner_assets)