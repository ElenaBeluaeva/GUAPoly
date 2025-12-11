from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config


def get_main_menu_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("👥 Присоединиться", callback_data="menu_join_game")],
        [InlineKeyboardButton("📖 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
    ]

    # Добавляем кнопку админа, если пользователь - админ
    if user_id and user_id in Config.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="menu_admin")])

    return InlineKeyboardMarkup(keyboard)


def get_back_button_keyboard(target: str = "main_menu") -> InlineKeyboardMarkup:
    """Универсальная кнопка назад"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_{target}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_rules_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела правил"""
    keyboard = [
        [InlineKeyboardButton("📋 Основные правила", callback_data="rules_basic")],
        [InlineKeyboardButton("💸 Экономика", callback_data="rules_economy")],
        [InlineKeyboardButton("🏗️ Строительство", callback_data="rules_building")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для админ-панели"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎮 Активные игры", callback_data="admin_games")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_lobby_keyboard(is_creator: bool = False, game_id: str = "") -> InlineKeyboardMarkup:
    """Клавиатура лобби (День 2)"""
    keyboard = []

    if is_creator:
        keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data=f"lobby_start_{game_id}")])

    keyboard.extend([
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data=f"lobby_invite_{game_id}")],
        [InlineKeyboardButton("📊 Статистика лобби", callback_data="lobby_stats")],
        [InlineKeyboardButton("❌ Покинуть лобби", callback_data="lobby_leave")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_lobby_keyboard(is_creator: bool = False, game_id: str = "") -> InlineKeyboardMarkup:
    """Клавиатура лобби (День 2)"""
    keyboard = []

    if is_creator:
        keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data=f"lobby_start_{game_id}")])  # ← ИСПРАВЛЕНО

    keyboard.extend([
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data=f"lobby_invite_{game_id}")],
        [InlineKeyboardButton("📊 Статистика лобби", callback_data=f"lobby_stats_{game_id}")],  # ← Добавили game_id
        [InlineKeyboardButton("❌ Покинуть лобби", callback_data="lobby_leave")]
    ])

    return InlineKeyboardMarkup(keyboard)



