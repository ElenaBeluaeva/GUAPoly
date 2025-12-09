"""
🎮 БОТ МОНОПОЛИИ - РАБОТАЕТ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
"""

import os
import sys
import logging
import random
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Добавляем корень проекта и src/backend в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
src_backend_dir = os.path.join(current_dir, 'src', 'backend')

# Добавляем необходимые пути
sys.path.insert(0, current_dir)  # корень проекта
sys.path.insert(0, src_backend_dir)  # папка src/backend

# Теперь импортируем
from config import Config
from src.backend.game import Game, GameState
from src.backend.player import Player, PlayerStatus
from src.backend.board import Board, PropertyCell, StationCell, UtilityCell
from src.backend.game_manager import GameManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация
game_manager = GameManager()


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def format_money(amount: int) -> str:
    """Форматирование денег"""
    return f"${amount}"


def escape_markdown(text: str) -> str:
    """Экранирование для Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


# ========== КЛАВИАТУРЫ ==========

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("👥 Присоединиться", callback_data="menu_join_game")],
        [InlineKeyboardButton("📖 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_lobby_keyboard(game_id: str, is_creator: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура лобби"""
    keyboard = []

    if is_creator:
        keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data=f"lobby_start_{game_id}")])

    keyboard.extend([
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data=f"lobby_invite_{game_id}")],
        [InlineKeyboardButton("📊 Статистика лобби", callback_data=f"lobby_stats_{game_id}")],
        [InlineKeyboardButton("❌ Покинуть лобби", callback_data="lobby_leave")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_game_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура игровых действий"""
    keyboard = [
        [InlineKeyboardButton("🎲 Бросить кубики", callback_data="game_roll_dice")],
        [InlineKeyboardButton("🗺️ Посмотреть поле", callback_data="game_view_board")],
        [InlineKeyboardButton("🏠 Мои свойства", callback_data="game_my_properties")],
        [InlineKeyboardButton("👥 Игроки", callback_data="game_players")],
        [InlineKeyboardButton("❌ Выйти из игры", callback_data="game_leave")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ========== КОМАНДЫ БОТА ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user

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

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
    logger.info(f"Пользователь {user.id} начал работу")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /myid"""
    user = update.effective_user

    # Простой текст без Markdown
    response = f"🆔 Ваш ID: {user.id}\n"
    response += f"👤 Имя: {user.full_name}\n"
    response += f"📱 Username: @{user.username or 'нет'}\n"

    # Проверяем, есть ли игрок в игре через game_manager
    game = game_manager.get_player_game(user.id)
    if game:
        response += f"\n🎮 Текущая игра: {game.game_id}"
        response += f"\n👥 Игроков: {len(game.players)}/8"
        if game.state == GameState.IN_PROGRESS:
            response += f"\n🎲 Статус: Игра идет"
        else:
            response += f"\n🕓 Статус: В лобби"

    # Отправляем БЕЗ parse_mode
    await update.message.reply_text(response)
    logger.info(f"Пользователь {user.id} запросил свой ID")


async def newgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /newgame"""
    user = update.effective_user

    logger.info(f"Пользователь {user.id} пытается создать игру")

    # Создаем игру - передаем ВСЕ 3 аргумента
    game_id = game_manager.create_game(
        user.id,
        user.username or "Игрок",
        user.full_name
    )

    if not game_id:
        await update.message.reply_text("❌ Не удалось создать игру!")
        return

    # Получаем созданную игру
    game = game_manager.get_game(game_id)

    keyboard = get_lobby_keyboard(is_creator=True, game_id=game_id)
    await update.message.reply_text(
        f"🎮 Игра создана!\n\n"
        f"Код игры: {game_id}\n\n"
        f"Пригласите друзей:\n"
        f"Они могут присоединиться командой:\n"
        f"/join {game_id}\n\n"
        f"Игроки в лобби:\n"
        f"• {user.full_name} (👑 Создатель)\n\n"
        f"Статус: Ожидание игроков (1/8)",
        reply_markup=keyboard
    )
    logger.info(f"Игра {game_id} создана пользователем {user.id}")

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /join"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите код игры:\n/join ABC123"
        )
        return

    game_id = context.args[0].upper()
    user = update.effective_user

    logger.info(f"Пользователь {user.id} пытается присоединиться к игре {game_id}")

    # Проверяем через game_manager
    if game_manager.get_player_game(user.id):
        await update.message.reply_text(
            f"❌ Вы уже участвуете в игре!\n\n"
            f"Сначала покиньте текущую игру командой /leave"
        )
        return

    # Присоединяемся через game_manager
    if game_manager.join_game(game_id, user.id, user.username or "Игрок", user.full_name):
        game = game_manager.get_game(game_id)

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
            f"✅ Вы присоединились к игре {game_id}!\n\n"
            f"Игроки в лобби:\n{players_list}\n\n"
            f"Ожидайте начала игры от создателя.",
            reply_markup=keyboard
        )
        logger.info(f"Пользователь {user.id} присоединился к игре {game_id}")
    else:
        await update.message.reply_text(
            "❌ Не удалось присоединиться к игре!\n"
            "Возможные причины:\n"
            "• Игра уже началась\n"
            "• Достигнут лимит игроков (8)\n"
            "• Вы уже в другой игре"
        )

async def startgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /startgame"""
    user = update.effective_user

    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*",
            parse_mode="Markdown"
        )
        return

    if game.creator_id != user.id:
        await update.message.reply_text(
            f"❌ *Только создатель может начать игру!*\n"
            f"Создатель: {escape_markdown(game.players[game.creator_id].full_name)}",
            parse_mode="Markdown"
        )
        return

    if len(game.players) < 2:
        await update.message.reply_text(
            f"❌ *Нужно хотя бы 2 игрока!*\n"
            f"Сейчас: {len(game.players)} игрок",
            parse_mode="Markdown"
        )
        return

    # Начинаем игру
    if game_manager.start_game(game.game_id):
        first_player = game.get_current_player()

        # Формируем порядок ходов
        players_order = "\n".join([
            f"{i + 1}. {escape_markdown(game.players[player_id].full_name)}"
            for i, player_id in enumerate(game.player_order)
        ])

        start_message = f"""🚀 *ИГРА НАЧАЛАСЬ!*

*Порядок ходов:*
{players_order}

*Первый ходит:* {escape_markdown(first_player.full_name)}

💰 *Стартовый капитал:* ${Config.START_MONEY} каждому
📍 *Начальная позиция:* клетка 0 (СТАРТ)

🎲 Используйте команду /roll чтобы сделать ход!"""

        await update.message.reply_text(
            start_message,
            parse_mode="Markdown"
        )

        # Уведомляем всех игроков
        for player in game.players.values():
            if player.user_id != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=player.user_id,
                        text=f"🎮 *Игра началась!*\n\n"
                             f"Первый ходит: {escape_markdown(first_player.full_name)}\n"
                             f"Используйте /roll когда наступит ваш ход!",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить игрока {player.user_id}: {e}")

        logger.info(f"Игра {game.game_id} начата. Первый ходит: {first_player.full_name}")
    else:
        await update.message.reply_text(
            "❌ *Не удалось начать игру!*",
            parse_mode="Markdown"
        )


