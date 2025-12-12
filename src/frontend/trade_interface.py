"""
Интерфейс торговли для Telegram бота
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
try:
    from src.backend.player import PlayerStatus
except ImportError:
    # Создаем локальную версию, если не удается импортировать
    from enum import Enum
    class PlayerStatus(Enum):
        ACTIVE = "active"
        BANKRUPT = "bankrupt"
        IN_JAIL = "in_jail"


def format_trade_summary(trade_items: dict, game=None, player_id=None) -> str:
    """Форматировать сводку по сделке"""
    lines = []

    if trade_items.get('money', 0) > 0:
        lines.append(f"  💰 ${trade_items['money']}")

    if trade_items.get('properties'):
        for prop_id in trade_items['properties']:
            if game:
                cell = game.board.get_cell(prop_id)
                if cell:
                    lines.append(f"  📌 {cell.name} (${cell.price})")
            else:
                lines.append(f"  📌 Собственность ID: {prop_id}")

    if not lines:
        lines.append("  (ничего)")

    return "\n".join(lines)


def calculate_trade_value(trade_items: dict, game, player_id: int) -> int:
    """Рассчитать стоимость сделки"""
    total = 0

    if 'money' in trade_items:
        total += trade_items['money']

    if 'properties' in trade_items:
        for prop_id in trade_items['properties']:
            cell = game.board.get_cell(prop_id)
            if cell and hasattr(cell, 'price'):
                total += cell.price

    return total


def get_trade_fairness_emoji(offer_value: int, request_value: int) -> str:
    """Получить эмодзи справедливости сделки"""
    if offer_value == 0 and request_value == 0:
        return "➖"

    if offer_value == 0:
        return "🎁"  # Дарение
    if request_value == 0:
        return "🎁"  # Дарение

    ratio = offer_value / request_value if request_value > 0 else float('inf')

    if ratio > 2:
        return "⚠️"  # Очень невыгодно
    elif ratio > 1.5:
        return "🤔"  # Невыгодно
    elif ratio > 0.8 and ratio < 1.2:
        return "✅"  # Справедливо
    elif ratio > 0.5:
        return "🤔"  # Выгодно
    else:
        return "⚠️"  # Очень выгодно


def create_trade_player_selection(game, current_player_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру выбора игрока для торговли"""
    keyboard = []

    for player_id, player in game.players.items():
        # Используем локальную проверку статуса
        player_status = getattr(player, 'status', None)
        is_active = False

        if hasattr(player_status, 'value'):
            is_active = player_status.value == "active"
        elif isinstance(player_status, str):
            is_active = player_status == "active"

        # Проверяем условия для торговли
        if (player_id != current_player_id and
                is_active and
                not getattr(player, 'in_jail', False)):
            # Считаем собственность более безопасным способом
            prop_count = (
                    len(getattr(player, 'properties', [])) +
                    len(getattr(player, 'stations', [])) +
                    len(getattr(player, 'utilities', []))
            )

            player_name = getattr(player, 'full_name', f'Игрок {player_id}')
            player_money = getattr(player, 'money', 0)

            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {player_name} (${player_money}, 🏠{prop_count})",
                    callback_data=f"trade_select_{game.game_id}_{player_id}"
                )
            ])

    if not keyboard:
        keyboard.append([
            InlineKeyboardButton("❌ Нет доступных игроков", callback_data="trade_none")
        ])

    keyboard.append([
        InlineKeyboardButton("❌ Отмена", callback_data="trade_cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


def create_trade_offer_selection(game, from_player_id: int, to_player_id: int,
                                 step: str = 'offer', offer: dict = None,
                                 request: dict = None) -> tuple:
    """
    Создать интерфейс выбора предложения/запроса

    Возвращает: (текст сообщения, клавиатура)
    """
    from_player = game.players[from_player_id]
    to_player = game.players[to_player_id]

    if step == 'offer':
        # Выбор того, что предлагаем
        title = "🤝 *ЧТО ВЫ ПРЕДЛАГАЕТЕ?*"
        current_items = offer or {'money': 0, 'properties': []}
        player = from_player
        player_props = game.get_player_available_properties(from_player_id)
        next_step = 'request'
        action = 'offer'
    else:  # step == 'request'
        # Выбор того, что просим
        title = "🤝 *ЧТО ВЫ ПРОСИТЕ ВЗАМЕН?*"
        current_items = request or {'money': 0, 'properties': []}
        player = to_player
        player_props = game.get_player_available_properties(to_player_id)
        next_step = 'confirm'
        action = 'request'

    # Форматируем текущий выбор
    current_summary = format_trade_summary(current_items, game, player.user_id)

    # Создаем клавиатуру
    keyboard = []

    # Кнопка денег
    if player.money > 0:
        money_text = f"💰 Деньги: ${current_items.get('money', 0)}"
        keyboard.append([
            InlineKeyboardButton(money_text,
                                 callback_data=f"trade_money_{game.game_id}_{from_player_id}_{to_player_id}_{action}")
        ])

    # Кнопки собственности
    for prop in player_props:
        is_selected = prop['id'] in current_items.get('properties', [])
        emoji = "✅" if is_selected else "📌"
        prop_text = f"{emoji} {prop['name']} (${prop['value']})"

        keyboard.append([
            InlineKeyboardButton(prop_text,
                                 callback_data=f"trade_prop_{game.game_id}_{from_player_id}_{to_player_id}_{prop['id']}_{action}")
        ])

    # Кнопки управления
    control_buttons = []

    if step == 'request':
        control_buttons.append(
            InlineKeyboardButton("⬅️ Назад",
                                 callback_data=f"trade_back_{game.game_id}_{from_player_id}_{to_player_id}")
        )

    control_buttons.extend([
        InlineKeyboardButton("🔄 Сбросить",
                             callback_data=f"trade_reset_{game.game_id}_{from_player_id}_{to_player_id}_{action}"),
        InlineKeyboardButton("➡️ Далее",
                             callback_data=f"trade_next_{game.game_id}_{from_player_id}_{to_player_id}_{action}")
    ])

    keyboard.append(control_buttons)
    keyboard.append([
        InlineKeyboardButton("❌ Отмена",
                             callback_data=f"trade_cancel_{game.game_id}_{from_player_id}_{to_player_id}")
    ])

    # Формируем текст
    text = f"{title}\n\n"
    text += f"👤 *Вы:* {from_player.full_name}\n"
    text += f"👤 *Партнер:* {to_player.full_name}\n\n"

    if step == 'request':
        # Показываем и предложение тоже
        offer_summary = format_trade_summary(offer, game, from_player_id)
        text += f"📤 *Ваше предложение:*\n{offer_summary}\n\n"

    text += f"📋 *Текущий выбор:*\n{current_summary}\n\n"

    if step == 'offer':
        text += f"💰 *Ваш баланс:* ${player.money}\n"
        text += f"🏠 *Доступно для обмена:* {len(player_props)} объектов\n"
    else:
        text += f"💰 *Баланс партнера:* ${player.money}\n"
        text += f"🏠 *У партнера доступно:* {len(player_props)} объектов\n"

    return text, InlineKeyboardMarkup(keyboard)


def create_trade_confirmation(game, from_player_id: int, to_player_id: int,
                              offer: dict, request: dict) -> tuple:
    """Создать интерфейс подтверждения сделки"""
    from_player = game.players[from_player_id]
    to_player = game.players[to_player_id]

    # Форматируем предложения
    offer_summary = format_trade_summary(offer, game, from_player_id)
    request_summary = format_trade_summary(request, game, to_player_id)

    # Рассчитываем стоимость
    offer_value = calculate_trade_value(offer, game, from_player_id)
    request_value = calculate_trade_value(request, game, to_player_id)

    # Оценка справедливости
    fairness_emoji = get_trade_fairness_emoji(offer_value, request_value)

    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить предложение",
                                 callback_data=f"trade_send_{game.game_id}_{from_player_id}_{to_player_id}"),
            InlineKeyboardButton("✏️ Редактировать",
                                 callback_data=f"trade_edit_{game.game_id}_{from_player_id}_{to_player_id}")
        ],
        [
            InlineKeyboardButton("❌ Отмена",
                                 callback_data=f"trade_cancel_{game.game_id}_{from_player_id}_{to_player_id}")
        ]
    ]

    # Формируем текст
    text = f"🤝 *ПОДТВЕРЖДЕНИЕ СДЕЛКИ*\n\n"
    text += f"👤 *От:* {from_player.full_name}\n"
    text += f"👤 *Кому:* {to_player.full_name}\n\n"
    text += f"📤 *ВЫ ОТДАЕТЕ:*\n{offer_summary}\n\n"
    text += f"📥 *ВЫ ПОЛУЧАЕТЕ:*\n{request_summary}\n\n"
    text += f"💰 *Оценка сделки:*\n"
    text += f"• Предлагаете: ${offer_value}\n"
    text += f"• Просите: ${request_value}\n"
    text += f"• Справедливость: {fairness_emoji}\n\n"

    # Добавляем предупреждения
    if offer_value == 0 and request_value > 0:
        text += "⚠️ *Внимание:* Вы просите дарение!\n\n"
    elif request_value == 0 and offer_value > 0:
        text += "⚠️ *Внимание:* Вы предлагаете дарение!\n\n"
    elif fairness_emoji == "⚠️":
        if offer_value > request_value * 2:
            text += "⚠️ *Внимание:* Вы предлагаете в 2 раза больше!\n\n"
        elif request_value > offer_value * 2:
            text += "⚠️ *Внимание:* Вы просите в 2 раза больше!\n\n"

    text += "*Подтвердите отправку предложения:*"

    return text, InlineKeyboardMarkup(keyboard)


