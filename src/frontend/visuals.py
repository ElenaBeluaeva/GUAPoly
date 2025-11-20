"""
🎨 ВИЗУАЛИЗАЦИЯ ИГРОВОГО ПОЛЯ И ДАННЫХ
День 3: Детальная визуализация поля и клеток
"""

# 🎯 КОНФИГУРАЦИЯ ИГРОВОГО ПОЛЯ (40 клеток)
BOARD_CONFIG = {
    0: {"name": "СТАРТ", "type": "start", "emoji": "🚀"},
    1: {"name": "Винер-штрассе", "type": "street", "color": "Коричневый", "price": 60, "rent": 2},
    2: {"name": "Общественная казна", "type": "chest", "emoji": "🏦"},
    3: {"name": "Тироль-штрассе", "type": "street", "color": "Коричневый", "price": 60, "rent": 4},
    4: {"name": "Подоходный налог", "type": "tax", "price": 200, "emoji": "💸"},
    5: {"name": "Вокзал 1", "type": "station", "price": 200, "rent": 25},
    6: {"name": "Баденер-штрассе", "type": "street", "color": "Голубой", "price": 100, "rent": 6},
    7: {"name": "Шанс", "type": "chance", "emoji": "🎯"},
    8: {"name": "Зюдтиролер-штрассе", "type": "street", "color": "Голубой", "price": 100, "rent": 6},
    9: {"name": "Эльзасер-штрассе", "type": "street", "color": "Голубой", "price": 120, "rent": 8},
    10: {"name": "ТЮРЬМА", "type": "jail", "emoji": "🚓"},
    11: {"name": "Постштрассе", "type": "street", "color": "Розовый", "price": 140, "rent": 10},
    12: {"name": "Электростанция", "type": "utility", "price": 150, "rent": 0},
    13: {"name": "Зеештрассе", "type": "street", "color": "Розовый", "price": 140, "rent": 10},
    14: {"name": "Хафенштрассе", "type": "street", "color": "Розовый", "price": 160, "rent": 12},
    15: {"name": "Вокзал 2", "type": "station", "price": 200, "rent": 25},
    16: {"name": "Хауптштрассе", "type": "street", "color": "Оранжевый", "price": 180, "rent": 14},
    17: {"name": "Общественная казна", "type": "chest", "emoji": "🏦"},
    18: {"name": "Нойе-штрассе", "type": "street", "color": "Оранжевый", "price": 180, "rent": 14},
    19: {"name": "Мюнхенер-штрассе", "type": "street", "color": "Оранжевый", "price": 200, "rent": 16},
    20: {"name": "БЕСПЛАТНАЯ СТОЯНКА", "type": "free_parking", "emoji": "🅿️"},
    21: {"name": "Леопольдштрассе", "type": "street", "color": "Красный", "price": 220, "rent": 18},
    22: {"name": "Шанс", "type": "chance", "emoji": "🎯"},
    23: {"name": "Шлосс-аллея", "type": "street", "color": "Красный", "price": 220, "rent": 18},
    24: {"name": "Рингштрассе", "type": "street", "color": "Красный", "price": 240, "rent": 20},
    25: {"name": "Вокзал 3", "type": "station", "price": 200, "rent": 25},
    26: {"name": "Кайзер-штрассе", "type": "street", "color": "Желтый", "price": 260, "rent": 22},
    27: {"name": "Макс-штрассе", "type": "street", "color": "Желтый", "price": 260, "rent": 22},
    28: {"name": "Водопровод", "type": "utility", "price": 150, "rent": 0},
    29: {"name": "Курфюрстендамм", "type": "street", "color": "Желтый", "price": 280, "rent": 24},
    30: {"name": "ОТПРАВЛЕНИЕ В ТЮРЬМУ", "type": "go_to_jail", "emoji": "🚨"},
    31: {"name": "Гроссе-штрассе", "type": "street", "color": "Зеленый", "price": 300, "rent": 26},
    32: {"name": "Унтер-ден-Линден", "type": "street", "color": "Зеленый", "price": 300, "rent": 26},
    33: {"name": "Общественная казна", "type": "chest", "emoji": "🏦"},
    34: {"name": "Шлосс-штрассе", "type": "street", "color": "Зеленый", "price": 320, "rent": 28},
    35: {"name": "Вокзал 4", "type": "station", "price": 200, "rent": 25},
    36: {"name": "Шанс", "type": "chance", "emoji": "🎯"},
    37: {"name": "Херрен-штрассе", "type": "street", "color": "Синий", "price": 350, "rent": 35},
    38: {"name": "Налог на роскошь", "type": "tax", "price": 100, "emoji": "💎"},
    39: {"name": "Хох-штрассе", "type": "street", "color": "Синий", "price": 400, "rent": 50}
}