async def force_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /force_start - принудительный старт"""
    user = update.effective_user

    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*",
            parse_mode="Markdown"
        )
        return

    if game.creator_id != user.id:
        await update.message.reply_text(
            f"❌ *Только создатель может принудительно начать игру!*",
            parse_mode="Markdown"
        )
        return

    # Принудительный старт
    if game_manager.force_start_game(game.game_id, user.id):
        first_player = game.get_current_player()

        await update.message.reply_text(
            f"🚀 *Игра принудительно начата!*\n\n"
            f"Первый ходит: {escape_markdown(first_player.full_name)}\n\n"
            f"🎲 Используйте /roll чтобы сделать ход!",
            parse_mode="Markdown"
        )
        logger.info(f"Игра {game.game_id} принудительно начата пользователем {user.id}")
    else:
        await update.message.reply_text(
            "❌ *Не удалось принудительно начать игру!*",
            parse_mode="Markdown"
        )

# В начале файла с roll_command
from src.frontend.keyboards import get_game_actions_keyboard


async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /roll"""
    try:
        print(f"\n=== ROLL COMMAND STARTED ===")
        user = update.effective_user
        print(f"User ID: {user.id}, Name: {user.full_name}")

        game = game_manager.get_player_game(user.id)

        if not game:
            print("❌ ERROR: Game not found")
            await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
            return

        print(f"✅ Game found: {game.game_id}")

        # ОТЛАДКА GameState
        print(f"=== GameState DEBUG ===")
        print(f"game.state: {game.state}")
        print(f"game.state.value: '{game.state.value}'")
        print(f"GameState.IN_PROGRESS: {GameState.IN_PROGRESS}")
        print(f"GameState.IN_PROGRESS.value: '{GameState.IN_PROGRESS.value}'")
        print(f"game.state == GameState.IN_PROGRESS: {game.state == GameState.IN_PROGRESS}")
        print(f"game.state.value == 'in_game': {game.state.value == 'in_game'}")
        print(f"======================")

        print(f"Players: {list(game.players.keys())}")
        print(f"Player order: {game.player_order}")
        print(f"Current player index: {game.current_player_index}")

        # ИСПРАВЛЕННОЕ сравнение
        if game.state.value != "in_game":  # Сравниваем СТРОКОВЫЕ значения
            print(f"❌ ERROR: Game not in progress. State value: '{game.state.value}'")
            await update.message.reply_text("❌ *Игра еще не началась!*", parse_mode="Markdown")
            return

        print("✅ Game is in progress")

        current_player = game.get_current_player()
        print(f"Current player: {current_player.user_id if current_player else 'None'}")
        print(f"Current player name: {current_player.full_name if current_player else 'None'}")

        if not current_player:
            print("❌ ERROR: No current player")
            await update.message.reply_text("❌ *Нет текущего игрока!*", parse_mode="Markdown")
            return

        if current_player.user_id != user.id:
            print(f"❌ ERROR: Not player's turn")
            await update.message.reply_text(
                f"❌ *Сейчас не ваш ход!*\nХодит: {escape_markdown(current_player.full_name)}",
                parse_mode="Markdown"
            )
            return

        print("✅ It's player's turn")

        # Бросок кубиков
        dice1, dice2, total = game.roll_dice()
        print(f"🎲 Dice roll: {dice1} + {dice2} = {total}")

        # Перемещаем игрока
        move_result = game.move_player(current_player, total)
        print(f"📍 Move result: {move_result}")

        # Формируем ответ
        response = f"🎲 *{escape_markdown(current_player.full_name)} бросает кубики:*\n"
        response += f"🎯 {dice1} + {dice2} = *{total}*\n\n"

        if move_result.get("passed_start"):
            response += f"💰 *Прошли СТАРТ!* +${Config.SALARY}\n\n"

        response += f"📍 *Новая позиция:* {current_player.position}\n"
        response += f"💰 *Баланс:* ${current_player.money}"

        # Проверяем дубль
        if dice1 == dice2:
            response += "\n\n🎲 *Дубль! Ходите еще раз!*"
            print("🎲 Double! Player gets another turn")
        else:
            # Передаем ход
            game.next_turn()
            next_player = game.get_current_player()

            if next_player:
                response += f"\n\n⏭️ *Следующий ход:* {escape_markdown(next_player.full_name)}"
                print(f"⏭️ Next player: {next_player.full_name}")

        print(f"📤 Sending response to user...")

        # Отправляем сообщение
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=None
        )

        print("✅ Response sent successfully")

        # Сохраняем состояние (раскомментируйте когда будет работать)
        # game_manager.save_game_state(game.game_id)
        print("💾 Game state would be saved here")

        print(f"=== ROLL COMMAND FINISHED ===\n")

    except Exception as e:
        print(f"\n❌❌❌ CRITICAL ERROR in roll_command:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()

        try:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        except:
            pass

async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /leave"""
    user = update.effective_user

    if not game_manager.is_player_in_game(user.id):
        await update.message.reply_text(
            "❌ *Вы не в игре!*",
            parse_mode="Markdown"
        )
        return

    # Покидаем игру
    game_manager.leave_game(user.id)

    await update.message.reply_text(
        "👋 *Вы покинули игру!*",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
    logger.info(f"Пользователь {user.id} покинул игру")


async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /games"""
    available_games = game_manager.get_available_games()

    if not available_games:
        await update.message.reply_text(
            "📭 *Нет доступных игр в лобби.*\n"
            "Создайте новую игру: /newgame",
            parse_mode="Markdown"
        )
        return

    response = "🎮 *ДОСТУПНЫЕ ИГРЫ:*\n\n"

    for i, game in enumerate(available_games, 1):
        creator = game.players.get(game.creator_id)
        creator_name = escape_markdown(creator.full_name) if creator else "Неизвестно"

        response += (
            f"{i}. *Игра {game.game_id}*\n"
            f"   👑 Создатель: {creator_name}\n"
            f"   👥 Игроков: {len(game.players)}/{Config.MAX_PLAYERS}\n"
            f"   👉 Присоединиться: `/join {game.game_id}`\n"
            f"   {'─' * 20}\n"
        )

    await update.message.reply_text(response, parse_mode="Markdown")


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

*🎮 Основные команды:*
/start - Главное меню
/newgame - Новая игра
/join <код> - Присоединиться к игре
/startgame - Начать игру (для создателя)
/force_start - Принудительно начать
/roll - Бросить кубики
/myid - Узнать свой ID
/games - Список доступных игр
/leave - Покинуть игру
/help - Правила игры"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /status - статус игры"""
    user = update.effective_user

    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*",
            parse_mode="Markdown"
        )
        return

    response = f"🎮 *ИГРА {game.game_id}*\n"
    response += f"Статус: {'🎲 В процессе' if game.state == GameState.IN_PROGRESS else '🕓 В лобби'}\n\n"

    response += "👥 *ИГРОКИ:*\n"

    players_to_show = game.player_order if game.state == GameState.IN_PROGRESS else game.players.keys()

    for player_id in players_to_show:
        player = game.players.get(player_id)
        if not player:
            continue

        markers = []
        if game.state == GameState.IN_PROGRESS and game.get_current_player() and game.get_current_player().user_id == player_id:
            markers.append("🎲")
        if player.user_id == game.creator_id:
            markers.append("👑")
        if player.user_id == user.id:
            markers.append("👤 Вы")

        markers_str = " ".join(markers)

        response += (
            f"{markers_str} *{escape_markdown(player.full_name)}*\n"
            f"   💰 {format_money(player.money)} | 📍 {player.position}\n"
        )

    await update.message.reply_text(response, parse_mode="Markdown")


