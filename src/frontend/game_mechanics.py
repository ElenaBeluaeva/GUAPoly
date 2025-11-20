"""
🎲 МЕХАНИКИ ИГРЫ И РАСЧЕТЫ
День 4: Бросок кубиков, перемещение, расчеты
"""
import random
from src.frontend.visuals import BOARD_CONFIG


class Dice:
    """Класс для работы с кубиками"""

    @staticmethod
    def roll() -> tuple:
        """Бросок двух кубиков"""
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        return dice1, dice2, dice1 + dice2

    @staticmethod
    def is_double(dice1: int, dice2: int) -> bool:
        """Проверка на дубль"""
        return dice1 == dice2


class Movement:
    """Класс для перемещения игроков"""

    @staticmethod
    def move_player(current_position: int, steps: int, board_size: int = 40) -> tuple:
        """
        Перемещение игрока с учетом круга
        Возвращает (новая_позиция, прошел_старт)
        """
        new_position = (current_position + steps) % board_size
        passed_start = (current_position + steps) >= board_size

        return new_position, passed_start

    @staticmethod
    def get_path(current_position: int, steps: int, board_size: int = 40) -> list:
        """Получить путь игрока (все пройденные клетки)"""
        path = []
        for step in range(1, steps + 1):
            position = (current_position + step) % board_size
            path.append(position)
        return path


class Finance:
    """Класс для финансовых операций"""

    @staticmethod
    def calculate_rent(cell_type: str, base_rent: int, houses: int = 0, stations_owned: int = 0) -> int:
        """Расчет ренты"""
        if cell_type == 'street':
            rent_multipliers = [1, 5, 15, 45, 80, 125]  # 0-5 домов (5 = отель)
            return base_rent * rent_multipliers[min(houses, 5)]

        elif cell_type == 'station':
            return base_rent * stations_owned  # 25, 50, 100, 200

        elif cell_type == 'utility':
            # Для коммунальных предприятий рента = 4 * бросок кубиков
            # Здесь возвращаем базовую, реальная будет рассчитана при броске
            return base_rent

        return base_rent

    @staticmethod
    def calculate_salary() -> int:
        """Зарплата за проход старта"""
        return 200

    @staticmethod
    def can_afford(player_money: int, cost: int) -> bool:
        """Может ли игрок позволить себе покупку"""
        return player_money >= cost


class GameValidator:
    """Класс для проверки игровых правил"""

    @staticmethod
    def can_build_houses(property_group: list, current_houses: dict) -> bool:
        """
        Может ли игрок строить дома на этой улице
        property_group - список позиций в цветовой группе
        current_houses - словарь {позиция: количество_домов}
        """
        # Игрок должен владеть всеми улицами группы
        # Проверка равномерной застройки
        houses_in_group = [current_houses.get(pos, 0) for pos in property_group]
        min_houses = min(houses_in_group)
        max_houses = max(houses_in_group)

        return max_houses - min_houses <= 1

    @staticmethod
    def get_buildable_properties(properties: dict, player_properties: list) -> list:
        """Получить список свойств, на которых можно строить"""
        buildable = []

        # Группируем свойства по цветам
        color_groups = {}
        for prop_pos, prop_data in properties.items():
            if prop_data.get('type') == 'street':
                color = prop_data.get('color')
                if color not in color_groups:
                    color_groups[color] = []
                color_groups[color].append(prop_pos)

        # Проверяем какие группы полностью принадлежат игроку
        for color, group_positions in color_groups.items():
            player_owns_group = all(pos in player_properties for pos in group_positions)

            if player_owns_group:
                buildable.extend(group_positions)

        return buildable


# Демо-данные для тестирования механик
demo_game_state = {
    "players": {
        "Игрок1": {
            "position": 0,
            "money": 1500,
            "properties": [1, 3, 5],
            "in_jail": False,
            "jail_turns": 0
        },
        "Игрок2": {
            "position": 10,
            "money": 1450,
            "properties": [6, 8, 9],
            "in_jail": False,
            "jail_turns": 0
        }
    },
    "current_player": "Игрок1",
    "properties": {
        1: {"owner": "Игрок1", "houses": 0},
        3: {"owner": "Игрок1", "houses": 0},
        5: {"owner": "Игрок1", "houses": 0},
        6: {"owner": "Игрок2", "houses": 0},
        8: {"owner": "Игрок2", "houses": 0},
        9: {"owner": "Игрок2", "houses": 0}
    },
    "turn_count": 1
}