def render_detailed_board(players: dict, properties: dict = None) -> str:
    """
    Детальная текстовая визуализация игрового поля
    День 3: Показывает все клетки с игроками
    """
    if properties is None:
        properties = {}

    board_lines = []
    board_lines.append("🗺️ *ДЕТАЛЬНОЕ ИГРОВОЕ ПОЛЕ*")
    board_lines.append("═" * 40)

    # Показываем каждую клетку с игроками на ней
    for position in range(40):
        cell = BOARD_CONFIG[position]
        cell_emoji = cell.get('emoji', '🏠')

        # Игроки на этой клетке
        players_here = []
        for player_name, player_pos in players.items():
            if player_pos == position:
                players_here.append(player_name)

        players_text = ""
        if players_here:
            players_text = f" 👤{', '.join(players_here)}"

        # Информация о собственности
        property_info = ""
        if position in properties:
            owner = properties[position].get('owner')
            if owner:
                property_info = f" 💰({owner})"

        # Формируем строку клетки
        if cell['type'] == 'street':
            color_emoji = get_color_emoji(cell['color'])
            board_lines.append(
                f"{position:2d}. {color_emoji} {cell['name']} (${cell['price']}){players_text}{property_info}")
        else:
            board_lines.append(f"{position:2d}. {cell_emoji} {cell['name']}{players_text}{property_info}")

    board_lines.append("")
    board_lines.append("*🎨 Легенда:*")
    board_lines.append("🚀 Старт | 🚓 Тюрьма | 🎯 Шанс | 🏦 Казна")
    board_lines.append("🅿️ Стоянка | 💸 Налог | 🚨 В тюрьму")
    board_lines.append("🚂 Вокзал | ⚡ Коммуналка | 🏠 Улица")

    return "\n".join(board_lines)


def get_color_emoji(color: str) -> str:
    """Возвращает эмодзи для цвета группы"""
    color_emojis = {
        "Коричневый": "🟫",
        "Голубой": "🟦",
        "Розовый": "🩷",
        "Оранжевый": "🟧",
        "Красный": "🟥",
        "Желтый": "🟨",
        "Зеленый": "🟩",
        "Синий": "🔵"
    }
    return color_emojis.get(color, "🏠")