def create_trade_response_buttons(trade_id: str) -> InlineKeyboardMarkup:
    """Создать кнопки ответа на предложение"""
    # Убедитесь, что trade_id корректно передается
    print(f"🔘 Создаем кнопки для trade_id: {trade_id}")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"trade_accept_{trade_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"trade_reject_{trade_id}")
        ]
    ])


def format_trade_notification(trade, game) -> str:
    """Форматировать уведомление о предложении"""
    from_player = game.players[trade.from_player_id]
    to_player = game.players[trade.to_player_id]

    offer_summary = format_trade_summary(trade.offer, game, trade.from_player_id)
    request_summary = format_trade_summary(trade.request, game, trade.to_player_id)

    text = f"🤝 *НОВОЕ ПРЕДЛОЖЕНИЕ ОБМЕНА!*\n\n"
    text += f"👤 *От:* {from_player.full_name}\n\n"
    text += f"📤 *ПРЕДЛАГАЕТ:*\n{offer_summary}\n\n"
    text += f"📥 *ПРОСИТ ВЗАМЕН:*\n{request_summary}\n\n"
    text += f"⏳ *Действует до:* {trade.expires_at.strftime('%H:%M:%S')}\n"
    text += f"🎮 *Игра:* {game.game_id}\n\n"
    text += f"*Выберите действие:*"

    return text


def create_trade_status_message(trade, game, action: str = "accepted") -> str:
    """Создать сообщение о статусе сделки"""
    from_player = game.players[trade.from_player_id]
    to_player = game.players[trade.to_player_id]

    if action == "accepted":
        emoji = "✅"
        status = "принята"
    elif action == "rejected":
        emoji = "❌"
        status = "отклонена"
    elif action == "cancelled":
        emoji = "⚠️"
        status = "отменена"
    elif action == "expired":
        emoji = "⏰"
        status = "истекла"
    else:
        emoji = "❓"
        status = "неизвестно"

    text = f"{emoji} *СДЕЛКА {status.upper()}*\n\n"
    text += f"👤 *От:* {from_player.full_name}\n"
    text += f"👤 *Кому:* {to_player.full_name}\n\n"

    if action in ["accepted", "rejected"]:
        text += f"⏰ *Когда:* {trade.processed_at.strftime('%H:%M:%S')}\n"

    if action == "accepted":
        text += "🎉 *Обмен успешно выполнен!*\n"

    return text