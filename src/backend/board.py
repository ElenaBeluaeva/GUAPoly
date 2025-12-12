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
    houses: int = 0  # <-- ДОБАВЛЕНО
    hotel: bool = False  # <-- ДОБАВЛЕНО

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

            # Коричневые улицы
            PropertyCell(
                id=1,
                name="Дикси",
                type=CellType.PROPERTY,
                color_group="brown",
                price=60,
                house_price=50,
                hotel_price=200,
                rent=[2, 10, 30, 90, 160, 250]
            ),
            BoardCell(2, "Общественная казна", CellType.CHEST),
            PropertyCell(
                id=3,
                name="Красное&белое",
                type=CellType.PROPERTY,
                color_group="brown",
                price=60,
                house_price=50,
                hotel_price=200,
                rent=[4, 20, 60, 180, 320, 450]
            ),
            BoardCell(4, "Взносы МСГ", CellType.TAX, "Заплатите 200$ за проживание", 200),

            # Метро
            StationCell(id=5, name="Ст. метро Московская", type=CellType.STATION),

            # Голубые улицы
            PropertyCell(
                id=6,
                name="Мед. кабинет",
                type=CellType.PROPERTY,
                color_group="light_blue",
                price=100,
                house_price=50,
                hotel_price=250,
                rent=[6, 30, 90, 270, 400, 550]
            ),
            BoardCell(7, "Шанс", CellType.CHANCE),
            PropertyCell(
                id=8,
                name="2 отдел",
                type=CellType.PROPERTY,
                color_group="light_blue",
                price=100,
                house_price=50,
                hotel_price=250,
                rent=[6, 30, 90, 270, 400, 550]
            ),
            PropertyCell(
                id=9,
                name="МФЦ",
                type=CellType.PROPERTY,
                color_group="light_blue",
                price=120,
                house_price=50,
                hotel_price=250,
                rent=[8, 40, 100, 300, 450, 600]
            ),

            # Тюрьма
            BoardCell(10, "Деканат. Просто посещение. Попейте чаек с администрацией", CellType.JAIL, "Просто посещение"),

            # Розовые улицы
            PropertyCell(
                id=11,
                name="Исаакиевский сквер",
                type=CellType.PROPERTY,
                color_group="pink",
                price=140,
                house_price=100,
                hotel_price=300,
                rent=[10, 50, 150, 450, 625, 750]
            ),
            UtilityCell(id=12, name="Чесменская церковь", type=CellType.UTILITY),
            PropertyCell(
                id=13,
                name="Парк 300-летия",
                type=CellType.PROPERTY,
                color_group="pink",
                price=140,
                house_price=100,
                hotel_price=300,
                rent=[10, 50, 150, 450, 625, 750]
            ),
            PropertyCell(
                id=14,
                name="Новая Голландия",
                type=CellType.PROPERTY,
                color_group="pink",
                price=160,
                house_price=100,
                hotel_price=300,
                rent=[12, 60, 180, 500, 700, 900]
            ),
            StationCell(id=15, name="Ст. метро Театральная", type=CellType.STATION),

            # Оранжевые улицы
            PropertyCell(
                id=16,
                name="Варшавская",
                type=CellType.PROPERTY,
                color_group="orange",
                price=180,
                house_price=100,
                hotel_price=400,
                rent=[14, 70, 200, 550, 750, 950]
            ),
            BoardCell(17, "Общественная казна", CellType.CHEST),
            PropertyCell(
                id=18,
                name="Передовиков",
                type=CellType.PROPERTY,
                color_group="orange",
                price=180,
                house_price=100,
                hotel_price=400,
                rent=[14, 70, 200, 550, 750, 950]
            ),
            PropertyCell(
                id=19,
                name="Жукова",
                type=CellType.PROPERTY,
                color_group="orange",
                price=200,
                house_price=100,
                hotel_price=400,
                rent=[16, 80, 220, 600, 800, 1000]
            ),

            # Бесплатная стоянка
            BoardCell(20, "Коворкинг с космонавтом. Просто отдохните во время окна", CellType.FREE_PARKING),

            # Красные улицы
            PropertyCell(
                id=21,
                name="Точка кипения",
                type=CellType.PROPERTY,
                color_group="red",
                price=220,
                house_price=150,
                hotel_price=500,
                rent=[18, 90, 250, 700, 875, 1050]
            ),
            BoardCell(22, "Шанс", CellType.CHANCE),
            PropertyCell(
                id=23,
                name="Актовый зал",
                type=CellType.PROPERTY,
                color_group="red",
                price=220,
                house_price=150,
                hotel_price=500,
                rent=[18, 90, 250, 700, 875, 1050]
            ),
            PropertyCell(
                id=24,
                name="Зал Да Винчи",
                type=CellType.PROPERTY,
                color_group="red",
                price=240,
                house_price=150,
                hotel_price=500,
                rent=[20, 100, 300, 750, 925, 1100]
            ),
            StationCell(id=25, name="Ст. метро Сенная площадь", type=CellType.STATION),

            # Желтые улицы
            PropertyCell(
                id=26,
                name="Ленсовета, 14",
                type=CellType.PROPERTY,
                color_group="yellow",
                price=260,
                house_price=150,
                hotel_price=600,
                rent=[22, 110, 330, 800, 975, 1150]
            ),
            PropertyCell(
                id=27,
                name="Гастелло, 15",
                type=CellType.PROPERTY,
                color_group="yellow",
                price=260,
                house_price=150,
                hotel_price=600,
                rent=[22, 110, 330, 800, 975, 1150]
            ),
            UtilityCell(id=28, name="Шавермечная", type=CellType.UTILITY),
            PropertyCell(
                id=29,
                name="Большая Морская, 67",
                type=CellType.PROPERTY,
                color_group="yellow",
                price=280,
                house_price=150,
                hotel_price=600,
                rent=[24, 120, 360, 850, 1025, 1200]
            ),

            # Отправка в тюрьму
            BoardCell(30, "Вы не закрыли сессию и попадаете на комиссию. Отправляйтесь в деканат решать этот вопрос", CellType.GO_TO_JAIL),

            # Зеленые улицы
            PropertyCell(
                id=31,
                name="Вольчека",
                type=CellType.PROPERTY,
                color_group="green",
                price=300,
                house_price=200,
                hotel_price=750,
                rent=[26, 130, 390, 900, 1100, 1275]
            ),
            PropertyCell(
                id=32,
                name="Люди любят",
                type=CellType.PROPERTY,
                color_group="green",
                price=300,
                house_price=200,
                hotel_price=750,
                rent=[26, 130, 390, 900, 1100, 1275]
            ),
            BoardCell(33, "Общественная казна", CellType.CHEST),
            PropertyCell(
                id=34,
                name="Цех 85",
                type=CellType.PROPERTY,
                color_group="green",
                price=320,
                house_price=200,
                hotel_price=750,
                rent=[28, 150, 450, 1000, 1200, 1400]
            ),
            StationCell(id=35, name="Ст. метро Адмиралтейская", type=CellType.STATION),

            # Темно-синие улицы
            BoardCell(36, "Шанс", CellType.CHANCE),
            PropertyCell(
                id=37,
                name="Профбюро 4",
                type=CellType.PROPERTY,
                color_group="dark_blue",
                price=350,
                house_price=200,
                hotel_price=1000,
                rent=[35, 175, 500, 1100, 1300, 1500]
            ),
            BoardCell(38, "Взносы в профсоюз", CellType.TAX, "Заплатите 100$", 100),
            PropertyCell(
                id=39,
                name="Усы лисы",
                type=CellType.PROPERTY,
                color_group="dark_blue",
                price=400,
                house_price=200,
                hotel_price=1000,
                rent=[50, 200, 600, 1400, 1700, 2000]
            )
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

        if hasattr(player, 'increment_properties_bought'):
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

    def process_cell_action(self, position: int) -> Dict[str, Any]:
        """Определить действие для клетки"""
        cell = self.get_cell(position)

        if cell.type == CellType.GO_TO_JAIL:
            return {
                "action": "go_to_jail",
                "message": "Вы отправлены в тюрьму!"
            }
        elif cell.type == CellType.GO:
            return {
                "action": "collect_salary",
                "message": "Получите зарплату при проходе!"
            }
        elif cell.type == CellType.TAX:
            return {
                "action": "pay_tax",
                "message": f"Заплатите налог ${cell.price}",
                "amount": cell.price
            }
        elif cell.type == CellType.CHANCE or cell.type == CellType.CHEST:
            return {
                "action": "draw_card",
                "message": "Вытяните карту",
                "card_type": cell.type.value
            }
        elif cell.type == CellType.JAIL:
            return {
                "action": "visit_jail",
                "message": "Просто посещение тюрьмы"
            }
        elif cell.type == CellType.FREE_PARKING:
            return {
                "action": "free_parking",
                "message": "Бесплатная стоянка!"
            }
        elif isinstance(cell, (PropertyCell, StationCell, UtilityCell)):
            if cell.owner_id is None:
                return {
                    "action": "buy_property",
                    "message": f"Свободная собственность: {cell.name} за ${cell.price}",
                    "price": cell.price
                }
            elif cell.owner_id is not None:
                return {
                    "action": "pay_rent",
                    "message": f"Чужая собственность! Заплатите ренту",
                    "owner_id": cell.owner_id
                }

        return {"action": "none", "message": ""}

    def can_build_house(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Проверить возможность постройки дома"""
        cell = self.get_cell(property_id)

        # Проверяем, что это PropertyCell
        if not isinstance(cell, PropertyCell):
            return {"can_build": False, "reason": "Это не недвижимость"}

        if cell.owner_id != owner_id:
            return {"can_build": False, "reason": "Вы не владеете этой недвижимостью"}

        if cell.mortgaged:
            return {"can_build": False, "reason": "Недвижимость в залоге"}

        if cell.hotel:
            return {"can_build": False, "reason": "Уже построен отель"}

        if cell.houses >= 4:
            return {"can_build": False, "reason": "Максимум 4 дома"}

        # Проверяем владение всей цветовой группой
        color_group = cell.color_group
        group_cells = self.get_color_group_cells(color_group)

        # Проверяем, что все клетки группы принадлежат игроку
        player_owns_group = all(c.owner_id == owner_id for c in group_cells)
        if not player_owns_group:
            return {"can_build": False, "reason": f"Не владеете всей группой {color_group}"}

        # Проверка равномерности застройки
        group_houses = [c.houses for c in group_cells if not c.hotel]
        if not group_houses:
            min_houses = 0
        else:
            min_houses = min(group_houses)

        if cell.houses > min_houses:
            return {"can_build": False, "reason": "Нарушена равномерность застройки"}

        # Проверяем деньги для строительства (эту проверку сделаем в bot.py)
        house_price = cell.house_price

        return {
            "can_build": True,
            "house_price": house_price,
            "current_houses": cell.houses,
            "max_houses": 4,
            "can_build_hotel": cell.houses == 3  # Можно строить отель на 4-й дом
        }

    def build_house(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Построить дом"""
        check_result = self.can_build_house(property_id, owner_id)

        if not check_result["can_build"]:
            return check_result

        cell = self.get_cell(property_id)
        if not isinstance(cell, PropertyCell):
            return {"success": False, "reason": "Это не недвижимость"}

        house_price = check_result["house_price"]

        # Строим дом (проверку денег делаем в bot.py)
        cell.houses += 1

        return {
            "success": True,
            "property_name": cell.name,
            "houses": cell.houses,
            "price": house_price,
            "message": f"Построен дом на {cell.name}. Всего домов: {cell.houses}"
        }

    def can_build_hotel(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Проверить возможность постройки отеля"""
        cell = self.get_cell(property_id)

        if not isinstance(cell, PropertyCell):
            return {"can_build": False, "reason": "Это не недвижимость"}

        if cell.owner_id != owner_id:
            return {"can_build": False, "reason": "Вы не владеете этой недвижимости"}

        if cell.mortgaged:
            return {"can_build": False, "reason": "Недвижимость в залоге"}

        if cell.hotel:
            return {"can_build": False, "reason": "Отель уже построен"}

        if cell.houses != 4:
            return {"can_build": False, "reason": "Нужно 4 дома перед постройкой отеля"}

        # Проверяем владение всей цветовой группой
        color_group = cell.color_group
        group_cells = self.get_color_group_cells(color_group)

        player_owns_group = all(c.owner_id == owner_id for c in group_cells)
        if not player_owns_group:
            return {"can_build": False, "reason": f"Не владеете всей группой {color_group}"}

        # Берем цену отеля из свойства cell.hotel_price
        hotel_price = cell.hotel_price  # Теперь всегда задано явно

        return {
            "can_build": True,
            "hotel_price": hotel_price,
            "message": f"Можно построить отель за ${hotel_price}",
            "sell_price": hotel_price // 2  # Цена продажи отеля (половина стоимости)
        }


    def build_hotel(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Построить отель"""
        check_result = self.can_build_hotel(property_id, owner_id)

        if not check_result["can_build"]:
            return check_result

        cell = self.get_cell(property_id)
        if not isinstance(cell, PropertyCell):
            return {"success": False, "reason": "Это не недвижимость"}

        hotel_price = check_result["hotel_price"]

        # Строим отель
        cell.hotel = True
        cell.houses = 0  # Дома заменяются отелем

        return {
            "success": True,
            "property_name": cell.name,
            "hotel": True,
            "price": hotel_price,
            "message": f"Построен отель на {cell.name}!"
        }

    def can_sell_house(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Проверить возможность продажи дома/отеля"""
        cell = self.get_cell(property_id)

        if not isinstance(cell, PropertyCell):
            return {"can_sell": False, "reason": "Это не недвижимость"}

        if cell.owner_id != owner_id:
            return {"can_sell": False, "reason": "Вы не владеете этой недвижимости"}

        if not cell.houses and not cell.hotel:
            return {"can_sell": False, "reason": "На улице нет домов или отеля"}

        if cell.mortgaged:
            return {"can_sell": False, "reason": "Недвижимость в залоге"}

        # Проверка равномерности застройки при продаже
        color_group = cell.color_group
        group_cells = self.get_color_group_cells(color_group)

        # Находим максимальное количество домов в группе (без отелей)
        group_houses = [c.houses for c in group_cells if not c.hotel]
        if group_houses:
            max_houses = max(group_houses)
            if cell.houses > max_houses - 1:
                return {"can_sell": False, "reason": "Нарушена равномерность застройки"}

        # Рассчитываем цену продажи
        if cell.hotel:
            sell_price = cell.hotel_price // 2  # Половина цены отеля
            return {
                "can_sell": True,
                "sell_price": sell_price,
                "is_hotel": True,
                "message": f"Можно продать отель за ${sell_price}"
            }
        else:
            sell_price = cell.house_price // 2  # Половина цены дома
            return {
                "can_sell": True,
                "sell_price": sell_price,
                "is_hotel": False,
                "message": f"Можно продать дом за ${sell_price}"
            }

    def sell_house(self, property_id: int, owner_id: int) -> Dict[str, Any]:
        """Продать дом"""
        check_result = self.can_sell_house(property_id, owner_id)

        if not check_result["can_sell"]:
            return check_result

        cell = self.get_cell(property_id)
        if not isinstance(cell, PropertyCell):
            return {"success": False, "reason": "Это не недвижимость"}

        if check_result.get("is_hotel"):
            # Продажа отеля
            sell_price = check_result["sell_price"]
            cell.hotel = False
            cell.houses = 4  # Возвращаем 4 дома

            return {
                "success": True,
                "property_name": cell.name,
                "sold_hotel": True,
                "price": sell_price,
                "message": f"Продан отель на {cell.name} за ${sell_price}. Осталось 4 дома."
            }
        else:
            # Продажа дома
            sell_price = check_result["sell_price"]
            cell.houses -= 1

            return {
                "success": True,
                "property_name": cell.name,
                "houses": cell.houses,
                "price": sell_price,
                "message": f"Продан дом на {cell.name}. Осталось домов: {cell.houses}"
            }


    def get_color_group_cells(self, color_group: str) -> List[PropertyCell]:
        """Получить все клетки цветовой группы"""
        return [cell for cell in self.cells
                if isinstance(cell, PropertyCell) and cell.color_group == color_group]

    def get_player_buildable_properties(self, player_id: int) -> List[Dict]:
        """Получить список недвижимости игрока, на которых можно строить"""
        buildable = []

        for cell in self.cells:
            if isinstance(cell, PropertyCell) and cell.owner_id == player_id:
                check_result = self.can_build_house(cell.id, player_id)
                if check_result.get("can_build"):
                    buildable.append({
                        "id": cell.id,
                        "name": cell.name,
                        "houses": cell.houses,
                        "color_group": cell.color_group,
                        "price": check_result.get("house_price", 0)
                    })

        return buildable

    def get_player_hotel_properties(self, player_id: int) -> List[Dict]:
        """Получить список недвижимости игрока, на которых можно строить отели"""
        hotelable = []

        for cell in self.cells:
            if isinstance(cell, PropertyCell) and cell.owner_id == player_id:
                check_result = self.can_build_hotel(cell.id, player_id)
                if check_result.get("can_build"):
                    hotelable.append({
                        "id": cell.id,
                        "name": cell.name,
                        "houses": cell.houses,
                        "color_group": cell.color_group,
                        "price": check_result.get("hotel_price", 0)
                    })

        return hotelable

    def get_player_sellable_properties(self, player_id: int) -> List[Dict]:
        """Получить список недвижимости игрока, с которых можно продавать дома"""
        sellable = []

        for cell in self.cells:
            if isinstance(cell, PropertyCell) and cell.owner_id == player_id:
                check_result = self.can_sell_house(cell.id, player_id)
                if check_result.get("can_sell"):
                    sellable.append({
                        "id": cell.id,
                        "name": cell.name,
                        "houses": cell.houses,
                        "hotel": cell.hotel,
                        "color_group": cell.color_group,
                        "price": check_result.get("sell_price", 0),
                        "is_hotel": check_result.get("is_hotel", False)
                    })

        return sellable

    def get_color_group_info(self, player_id: int) -> Dict[str, Dict]:
        """Получить информацию о цветовых группах игрока"""
        color_groups = {}

        for cell in self.cells:
            if isinstance(cell, PropertyCell) and cell.color_group:
                color_group = cell.color_group

                if color_group not in color_groups:
                    # Получаем все клетки этой группы
                    group_cells = self.get_color_group_cells(color_group)
                    total_in_group = len(group_cells)

                    # Считаем сколько принадлежит игроку
                    owned_by_player = [c for c in group_cells if c.owner_id == player_id]
                    owned_count = len(owned_by_player)

                    # Считаем дома и отели
                    total_houses = sum(c.houses for c in owned_by_player)
                    total_hotels = sum(1 for c in owned_by_player if c.hotel)

                    # Получаем самую дешевую цену дома в группе
                    house_prices = [c.house_price for c in group_cells]
                    min_house_price = min(house_prices) if house_prices else 0


                    color_groups[color_group] = {
                        "total": total_in_group,
                        "owned": owned_count,
                        "complete": owned_count == total_in_group,
                        "properties": group_cells,
                        "owned_properties": owned_by_player,
                        "total_houses": total_houses,
                        "total_hotels": total_hotels,
                        "house_price": min_house_price
                    }

        return color_groups
