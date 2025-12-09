"""
🎮 ГЛАВНЫЙ ЗАПУСКНОЙ ФАЙЛ БОТА МОНОПОЛИИ
Работающая версия с интеграцией game_manager.py
"""

import os
import sys
import logging
from typing import Dict

# Telegram Bot импорты
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Добавляем путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== УПРОЩЕННЫЕ КЛАССЫ ДЛЯ СОВМЕСТИМОСТИ ==========

import random
import string
from datetime import datetime


class SimplePlayer:
    def __init__(self, user_id: int, username: str, full_name: str):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.position = 0
        self.money = 1500
        self.properties = []
        self.in_jail = False
        self.jail_turns = 0
        self.color = random.choice(["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚫", "⚪"])


class SimpleGame:
    def __init__(self, game_id: str, creator_id: int):
        self.game_id = game_id
        self.creator_id = creator_id
        self.players: Dict[int, SimplePlayer] = {}
        self.player_order = []
        self.current_player_index = 0
        self.state = "lobby"
        self.created_at = datetime.now().strftime("%H:%M")
        self.double_count = 0

    def add_player(self, user_id: int, username: str, full_name: str) -> bool:
        if user_id in self.players:
            return False
        if self.state != "lobby":
            return False
        if len(self.players) >= 8:
            return False

        player = SimplePlayer(user_id, username, full_name)
        self.players[user_id] = player
        return True

    def remove_player(self, user_id: int):
        if user_id in self.players:
            if user_id in self.player_order:
                self.player_order.remove(user_id)
            del self.players[user_id]

    def start_game(self) -> bool:
        if len(self.players) < 2:
            return False
        if self.state != "lobby":
            return False

        self.state = "in_game"
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.current_player_index = 0
        return True

    def get_current_player(self):
        if not self.player_order:
            return None
        current_id = self.player_order[self.current_player_index]
        return self.players.get(current_id)

    def next_turn(self):
        if not self.player_order:
            return
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.double_count = 0

    def roll_dice(self):
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        if dice1 == dice2:
            self.double_count += 1
        else:
            self.double_count = 0

        return dice1, dice2, total


# Глобальные переменные для хранения данных
games: Dict[str, SimpleGame] = {}
player_to_game: Dict[int, str] = {}  # user_id -> game_id