def get_board_view_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для просмотра поля (День 3)"""
    keyboard = [
        [InlineKeyboardButton("🔍 Обзор клеток 0-9", callback_data="cell_overview_0")],
        [InlineKeyboardButton("🔍 Обзор клеток 10-19", callback_data="cell_overview_10")],
        [InlineKeyboardButton("🔍 Обзор клеток 20-29", callback_data="cell_overview_20")],
        [InlineKeyboardButton("🔍 Обзор клеток 30-39", callback_data="cell_overview_30")],
        [InlineKeyboardButton("💰 Финансовая сводка", callback_data="show_finances")],
        [InlineKeyboardButton("🔙 Назад к игре", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_properties_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления недвижимостью (День 3)"""
    keyboard = [
        [InlineKeyboardButton("🏗️ Управление домами", callback_data="manage_houses")],
        [InlineKeyboardButton("📊 Статистика", callback_data="properties_stats")],
        [InlineKeyboardButton("💸 Продать недвижимость", callback_data="sell_property")],
        [InlineKeyboardButton("🔙 Назад к игре", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_property_decision_keyboard(property_id: int, property_name: str, price: int) -> InlineKeyboardMarkup:
    """Клавиатура для решения о покупке недвижимости (День 4)"""
    keyboard = [
        [
            InlineKeyboardButton(f"✅ Купить за ${price}", callback_data=f"property_buy_{property_id}"),
            InlineKeyboardButton("❌ Отказаться", callback_data=f"property_skip_{property_id}")  # ← ИСПРАВЛЕНО
        ],
        [InlineKeyboardButton("🎰 Начать аукцион", callback_data=f"property_auction_{property_id}")],  # ← Добавили property_id
        [InlineKeyboardButton("🔙 Назад", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_after_roll_keyboard(position: int, can_buy: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после броска кубиков (День 4)"""
    keyboard = []

    if can_buy:
        keyboard.append([InlineKeyboardButton("🏠 Купить недвижимость", callback_data="property_buy")])

    keyboard.extend([
        [InlineKeyboardButton("🔍 Инфо о клетке", callback_data=f"cell_info_{position}")],
        [InlineKeyboardButton("🗺️ Посмотреть поле", callback_data="game_view_board")],
        [InlineKeyboardButton("⏭️ Завершить ход", callback_data="game_end_turn")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="back_main_menu")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_cell_overview_keyboard(start_position: int) -> InlineKeyboardMarkup:
    """Клавиатура для обзора группы клеток (День 3)"""
    keyboard = []

    # Показываем кнопки для 10 клеток
    for i in range(10):
        position = start_position + i
        if position < 40:
            keyboard.append([InlineKeyboardButton(f"📍 Клетка {position}", callback_data=f"cell_info_{position}")])

    keyboard.extend([
        [InlineKeyboardButton("🔙 Назад к обзору", callback_data="game_view_board")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="back_main_menu")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_house_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления домами (День 4)"""
    keyboard = [
        [InlineKeyboardButton("🏠 Построить дом", callback_data="build_house")],
        [InlineKeyboardButton("🏨 Построить отель", callback_data="build_hotel")],
        [InlineKeyboardButton("🔨 Продать дом", callback_data="sell_house")],
        [InlineKeyboardButton("🏚️ Продать отель", callback_data="sell_hotel")],
        [InlineKeyboardButton("🔙 Назад к свойствам", callback_data="game_my_properties")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_trade_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для торговли (День 4)"""
    keyboard = [
        [InlineKeyboardButton("🤝 Предложить обмен", callback_data="trade_propose")],
        [InlineKeyboardButton("📨 Мои предложения", callback_data="trade_my_offers")],
        [InlineKeyboardButton("📥 Входящие предложения", callback_data="trade_incoming")],
        [InlineKeyboardButton("🔙 Назад к игре", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_jail_keyboard(has_card: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура в тюрьме"""
    keyboard = []

    if has_card:
        keyboard.append([InlineKeyboardButton("🎫 Использовать карту освобождения", callback_data="jail_card")])

    keyboard.append([InlineKeyboardButton("💵 Заплатить $200", callback_data="jail_pay")])
    keyboard.append([InlineKeyboardButton("🎲 Попытаться выбросить дубль", callback_data="jail_roll")])
    keyboard.append([InlineKeyboardButton("⏳ Пропустить попытку", callback_data="jail_skip")])  # <-- ВЕРНУТЬ

    return InlineKeyboardMarkup(keyboard)



def get_card_actions_keyboard(card_type: str) -> InlineKeyboardMarkup:
    """Клавиатура для карточек шанс/казна (День 4)"""
    keyboard = [
        [InlineKeyboardButton("✅ Применить карту", callback_data=f"card_apply_{card_type}")],
        [InlineKeyboardButton("🔙 Продолжить игру", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_game_management_keyboard() -> InlineKeyboardMarkup:
    """Расширенная клавиатура игровых действий (День 4)"""
    keyboard = [
        [InlineKeyboardButton("🎲 Бросить кубики", callback_data="game_roll_dice")],
        [InlineKeyboardButton("🗺️ Посмотреть поле", callback_data="game_view_board")],
        [InlineKeyboardButton("🏠 Мои свойства", callback_data="game_my_properties")],
        [InlineKeyboardButton("🤝 Торговля", callback_data="game_trade")],
        [InlineKeyboardButton("💼 Управление", callback_data="game_manage")],
        [InlineKeyboardButton("⏭️ Завершить ход", callback_data="game_end_turn")]
    ]
    return InlineKeyboardMarkup(keyboard)
def get_manage_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления"""
    keyboard = [
        [InlineKeyboardButton("🏗️ Управление домами", callback_data="manage_houses")],
        [InlineKeyboardButton("💳 Заложить собственность", callback_data="manage_mortgage")],
        [InlineKeyboardButton("🏦 Снять залог", callback_data="manage_unmortgage")],
        [InlineKeyboardButton("📊 Статистика", callback_data="manage_stats")],
        [InlineKeyboardButton("🔙 Назад к игре", callback_data="back_game_actions")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_game_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура игровых действий (День 2)"""
    keyboard = [
        [InlineKeyboardButton("🎲 Бросить кубики", callback_data="game_roll_dice")],
        [InlineKeyboardButton("🗺 Посмотреть поле", callback_data="game_view_board")],
        [InlineKeyboardButton("🏠 Мои свойства", callback_data="game_my_properties")],
        [InlineKeyboardButton("🔙 Выйти из игры", callback_data="back_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