# ========== ОБРАБОТЧИКИ КНОПОК ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    try:
        # Главное меню
        if data == "menu_new_game":
            await newgame_command(query.message, context)

        elif data == "menu_join_game":
            await query.message.edit_text(
                "👥 *Присоединиться к игре*\n\n"
                "Введите команду:\n"
                "`/join КОД_ИГРЫ`\n\n"
                "Или посмотрите доступные игры: /games",
                parse_mode="Markdown"
            )

        elif data == "menu_rules":
            await help_command(query.message, context)

        elif data == "menu_profile":
            await myid_command(query.message, context)

        # Лобби
        elif data.startswith("lobby_start_"):
            game_id = data.replace("lobby_start_", "")
            await startgame_command(query.message, context)

        elif data.startswith("lobby_invite_"):
            game_id = data.replace("lobby_invite_", "")
            await query.message.reply_text(
                f"👥 *Приглашение в игру*\n\n"
                f"Код игры: `{game_id}`\n\n"
                f"Отправьте друзьям эту команду:\n"
                f"`/join {game_id}`",
                parse_mode="Markdown"
            )

        elif data.startswith("lobby_stats_"):
            game_id = data.replace("lobby_stats_", "")
            game = game_manager.get_game(game_id)

            if game:
                players_list = "\n".join([
                    f"• {escape_markdown(player.full_name)}" +
                    (" 👑" if player.user_id == game.creator_id else "")
                    for player in game.players.values()
                ])

                await query.message.reply_text(
                    f"📊 *Статистика лобби*\n\n"
                    f"🎮 Игра: `{game.game_id}`\n"
                    f"👥 Игроков: {len(game.players)}/{Config.MAX_PLAYERS}\n\n"
                    f"*Участники:*\n{players_list}",
                    parse_mode="Markdown"
                )

        elif data == "lobby_leave":
            await leave_command(query.message, context)

        # Игровые действия
        elif data == "game_roll_dice":
            await roll_command(query.message, context)

        elif data == "game_view_board":
            game = game_manager.get_player_game(user.id)
            if game:
                board_text = "🗺️ *Игровое поле*\n\n"
                for player in game.players.values():
                    board_text += f"{player.color} *{escape_markdown(player.full_name)}*: клетка {player.position}\n"

                await query.message.edit_text(board_text, parse_mode="Markdown")

        elif data == "game_my_properties":
            game = game_manager.get_player_game(user.id)
            if game:
                player = game.players.get(user.id)
                if player:
                    response = f"🏘 *Собственность {escape_markdown(player.full_name)}*\n\n"
                    response += f"💰 *Деньги:* {format_money(player.money)}\n"
                    response += f"📍 *Позиция:* {player.position}\n"

                    await query.message.edit_text(response, parse_mode="Markdown")

        elif data == "game_players":
            await status_command(query.message, context)

        elif data == "game_leave":
            await leave_command(query.message, context)

    except Exception as e:
        logger.error(f"Ошибка обработки кнопки {data}: {e}")
        await query.answer("⚠️ Произошла ошибка", show_alert=True)