def render_cell_info(position: int, properties: dict = None) -> str:
    """
    Детальная информация о клетке
    День 3: Показывает все данные клетки
    """
    if properties is None:
        properties = {}

    cell = BOARD_CONFIG[position]
    lines = []

    lines.append(f"📍 *КЛЕТКА {position}: {cell['name']}*")
    lines.append("─" * 35)

    # Тип клетки
    type_emoji = cell.get('emoji', '🏠')
    lines.append(f"*Тип:* {type_emoji} {cell['type'].replace('_', ' ').title()}")

    # Для улиц показываем детали
    if cell['type'] == 'street':
        lines.append(f"*Цвет:* {get_color_emoji(cell['color'])} {cell['color']}")
        lines.append(f"*Стоимость:* ${cell['price']}")
        lines.append(f"*Базовая рента:* ${cell['rent']}")

        # Расчет ренты с домами
        if cell.get('houses', 0) > 0:
            houses = cell['houses']
            if houses == 5:
                lines.append(f"*🏨 Отель:* Рента ${cell['rent'] * 30}")
            else:
                lines.append(f"*🏠 Домов ({houses}):* Рента ${cell['rent'] * (houses * 5)}")

    elif cell['type'] == 'station':
        lines.append(f"*Стоимость:* ${cell['price']}")
        lines.append(f"*Рента:* ${cell['rent']} (за каждый вокзал)")

    elif cell['type'] == 'utility':
        lines.append(f"*Стоимость:* ${cell['price']}")
        lines.append("*Рента:* В 4 раза больше броска кубиков")

    elif cell['type'] == 'tax':
        lines.append(f"*💸 Платите:* ${cell['price']}")

    # Информация о владельце
    if position in properties:
        owner_data = properties[position]
        lines.append("")
        lines.append(f"*Владелец:* 👤 {owner_data['owner']}")
        if owner_data.get('houses', 0) > 0:
            houses = owner_data['houses']
            if houses == 5:
                lines.append(f"*Построено:* 🏨 1 отель")
            else:
                lines.append(f"*Построено:* 🏠 {houses} домов")
    else:
        lines.append("")
        lines.append("*Владелец:* Свободна 🆓")

    return "\n".join(lines)


def render_player_finances(players: dict) -> str:
    """
    Финансовая сводка всех игроков
    День 3: Показывает деньги и собственность
    """
    lines = []
    lines.append("💰 *ФИНАНСОВАЯ СВОДКА*")
    lines.append("═" * 30)

    for player_name, player_data in players.items():
        lines.append(f"👤 *{player_name}*")
        lines.append(f"   💰 Деньги: ${player_data.get('money', 0)}")

        properties = player_data.get('properties', [])
        if properties:
            lines.append(f"   🏠 Недвижимость: {len(properties)} объектов")
            # Группируем по цветам
            color_groups = {}
            for prop in properties:
                color = prop.get('color', 'Разное')
                if color not in color_groups:
                    color_groups[color] = 0
                color_groups[color] += 1

            for color, count in color_groups.items():
                lines.append(f"     {get_color_emoji(color)} {color}: {count}")
        else:
            lines.append("   🏠 Недвижимость: нет")

        lines.append("")  # Пустая строка между игроками

    return "\n".join(lines)


def render_text_board(players: dict) -> str:
    """
    Текстовая визуализация игрового поля (простая версия)
    Сохранена для обратной совместимости
    """
    board_lines = []
    board_lines.append("🗺️ *ИГРОВОЕ ПОЛО*")
    board_lines.append("═" * 30)

    # Показываем позиции игроков
    for player_name, position in players.items():
        board_lines.append(f"👤 {player_name}: клетка {position}")

    board_lines.append("")
    board_lines.append("*Легенда:*")
    board_lines.append("🚀 Старт | 🚓 Тюрьма | 🎯 Шанс")
    board_lines.append("🏠 Улица | 💰 Банк | 🏦 Казна")

    return "\n".join(board_lines)


def render_player_stats(player_data: dict) -> str:
    """Визуализация статистики игрока (простая версия)"""
    lines = []
    lines.append(f"👤 *{player_data['name']}*")
    lines.append("─" * 20)
    lines.append(f"💰 *Деньги:* ${player_data['money']}")
    lines.append(f"📍 *Позиция:* {player_data['position']}")

    if player_data.get('properties'):
        lines.append("")
        lines.append("🏠 *Недвижимость:*")
        for prop in player_data['properties']:
            lines.append(f"• {prop}")
    else:
        lines.append("")
        lines.append("🏠 *Недвижимость:* нет")

    return "\n".join(lines)