# ========== ФУНКЦИИ ДЛЯ МЕНЮ ==========

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("👥 Присоединиться", callback_data="menu_join_game")],
        [InlineKeyboardButton("📖 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_lobby_keyboard(is_creator: bool = False, game_id: str = "") -> InlineKeyboardMarkup:
    """Клавиатура лобби"""
    keyboard = []

    if is_creator:
        keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="lobby_start_game")])

    keyboard.extend([
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data=f"lobby_invite_{game_id}")],
        [InlineKeyboardButton("📊 Статистика лобби", callback_data="lobby_stats")],
        [InlineKeyboardButton("❌ Покинуть лобби", callback_data="lobby_leave")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_game_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура игровых действий"""
    keyboard = [
        [InlineKeyboardButton("🎲 Бросить кубики", callback_data="game_roll_dice")],
        [InlineKeyboardButton("🗺️ Посмотреть поле", callback_data="game_view_board")],
        [InlineKeyboardButton("🏠 Мои свойства", callback_data="game_my_properties")],
        [InlineKeyboardButton("🔙 Выйти из игры", callback_data="game_leave")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал работу")

    welcome_text = f"""🎲 *Добро пожаловать в Монополию, {user.first_name}!*

*Это телеграм-версия классической настольной игры!*

*🚀 Быстрый старт:*
1. Создайте новую игру
2. Пригласите друзей 
3. Начните играть!

*📋 Основные команды:*
/start - Главное меню
/newgame - Новая игра
/join - Присоединиться к игре
/help - Правила игры
/myid - Узнать свой ID

*💡 Начните с создания игры и пригласите друзей!*"""

    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /myid - РАБОТАЕТ ДЛЯ ВСЕХ!"""
    user = update.effective_user

    # Экранируем специальные символы Markdown
    username = user.username if user.username else 'нет'
    # Экранируем символы, которые могут сломать Markdown
    safe_username = username.replace('_', r'\_').replace('*', r'\*').replace('`', r'\`').replace('[', r'\[')
    safe_full_name = user.full_name.replace('_', r'\_').replace('*', r'\*').replace('`', r'\`').replace('[', r'\[')

    # Формируем ответ
    response = (
        f"🆔 *Ваш ID:* `{user.id}`\n"
        f"👤 *Имя:* {safe_full_name}\n"
        f"📱 *Username:* @{safe_username}\n"
    )

    # Проверяем, есть ли игрок в игре
    game_id = player_to_game.get(user.id)
    if game_id and game_id in games:
        game = games[game_id]
        response += f"\n🎮 *Текущая игра:* `{game.game_id}`"
        response += f"\n👥 *Игроков:* {len(game.players)}/8"
        if game.state == "in_game":
            response += f"\n🎲 *Статус:* Игра идет"
        else:
            response += f"\n🕓 *Статус:* В лобби"

    await update.message.reply_text(response, parse_mode="Markdown")
    logger.info(f"Пользователь {user.id} запросил свой ID")

async def newgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /newgame"""
    user_id = update.effective_user.id
    user = update.effective_user

    logger.info(f"Пользователь {user_id} пытается создать игру")

    # Проверяем, не участвует ли пользователь уже в игре
    if user_id in player_to_game:
        game_id = player_to_game[user_id]
        await update.message.reply_text(
            f"❌ Вы уже участвуете в игре!\n"
            f"Код игры: `{game_id}`\n\n"
            f"Сначала покиньте текущую игру командой /leave",
            parse_mode="Markdown"
        )
        return

    # Создаем новую игру
    while True:
        game_id = ''.join(random.choices(string.ascii_uppercase, k=6))
        if game_id not in games:
            break

    game = SimpleGame(game_id, user_id)
    games[game_id] = game

    # Добавляем создателя в игру
    if game.add_player(user_id, user.username or "Игрок", user.full_name):
        player_to_game[user_id] = game_id

        keyboard = get_lobby_keyboard(is_creator=True, game_id=game_id)
        await update.message.reply_text(
            f"🎮 *Игра создана!*\n\n"
            f"*Код игры:* `{game_id}`\n\n"
            f"*Пригласите друзей:*\n"
            f"Они могут присоединиться командой:\n"
            f"`/join {game_id}`\n\n"
            f"*Игроки в лобби:*\n"
            f"• {user.full_name} (👑 Создатель)\n\n"
            f"*Статус:* Ожидание игроков (1/8)",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.info(f"Игра {game_id} создана")
    else:
        await update.message.reply_text("❌ Не удалось создать игру!", parse_mode="Markdown")


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /join"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите код игры:\n`/join ABC123`",
            parse_mode="Markdown"
        )
        return

    game_id = context.args[0].upper()
    user = update.effective_user

    logger.info(f"Пользователь {user.id} пытается присоединиться к игре {game_id}")

    # Проверяем, не участвует ли уже в игре
    if user.id in player_to_game:
        existing_game_id = player_to_game[user.id]
        await update.message.reply_text(
            f"❌ Вы уже участвуете в игре!\n"
            f"Код игры: `{existing_game_id}`\n\n"
            f"Сначала покиньте текущую игру командой /leave",
            parse_mode="Markdown"
        )
        return

    # Проверяем существование игры
    if game_id not in games:
        await update.message.reply_text(
            "❌ Игра не найдена! Проверьте код игры.",
            parse_mode="Markdown"
        )
        return

    game = games[game_id]

    # Пытаемся присоединиться
    if game.add_player(user.id, user.username or "Игрок", user.full_name):
        player_to_game[user.id] = game_id

        # Формируем список игроков
        players_list = "\n".join([
            f"• {player.full_name}" + (" 👑" if player.user_id == game.creator_id else "")
            for player in game.players.values()
        ])

        keyboard = get_lobby_keyboard(
            is_creator=(user.id == game.creator_id),
            game_id=game_id
        )

        await update.message.reply_text(
            f"✅ *Вы присоединились к игре {game_id}!*\n\n"
            f"*Игроки в лобби:*\n{players_list}\n\n"
            f"Ожидайте начала игры от создателя.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.info(f"Пользователь {user.id} присоединился к игре {game_id}")
    else:
        await update.message.reply_text(
            "❌ Не удалось присоединиться к игре!\n"
            "Возможные причины:\n"
            "• Игра уже началась\n"
            "• Достигнут лимит игроков (8)\n"
            "• Вы уже в другой игре",
            parse_mode="Markdown"
        )


async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /games"""
    available_games = [game for game in games.values()
                       if game.state == "lobby" and len(game.players) < 8]

    if not available_games:
        await update.message.reply_text(
            "📭 *Нет доступных игр в лобби.*\n"
            "Создайте новую игру: /newgame",
            parse_mode="Markdown"
        )
        return

    response = "🎲 *Доступные игры:*\n\n"

    for i, game in enumerate(available_games, 1):
        creator = game.players.get(game.creator_id)
        creator_name = creator.full_name if creator else "Неизвестно"

        response += (
            f"{i}. *Игра {game.game_id}*\n"
            f"   👑 Создатель: {creator_name}\n"
            f"   👥 Игроков: {len(game.players)}/8\n"
            f"   👉 Присоединиться: `/join {game.game_id}`\n"
            f"   {'─' * 20}\n"
        )

    await update.message.reply_text(response, parse_mode="Markdown")


async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /startgame"""
    user_id = update.effective_user.id
    user = update.effective_user

    logger.info(f"Пользователь {user_id} пытается начать игру")

    # Проверяем, участвует ли пользователь в игре
    if user_id not in player_to_game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*\n"
            "Сначала создайте игру: /newgame\n"
            "Или присоединитесь к существующей: /join <код>",
            parse_mode="Markdown"
        )
        return

    game_id = player_to_game[user_id]

    if game_id not in games:
        await update.message.reply_text(
            "❌ *Игра не найдена!*\n"
            "Возможно, игра была удалена.",
            parse_mode="Markdown"
        )
        return

    game = games[game_id]

    # Проверяем, является ли пользователь создателем игры
    if game.creator_id != user_id:
        await update.message.reply_text(
            f"❌ *Только создатель может начать игру!*\n"
            f"Создатель: {game.players[game.creator_id].full_name}",
            parse_mode="Markdown"
        )
        return

    # Проверяем, что игра еще в лобби
    if game.state != "lobby":
        await update.message.reply_text(
            f"❌ *Игра уже началась!*\n"
            f"Текущий статус: {'Идет игра' if game.state == 'in_game' else 'Завершена'}",
            parse_mode="Markdown"
        )
        return

    # Проверяем минимальное количество игроков
    if len(game.players) < 2:
        await update.message.reply_text(
            f"❌ *Нужно хотя бы 2 игрока для начала!*\n"
            f"Сейчас игроков: {len(game.players)}",
            parse_mode="Markdown"
        )
        return

    # Начинаем игру
    if game.start_game():
        # Получаем первого игрока
        first_player = game.get_current_player()

        # Формируем список игроков в порядке хода
        players_list = "\n".join([
            f"{i + 1}. {game.players[player_id].full_name}"
            for i, player_id in enumerate(game.player_order)
        ])

        # Сообщение о начале игры
        start_message = f"""🎮 *ИГРА НАЧАЛАСЬ!*

*Порядок ходов:*
{players_list}

*Первый ходит:* {first_player.full_name}

💰 *Стартовый капитал:* $1500 каждому
📍 *Начальная позиция:* клетка 0 (СТАРТ)

🎲 Используйте кнопку "Бросить кубики" для начала хода!"""

        await update.message.reply_text(
            start_message,
            parse_mode="Markdown"
        )

        # Отправляем уведомления всем игрокам
        for player_id, player in game.players.items():
            if player_id != user_id:  # Не отправляем создателю (он уже получил сообщение)
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=f"🎮 *Игра началась!*\n\n"
                             f"Создатель {user.full_name} начал игру.\n"
                             f"Порядок ходов:\n{players_list}\n\n"
                             f"*Первый ходит:* {first_player.full_name}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление игроку {player_id}: {e}")

        # Отправляем игровое меню
        keyboard = get_game_actions_keyboard()
        await update.message.reply_text(
            f"🎲 *Начните игру!*\n\n"
            f"Первый ход у {first_player.full_name}\n"
            f"Используйте кнопки ниже для управления игрой:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        logger.info(f"Игра {game_id} начата. Первый ходит: {first_player.full_name}")

    else:
        await update.message.reply_text(
            "❌ *Не удалось начать игру!*\n"
            "Возможные причины:\n"
            "• Игра уже началась\n"
            "• Недостаточно игроков\n"
            "• Техническая ошибка",
            parse_mode="Markdown"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help"""
    help_text = """📖 *ПРАВИЛА МОНОПОЛИИ*

*🎯 Цель игры:* Стать последним непобанкротившимся игроком!

*🔄 Как играть:*
1. 🎲 *Бросок кубиков* - ходите по очереди
2. 🏠 *Покупка недвижимости* - покупайте свободные клетки
3. 💰 *Сбор ренты* - другие игроки платят вам
4. 🏗️ *Строительство* - стройте дома и отели
5. 🤝 *Торговля* - обменивайтесь с другими игроками

*📍 Особые клетки:*
🚀 *Старт* - получайте $200 за проход
🚓 *Тюрьма* - посещение или отсидка
🎯 *Шанс/Казна* - случайные события
💸 *Налоги* - платите банку

*💎 Стартовый капитал:* $1500
*👥 Максимум игроков:* 8

*🎮 Управление в боте:*
Используйте кнопки под сообщениями для всех действий!"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /leave"""
    user_id = update.effective_user.id

    if user_id not in player_to_game:
        await update.message.reply_text(
            "❌ *Вы не участвуете в игре!*",
            parse_mode="Markdown"
        )
        return

    game_id = player_to_game[user_id]

    if game_id in games:
        game = games[game_id]
        game.remove_player(user_id)

        # Если игра пуста, удаляем ее
        if not game.players:
            del games[game_id]

    del player_to_game[user_id]

    await update.message.reply_text(
        "👋 *Вы покинули игру!*",
        parse_mode="Markdown"
    )

    # Возвращаем в главное меню
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(
        "🎲 *Главное меню*\n\nВыберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ========== ОБРАБОТЧИКИ КНОПОК ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    logger.info(f"Нажата кнопка: {data} пользователем {user_id}")

    try:
        # === ГЛАВНОЕ МЕНЮ ===
        if data == "menu_new_game":
            await newgame_command(query.message, context)

        elif data == "menu_join_game":
            await query.message.edit_text(
                "👥 *Присоединиться к игре*\n\n"
                "Введите команду:\n"
                "`/join КОД_ИГРЫ`\n\n"
                "Или просмотрите доступные игры: /games",
                parse_mode="Markdown"
            )

        elif data == "menu_rules":
            await help_command(query.message, context)

        elif data == "menu_profile":
            user = query.from_user
            game_id = player_to_game.get(user.id)

            if game_id and game_id in games:
                game = games[game_id]
                game_status = "🎮 В игре" if game.state == "in_game" else "🕓 В лобби"
                response = (
                    f"👤 *Ваш профиль*\n\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"👤 Имя: {user.full_name}\n"
                    f"📱 Username: @{user.username or 'нет'}\n\n"
                    f"🎮 *Статус:* {game_status}\n"
                    f"Код игры: `{game.game_id}`"
                )
            else:
                response = (
                    f"👤 *Ваш профиль*\n\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"👤 Имя: {user.full_name}\n"
                    f"📱 Username: @{user.username or 'нет'}\n\n"
                    f"🎮 *Статус:* 📭 Нет игры"
                )

            await query.message.edit_text(response, parse_mode="Markdown")

        # === ЛОББИ ===
        elif data == "lobby_start_game":
            game_id = player_to_game.get(user_id)

            if not game_id or game_id not in games:
                await query.answer("❌ Вы не в игре!", show_alert=True)
                return

            game = games[game_id]

            if game.creator_id != user_id:
                await query.answer("❌ Только создатель может начать игру!", show_alert=True)
                return

            if len(game.players) < 2:
                await query.answer("❌ Нужно хотя бы 2 игрока для начала!", show_alert=True)
                return

            if game.start_game():
                first_player = game.get_current_player()
                players_list = "\n".join([
                    f"{i + 1}. {game.players[player_id].full_name}"
                    for i, player_id in enumerate(game.player_order)
                ])

                await query.message.edit_text(
                    f"🎮 *Игра началась!*\n\n"
                    f"*Порядок ходов:*\n{players_list}\n\n"
                    f"*Первый ходит:* {first_player.full_name}",
                    parse_mode="Markdown"
                )

                # Отправляем игровое меню
                keyboard = get_game_actions_keyboard()
                await query.message.reply_text(
                    "🎲 *Начните игру!*\n\n"
                    f"Первый ход у {first_player.full_name}",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await query.answer("❌ Не удалось начать игру!", show_alert=True)

        elif data.startswith("lobby_invite_"):
            try:
                game_id = data.split("_")[-1]
                await query.message.reply_text(
                    f"👥 *Приглашение в игру*\n\n"
                    f"Код игры: `{game_id}`\n\n"
                    f"*Скопируйте и отправьте друзьям:*\n"
                    f"`/join {game_id}`",
                    parse_mode="Markdown"
                )
            except:
                await query.answer("Ошибка приглашения", show_alert=True)

        elif data == "lobby_stats":
            game_id = player_to_game.get(user_id)

            if game_id and game_id in games:
                game = games[game_id]
                players_list = "\n".join([
                    f"• {player.full_name}" + (" 👑" if player.user_id == game.creator_id else "")
                    for player in game.players.values()
                ])

                await query.message.reply_text(
                    f"📊 *Статистика лобби*\n\n"
                    f"*Игра:* {game.game_id}\n"
                    f"*Игроков:* {len(game.players)}/8\n"
                    f"*Создатель:* {game.players[game.creator_id].full_name}\n\n"
                    f"*Участники:*\n{players_list}",
                    parse_mode="Markdown"
                )

        elif data == "lobby_leave":
            await leave_command(query.message, context)

        # === ИГРОВЫЕ ДЕЙСТВИЯ ===
        elif data == "game_roll_dice":
            game_id = player_to_game.get(user_id)

            if not game_id or game_id not in games:
                await query.answer("❌ Вы не в игре!", show_alert=True)
                return

            game = games[game_id]

            if game.state != "in_game":
                await query.answer("❌ Игра еще не началась!", show_alert=True)
                return

            current_player = game.get_current_player()
            if not current_player or current_player.user_id != user_id:
                await query.answer(
                    f"❌ Сейчас ходит {current_player.full_name if current_player else 'другой игрок'}!",
                    show_alert=True
                )
                return

            # Бросок кубиков
            dice1, dice2, total = game.roll_dice()
            current_player.position = (current_player.position + total) % 40

            # Проверка прохода старта
            passed_start = current_player.position < total
            if passed_start:
                current_player.money += 200

            response = f"🎲 *{current_player.full_name} бросает кубики:*\n"
            response += f"🎯 {dice1} + {dice2} = *{total}*\n\n"

            if passed_start:
                response += f"💰 *Прошли СТАРТ!* +$200\n\n"

            response += f"📍 *Позиция {current_player.position}*\n"
            response += f"💰 *Баланс:* ${current_player.money}"

            # Проверка на дубль
            if dice1 == dice2:
                response += "\n\n🎲 *Дубль! Ходите еще раз!*"
                await query.answer("🎲 Дубль! Ходите еще раз!", show_alert=True)
            else:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response += f"\n\n⏭️ *Следующий ход:* {next_player.full_name}"

            keyboard = get_game_actions_keyboard()
            await query.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")

        elif data == "game_view_board":
            game_id = player_to_game.get(user_id)

            if game_id and game_id in games:
                game = games[game_id]

                board_text = "🗺️ *Игровое поле*\n\n"
                for player in game.players.values():
                    board_text += f"👤 *{player.full_name}* {player.color}: клетка {player.position}\n"

                await query.message.edit_text(board_text, parse_mode="Markdown")
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

        elif data == "game_my_properties":
            game_id = player_to_game.get(user_id)

            if not game_id or game_id not in games:
                await query.answer("❌ Вы не в игре!", show_alert=True)
                return

            game = games[game_id]
            player = game.players.get(user_id)

            if not player:
                await query.answer("❌ Игрок не найден!", show_alert=True)
                return

            response = f"🏘 *Собственность {player.full_name}*\n\n"
            response += f"💰 *Деньги:* ${player.money}\n"
            response += f"🏠 *Недвижимость:* {len(player.properties)} объектов\n"
            response += f"📍 *Позиция:* {player.position}"

            keyboard = get_game_actions_keyboard()
            await query.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")

        elif data == "game_leave":
            await leave_command(query.message, context)

    except Exception as e:
        logger.error(f"Ошибка обработки кнопки: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех нажатий на кнопки"""
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Ошибка при answer: {e}")
        # Пытаемся отправить сообщение об ошибке
        try:
            await update.message.reply_text("⚠️ Произошла ошибка при обработке кнопки")
        except:
            pass
        return

    data = query.data
    user_id = query.from_user.id

    logger.info(f"Нажата кнопка: {data} пользователем {user_id}")

    try:
        # === ГЛАВНОЕ МЕНЮ ===
        if data == "menu_new_game":
            await newgame_command(query.message, context)

        elif data == "menu_join_game":
            try:
                await query.message.edit_text(
                    "👥 *Присоединиться к игре*\n\n"
                    "Введите команду:\n"
                    "`/join КОД_ИГРЫ`\n\n"
                    "Или просмотрите доступные игры: /games",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка в menu_join_game: {e}")
                await query.message.edit_text(
                    "👥 Присоединиться к игре\n\n"
                    "Введите команду:\n"
                    "/join КОД_ИГРЫ\n\n"
                    "Или просмотрите доступные игры: /games"
                )

        elif data == "menu_rules":
            await help_command(query.message, context)

        elif data == "menu_profile":
            try:
                user = query.from_user
                game_id = player_to_game.get(user.id)

                if game_id and game_id in games:
                    game = games[game_id]
                    game_status = "🎮 В игре" if game.state == "in_game" else "🕓 В лобби"
                    response = (
                        f"👤 *Ваш профиль*\n\n"
                        f"🆔 ID: `{user.id}`\n"
                        f"👤 Имя: {user.full_name}\n"
                        f"📱 Username: @{user.username or 'нет'}\n\n"
                        f"🎮 *Статус:* {game_status}\n"
                        f"Код игры: `{game.game_id}`"
                    )
                else:
                    response = (
                        f"👤 *Ваш профиль*\n\n"
                        f"🆔 ID: `{user.id}`\n"
                        f"👤 Имя: {user.full_name}\n"
                        f"📱 Username: @{user.username or 'нет'}\n\n"
                        f"🎮 *Статус:* 📭 Нет игры"
                    )

                await query.message.edit_text(response, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка в menu_profile: {e}")
                # Упрощенный ответ без Markdown
                user = query.from_user
                game_id = player_to_game.get(user.id)

                if game_id and game_id in games:
                    game = games[game_id]
                    response = (
                        f"👤 Ваш профиль\n\n"
                        f"🆔 ID: {user.id}\n"
                        f"👤 Имя: {user.full_name}\n"
                        f"📱 Username: @{user.username or 'нет'}\n\n"
                        f"🎮 Статус: {'В игре' if game.state == 'in_game' else 'В лобби'}\n"
                        f"Код игры: {game.game_id}"
                    )
                else:
                    response = (
                        f"👤 Ваш профиль\n\n"
                        f"🆔 ID: {user.id}\n"
                        f"👤 Имя: {user.full_name}\n"
                        f"📱 Username: @{user.username or 'нет'}\n\n"
                        f"🎮 Статус: Нет игры"
                    )

                await query.message.edit_text(response)

        # === ЛОББИ ===
        elif data == "lobby_start_game":
            try:
                game_id = player_to_game.get(user_id)

                if not game_id or game_id not in games:
                    await query.answer("❌ Вы не в игре!", show_alert=True)
                    return

                game = games[game_id]

                if game.creator_id != user_id:
                    await query.answer("❌ Только создатель может начать игру!", show_alert=True)
                    return

                if len(game.players) < 2:
                    await query.answer("❌ Нужно хотя бы 2 игрока для начала!", show_alert=True)
                    return

                if game.start_game():
                    first_player = game.get_current_player()
                    players_list = "\n".join([
                        f"{i + 1}. {game.players[player_id].full_name}"
                        for i, player_id in enumerate(game.player_order)
                    ])

                    await query.message.edit_text(
                        f"🎮 *Игра началась!*\n\n"
                        f"*Порядок ходов:*\n{players_list}\n\n"
                        f"*Первый ходит:* {first_player.full_name}",
                        parse_mode="Markdown"
                    )

                    # Отправляем игровое меню
                    keyboard = get_game_actions_keyboard()
                    await query.message.reply_text(
                        "🎲 *Начните игру!*\n\n"
                        f"Первый ход у {first_player.full_name}",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    await query.answer("❌ Не удалось начать игру!", show_alert=True)
            except Exception as e:
                logger.error(f"Ошибка в lobby_start_game: {e}")
                await query.answer("❌ Ошибка при старте игры", show_alert=True)

        elif data.startswith("lobby_invite_"):
            try:
                game_id = data.split("_")[-1]
                await query.message.reply_text(
                    f"👥 *Приглашение в игру*\n\n"
                    f"Код игры: `{game_id}`\n\n"
                    f"*Скопируйте и отправьте друзьям:*\n"
                    f"`/join {game_id}`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка в lobby_invite: {e}")
                await query.answer("Ошибка приглашения", show_alert=True)

        elif data == "lobby_stats":
            try:
                game_id = player_to_game.get(user_id)

                if game_id and game_id in games:
                    game = games[game_id]
                    players_list = "\n".join([
                        f"• {player.full_name}" + (" 👑" if player.user_id == game.creator_id else "")
                        for player in game.players.values()
                    ])

                    await query.message.reply_text(
                        f"📊 *Статистика лобби*\n\n"
                        f"*Игра:* {game.game_id}\n"
                        f"*Игроков:* {len(game.players)}/8\n"
                        f"*Создатель:* {game.players[game.creator_id].full_name}\n\n"
                        f"*Участники:*\n{players_list}",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Ошибка в lobby_stats: {e}")
                await query.answer("❌ Ошибка при загрузке статистики", show_alert=True)

        elif data == "lobby_leave":
            try:
                await leave_command(query.message, context)
            except Exception as e:
                logger.error(f"Ошибка в lobby_leave: {e}")
                await query.answer("❌ Ошибка при выходе из лобби", show_alert=True)
        # В функции button_callback, в разделе "=== ЛОББИ ===":

        elif data == "lobby_start_game":
            try:
                game_id = player_to_game.get(user_id)

                if not game_id or game_id not in games:
                    await query.answer("❌ Вы не в игре!", show_alert=True)
                    return

                game = games[game_id]

                if game.creator_id != user_id:
                    await query.answer("❌ Только создатель может начать игру!", show_alert=True)
                    return

                if len(game.players) < 2:
                    await query.answer("❌ Нужно хотя бы 2 игрока для начала!", show_alert=True)
                    return

                if game.start_game():
                    first_player = game.get_current_player()
                    players_list = "\n".join([
                        f"{i + 1}. {game.players[player_id].full_name}"
                        for i, player_id in enumerate(game.player_order)
                    ])

                    # Отправляем сообщение о начале игры
                    await query.message.edit_text(
                        f"🎮 *Игра началась!*\n\n"
                        f"*Порядок ходов:*\n{players_list}\n\n"
                        f"*Первый ходит:* {first_player.full_name}\n\n"
                        f"💰 *Стартовый капитал:* $1500 каждому\n"
                        f"📍 *Начальная позиция:* клетка 0 (СТАРТ)",
                        parse_mode="Markdown"
                    )

                    # Отправляем уведомления другим игрокам
                    for player_id, player in game.players.items():
                        if player_id != user_id:
                            try:
                                await context.bot.send_message(
                                    chat_id=player_id,
                                    text=f"🎮 *Игра началась!*\n\n"
                                         f"Создатель {query.from_user.full_name} начал игру.\n"
                                         f"Порядок ходов:\n{players_list}\n\n"
                                         f"*Первый ходит:* {first_player.full_name}\n\n"
                                         f"💰 *Ваш баланс:* $1500",
                                    parse_mode="Markdown"
                                )
                            except Exception as e:
                                logger.error(f"Не удалось отправить уведомление игроку {player_id}: {e}")

                    # Отправляем игровое меню
                    keyboard = get_game_actions_keyboard()
                    await query.message.reply_text(
                        "🎲 *Начните игру!*\n\n"
                        f"Первый ход у {first_player.full_name}\n"
                        f"Используйте кнопки ниже для управления игрой:",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    await query.answer("❌ Не удалось начать игру!", show_alert=True)
            except Exception as e:
                logger.error(f"Ошибка в lobby_start_game: {e}")
                await query.answer("❌ Ошибка при старте игры", show_alert=True)

        # === ИГРОВЫЕ ДЕЙСТВИЯ ===
        elif data == "game_roll_dice":
            try:
                game_id = player_to_game.get(user_id)

                if not game_id or game_id not in games:
                    await query.answer("❌ Вы не в игре!", show_alert=True)
                    return

                game = games[game_id]

                if game.state != "in_game":
                    await query.answer("❌ Игра еще не началась!", show_alert=True)
                    return

                current_player = game.get_current_player()
                if not current_player or current_player.user_id != user_id:
                    await query.answer(
                        f"❌ Сейчас ходит {current_player.full_name if current_player else 'другой игрок'}!",
                        show_alert=True
                    )
                    return

                # Бросок кубиков
                dice1, dice2, total = game.roll_dice()
                current_player.position = (current_player.position + total) % 40

                # Проверка прохода старта
                passed_start = current_player.position < total
                if passed_start:
                    current_player.money += 200

                response = f"🎲 *{current_player.full_name} бросает кубики:*\n"
                response += f"🎯 {dice1} + {dice2} = *{total}*\n\n"

                if passed_start:
                    response += f"💰 *Прошли СТАРТ!* +$200\n\n"

                response += f"📍 *Позиция {current_player.position}*\n"
                response += f"💰 *Баланс:* ${current_player.money}"

                # Проверка на дубль
                if dice1 == dice2:
                    response += "\n\n🎲 *Дубль! Ходите еще раз!*"
                    await query.answer("🎲 Дубль! Ходите еще раз!", show_alert=True)
                else:
                    game.next_turn()
                    next_player = game.get_current_player()
                    if next_player:
                        response += f"\n\n⏭️ *Следующий ход:* {next_player.full_name}"

                keyboard = get_game_actions_keyboard()
                await query.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка в game_roll_dice: {e}")
                await query.answer("❌ Ошибка при броске кубиков", show_alert=True)

        elif data == "game_view_board":
            try:
                game_id = player_to_game.get(user_id)

                if game_id and game_id in games:
                    game = games[game_id]

                    board_text = "🗺️ *Игровое поле*\n\n"
                    for player in game.players.values():
                        board_text += f"👤 *{player.full_name}* {player.color}: клетка {player.position}\n"

                    await query.message.edit_text(board_text, parse_mode="Markdown")
                else:
                    await query.answer("❌ Вы не в игре!", show_alert=True)
            except Exception as e:
                logger.error(f"Ошибка в game_view_board: {e}")
                await query.answer("❌ Ошибка при просмотре поля", show_alert=True)

        elif data == "game_my_properties":
            try:
                game_id = player_to_game.get(user_id)

                if not game_id or game_id not in games:
                    await query.answer("❌ Вы не в игре!", show_alert=True)
                    return

                game = games[game_id]
                player = game.players.get(user_id)

                if not player:
                    await query.answer("❌ Игрок не найден!", show_alert=True)
                    return

                response = f"🏘 *Собственность {player.full_name}*\n\n"
                response += f"💰 *Деньги:* ${player.money}\n"
                response += f"🏠 *Недвижимость:* {len(player.properties)} объектов\n"
                response += f"📍 *Позиция:* {player.position}"

                keyboard = get_game_actions_keyboard()
                await query.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка в game_my_properties: {e}")
                await query.answer("❌ Ошибка при просмотре свойств", show_alert=True)

        elif data == "game_leave":
            try:
                await leave_command(query.message, context)
            except Exception as e:
                logger.error(f"Ошибка в game_leave: {e}")
                await query.answer("❌ Ошибка при выходе из игры", show_alert=True)

        # Если кнопка не обработана
        else:
            logger.warning(f"Неизвестная кнопка: {data}")
            await query.answer("⚠️ Эта кнопка пока не работает", show_alert=True)

    except Exception as e:
        logger.error(f"Критическая ошибка обработки кнопки {data}: {e}")
        try:
            await query.answer("❌ Произошла критическая ошибка", show_alert=True)
        except:
            pass

# ========== ЗАПУСК БОТА ==========

def main():
    """Основная функция запуска бота"""
    # Ваш токен бота
    TOKEN = "8440935363:AAEe9pvkrYL3G-CLzcRXw9Qyy-aZLRVkX04"

    print("=" * 60)
    print("🚀 ЗАПУСК БОТА МОНОПОЛИИ")
    print(f"Токен: {TOKEN[:10]}...")
    print("=" * 60)

    # Создаем Application
    try:
        application = Application.builder().token(TOKEN).build()
        print("✅ Приложение создано")
    except Exception as e:
        print(f"❌ Ошибка создания приложения: {e}")
        return

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("newgame", newgame_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("games", games_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("leave", leave_command))
    application.add_handler(CommandHandler("startgame", start_game_command))


    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем бота
    print("✅ Бот запущен и готов к работе!")
    print("📱 Перейдите в Telegram и начните диалог с ботом")
    print("⚙️ Используйте команду /start в боте")
    print("=" * 60)

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n✋ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Создаем необходимые директории
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Запускаем бота
    main()