async def properties_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полная рабочая версия /properties"""
    user = update.effective_user

    print(f"🔍 Пользователь {user.id} использует /properties")

    # Получаем игру пользователя
    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*\n\n"
            "Для просмотра собственности нужно быть в игре.\n\n"
            "📋 Как начать:\n"
            "1. `/newgame` - создать новую игру\n"
            "2. `/join КОД` - присоединиться к игре\n"
            "3. `/games` - посмотреть доступные игры",
            parse_mode="Markdown"
        )
        return

    print(f"✅ Игра найдена: {game.game_id}")

    # Получаем игрока
    player = game.players.get(user.id)

    if not player:
        await update.message.reply_text("❌ Ошибка: игрок не найден в игре!")
        return

    # Формируем ответ
    response = f"🏘 *СОБСТВЕННОСТЬ {getattr(player, 'name', 'Игрок')}*\n\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ОСНОВНАЯ ИНФОРМАЦИЯ
    response += f"💰 *Баланс:* ${getattr(player, 'money', 0)}\n"
    response += f"📍 *Позиция:* {getattr(player, 'position', 0)}\n"
    response += f"🎨 *Цвет фишки:* {getattr(player, 'color', '🎲')}\n"
    response += f"🎮 *Статус:* {getattr(getattr(player, 'status', None), 'value', 'активен')}\n\n"

    response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # УЛИЦЫ
    properties = getattr(player, 'properties', [])
    if properties:
        response += f"🏠 *УЛИЦЫ ({len(properties)}):*\n"
        for prop_id in properties:
            cell = game.board.get_cell(prop_id)
            if cell and hasattr(cell, 'name'):
                # Получаем информацию о домах
                houses_info = ""
                if hasattr(cell, 'houses') and cell.houses > 0:
                    if hasattr(cell, 'hotel') and cell.hotel:
                        houses_info = "🏨 ОТЕЛЬ"
                    else:
                        houses_info = f"🏠×{cell.houses}"

                # Получаем информацию о залоге
                mortgaged_info = "💳 ЗАЛОЖЕНА" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""

                response += f"• *{cell.name}*"
                if houses_info:
                    response += f" {houses_info}"
                if mortgaged_info:
                    response += f" {mortgaged_info}"
                response += f"\n"
    else:
        response += "🏠 *УЛИЦЫ:* нет\n"

    response += "\n"

    # ВОКЗАЛЫ
    stations = getattr(player, 'stations', [])
    if stations:
        response += f"🚂 *ВОКЗАЛЫ ({len(stations)}):*\n"
        for station_id in stations:
            cell = game.board.get_cell(station_id)
            if cell and hasattr(cell, 'name'):
                mortgaged_info = "💳 ЗАЛОЖЕН" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""
                response += f"• *{cell.name}* {mortgaged_info}\n"
    else:
        response += "🚂 *ВОКЗАЛЫ:* нет\n"

    response += "\n"

    # ПРЕДПРИЯТИЯ
    utilities = getattr(player, 'utilities', [])
    if utilities:
        response += f"⚡ *ПРЕДПРИЯТИЯ ({len(utilities)}):*\n"
        for util_id in utilities:
            cell = game.board.get_cell(util_id)
            if cell and hasattr(cell, 'name'):
                mortgaged_info = "💳 ЗАЛОЖЕНО" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""
                response += f"• *{cell.name}* {mortgaged_info}\n"
    else:
        response += "⚡ *ПРЕДПРИЯТИЯ:* нет\n"

    response += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # Если нет собственности
    if not properties and not stations and not utilities:
        response += "😢 *У вас пока нет собственности!*\n\n"
        response += "📋 *Советы для начала:*\n"
        response += "1. Бросайте кубики: `/roll`\n"
        response += "2. Покупайте свободную недвижимость: `/buy`\n"
        response += "3. Собирайте цветовые группы\n"
        response += "4. Стройте дома для увеличения ренты\n\n"

    # Статистика
    response += "📊 *СТАТИСТИКА:*\n"
    response += f"• Получено ренты: ${getattr(player, 'total_rent_received', 0)}\n"
    response += f"• Уплачено ренты: ${getattr(player, 'total_rent_paid', 0)}\n"
    response += f"• Куплено недвижимости: {len(properties)}\n"  # Используем количество property вместо отдельного счетчика
    response += f"• Карт освобождения: {getattr(player, 'get_out_of_jail_cards', 0)}\n"

    # Добавляем кнопки управления (если они есть)
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏗️ Управление домами", callback_data="manage_houses")],
            [InlineKeyboardButton("💳 Заложить собственность", callback_data="manage_mortgage")],
            [InlineKeyboardButton("🎮 Вернуться к игре", callback_data="back_game_actions")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_main_menu")]
        ])

        await update.message.reply_text(
            response,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except:
        # Если есть ошибки с кнопками, отправляем без них
        await update.message.reply_text(
            response,
            parse_mode="Markdown"
        )

    print(f"✅ Информация отправлена пользователю {user.id}")

async def jail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /jail - действия в тюрьме"""
    user = update.effective_user

    logger.info(f"Пользователь {user.id} использует /jail")

    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text(
            "❌ *Вы не в игре!*\n\n"
            "Сначала присоединитесь к игре:\n"
            "`/newgame` - создать игру\n"
            "`/join КОД` - присоединиться",
            parse_mode="Markdown"
        )
        return

    player = game.players.get(user.id)

    if not player:
        await update.message.reply_text("❌ Ошибка: игрок не найден!")
        return

    if player.status != PlayerStatus.IN_JAIL:
        await update.message.reply_text(
            "❌ *Вы не в тюрьме!*\n\n"
            f"📍 Ваша позиция: {player.position}\n"
            f"🎮 Статус: {player.status.value}",
            parse_mode="Markdown"
        )
        return

    keyboard = get_jail_keyboard()

    await update.message.reply_text(
        f"🔒 *ВЫ В ТЮРЬМЕ!*\n\n"
        f"Ход в тюрьме: {player.jail_turns + 1}/3\n\n"
        f"👤 *Игрок:* {player.full_name}\n"
        f"📍 *Позиция:* 10 (ТЮРЬМА)\n"
        f"💰 *Баланс:* {format_money(player.money)}\n\n"
        f"🎲 *Варианты выхода:*\n\n"
        f"1. 🎲 Попытаться выбросить дубль (бесплатно)\n"
        f"   • Бросить кубики и надеяться на дубль\n"
        f"   • Можно пытаться 3 раза\n"
        f"   • После 3-й неудачи нужно платить штраф\n\n"
        f"2. 💵 Заплатить ${Config.JAIL_FINE}\n"
        f"   • Немедленный выход\n"
        f"   • Требует наличия ${Config.JAIL_FINE}\n\n"
        f"3. 🎫 Использовать карту освобождения\n"
        f"   • Использовать карту 'Освобождение из тюрьмы'\n"
        f"   • Немедленный выход\n"
        f"   • Карты можно получить из Шанса/Казна\n\n"
        f"4. ⏳ Остаться еще ход\n"
        f"   • Пропустить ход\n"
        f"   • Можно остаться максимум 3 хода\n"
        f"   • После 3-го хода нужно платить штраф\n\n"
        f"🎮 *Доступные действия:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ========== ЗАПУСК БОТА ==========

def main():
    """Главная функция запуска бота"""
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА МОНОПОЛИИ")
    print(f"🔧 Бот работает для всех пользователей")
    print("=" * 60)

    try:
        app = Application.builder().token(Config.BOT_TOKEN).build()
    except Exception as e:
        print(f"❌ Ошибка создания приложения: {e}")
        return

    # Регистрируем команды
    commands = [
        ("start", start_command),
        ("myid", myid_command),
        ("newgame", newgame_command),
        ("join", join_command),
        ("startgame", startgame_command),
        ("force_start", force_start_command),
        ("roll", roll_command),
        ("leave", leave_command),
        ("games", games_command),
        ("help", help_command),
        ("status", status_command),
        ("properties", properties_command),  # ← ДОЛЖНА БЫТЬ ЗАРЕГИСТРИРОВАНА
        ("jail", jail_command),
        ("buy", buy_command),
    ]

    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))
        print(f"✅ /{cmd}")

    # Регистрируем кнопки
    app.add_handler(CallbackQueryHandler(button_handler))

    print("\n✅ Бот запущен и готов к работе!")
    print("📱 Перейдите в Telegram и начните диалог с ботом")
    print("=" * 60)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    main()