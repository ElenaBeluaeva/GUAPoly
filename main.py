"""
🎮 БОТ МОНОПОЛИИ - РАБОТАЕТ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
"""
from datetime import datetime
import os
import sys
import logging
import random
from datetime import datetime
# Для таймера очистки предложений
import asyncio
import io
from PIL import Image
from src.frontend.graphics import board_renderer

# При запуске бота добавьте задачу
# application.job_queue.run_repeating(clear_buy_offer, interval=30, first=10)

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

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
from src.backend.board import Board, PropertyCell, StationCell, UtilityCell, CellType
from src.backend.game_manager import GameManager
from src.frontend.combined_graphics import create_game_message_with_board, get_combined_board_bytes

# удалить потом
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

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
logger = logging.getLogger(__name__)


# Добавьте обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")

    if isinstance(context.error, telegram.error.TimedOut):
        # Если таймаут - пытаемся отправить простое текстовое сообщение
        try:
            await update.message.reply_text("⏳ Запрос занял слишком много времени. Попробуйте еще раз.")
        except:
            pass

# Инициализация
game_manager = GameManager()

def escape_markdown(text: str) -> str:
    """Экранирование для Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def format_money(amount: int) -> str:
    """Форматирование денег"""
    return f"₽{amount}"


def escape_markdown(text: str) -> str:
    """Экранирование для Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def mention_player(user_id: int, username: str, full_name: str) -> str:
    """Форматирует упоминание игрока"""
    if username:
        return f"@{username}"
    else:
        return f"[{full_name}](tg://user?id={user_id})"
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


async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /roll с интерактивными кнопками"""
    try:
        print(f"\n=== ROLL COMMAND STARTED ===")
        user = update.effective_user

        game = game_manager.get_player_game(user.id)

        if not game:
            await update.message.reply_text("❌ Вы не в игре!")
            return

        if game.state.value != "in_game":
            await update.message.reply_text("❌ Игра еще не началась!")
            return

        current_player = game.get_current_player()
        if not current_player:
            await update.message.reply_text("❌ Ошибка: текущий игрок не найден!")
            return

        # Проверяем, чей сейчас ход
        if current_player.user_id != user.id:
            await update.message.reply_text(
                f"❌ Сейчас не ваш ход!\n\n🎯 Сейчас ходит: {current_player.full_name}\n⏳ Ожидайте своей очереди"
            )
            return

        # Проверка тюрьмы
        if current_player.in_jail:
            jail_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Попытаться выбросить дубль", callback_data=f"jail_roll_{game.game_id}")],
                [InlineKeyboardButton("💵 Заплатить $200", callback_data=f"jail_pay_{game.game_id}")],
                [InlineKeyboardButton("🎫 Использовать карту", callback_data=f"jail_card_{game.game_id}")],
                [InlineKeyboardButton("⏳ Пропустить ход", callback_data=f"jail_skip_{game.game_id}")]
            ])

            await update.message.reply_text(
                f"🔒 Вы в тюрьме!\n\nХод в тюрьме: {current_player.jail_turns + 1}/3\n\nВыберите действие:",
                reply_markup=jail_keyboard
            )
            return

        # Бросок кубиков
        dice1, dice2, total = game.roll_dice()

        # Обработка дублей для тюрьмы
        if dice1 == dice2:
            game.double_count += 1
            if game.double_count >= 3:
                await update.message.reply_text(
                    f"🎲 Выброшен третий дубль!\n🎯 {dice1} + {dice2} = {total}\n\n🔒 Вы отправляетесь в тюрьму!"
                )
                current_player.go_to_jail()
                game.next_turn()
                game_manager.save_game_state(game.game_id)
                await notify_next_player(game, context, current_player.user_id)
                return
        else:
            game.double_count = 0

        # Перемещаем игрока
        old_position = current_player.position
        move_result = game.move_player(current_player, total)

        # Получаем клетку
        cell = game.board.get_cell(current_player.position)
        cell_action = game.process_cell_action(current_player, total)

        # Обработка отправки в тюрьму
        if cell_action.get("action") == "go_to_jail":
            current_player.position = 10
            current_player.in_jail = True
            current_player.jail_turns = 0

            jail_response = f"{current_player.color if hasattr(current_player, 'color') else '🎲'} {current_player.full_name} бросает кубики:\n"
            jail_response += f"🎯 {dice1} + {dice2} = {total}\n\n"

            if move_result.get("passed_start"):
                jail_response += f"💰 Прошли СТАРТ! +${Config.SALARY}\n\n"

            jail_response += f"📍 Перемещение: {old_position} → {current_player.position}\n"
            jail_response += f"💰 Баланс: ${current_player.money}\n\n"

            cell_name = cell.name if cell else "Неизвестно"
            jail_response += f"🏠 Клетка {current_player.position}: {cell_name}\n"
            jail_response += f"\n🔒 ВЫ ОТПРАВЛЕНЫ В ТЮРЬМУ!\n"
            jail_response += f"📍 Позиция: Тюрьма (клетка 10)\n"
            jail_response += f"📅 Круг: 1/3\n\n"
            jail_response += f"🎮 В следующий ваш ход используйте:\n"
            jail_response += f"• /jail - меню тюрьмы\n"
            jail_response += f"• /jail_pay - заплатить ${Config.JAIL_FINE}\n"
            jail_response += f"• /jail_roll - попытать удачу\n"
            jail_response += f"• /jail_card - использовать карту\n\n"

            # Передаем ход
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                next_color = next_player.color if hasattr(next_player, 'color') else '🎲'
                jail_response += f"⏭️ Ход переходит\n🎯 {next_color} {next_player.full_name}"

            await update.message.reply_text(jail_response)
            game_manager.save_game_state(game.game_id)
            return

        # Формируем текстовое сообщение
        response_lines = []

        # 1. Первая строка: имя игрока
        player_name = current_player.full_name
        player_icon = current_player.color if hasattr(current_player, 'color') else '🎲'
        response_lines.append(f"{player_icon} {player_name} бросает кубики:")

        # 2. Результат броска
        response_lines.append(f"🎯 {dice1} + {dice2} = {total}")
        response_lines.append("")

        # 3. Прошли старт
        if move_result.get("passed_start"):
            response_lines.append(f"💰 Прошли СТАРТ! +${Config.SALARY}")
            response_lines.append("")

        # 4. Перемещение и баланс
        response_lines.append(f"📍 Перемещение: {old_position} → {current_player.position}")
        response_lines.append(f"💰 Баланс: ${current_player.money}")
        response_lines.append("")

        # 5. Информация о клетке
        cell_name = cell.name if cell else "Неизвестно"
        response_lines.append(f"🏠 Клетка {current_player.position}: {cell_name}")

        # Подготавливаем данные для отображения
        players_data = []
        properties_data = {}

        for player_id, player in game.players.items():
            players_data.append({
                "id": player_id,
                "name": player.full_name,
                "position": player.position,
                "color": getattr(player, 'color', '🔴'),
                "money": player.money
            })

        for board_cell in game.board.cells:
            if hasattr(board_cell, 'owner_id') and board_cell.owner_id:
                properties_data[board_cell.id] = {
                    "owner": board_cell.owner_id,
                    "houses": getattr(board_cell, 'houses', 0),
                    "hotel": getattr(board_cell, 'hotel', False)
                }

        game_data = {
            "players": players_data,
            "properties": properties_data
        }

        # Создаем клавиатуру
        keyboard = None

        # Проверяем действия на клетке
        if cell_action["action"] == "buy_property":
            # Кнопки для покупки
            price = cell.price if hasattr(cell, 'price') else 0
            response_lines.append("")
            response_lines.append("🏠 СОБСТВЕННОСТЬ СВОБОДНА!")
            response_lines.append(f"🏷 {cell_name}")
            response_lines.append(f"💵 Цена покупки: ${price}")
            response_lines.append(f"💰 У вас: ${current_player.money}")
            response_lines.append("")

            if current_player.money >= price:
                response_lines.append("✅ Достаточно средств для покупки!")
            else:
                response_lines.append("❌ Недостаточно средств!")

            # Сохраняем информацию о покупке в user_data
            context.user_data[f'buy_offer_{game.game_id}_{current_player.position}'] = {
                'game_id': game.game_id,
                'position': current_player.position,
                'player_id': user.id,
                'price': price,
                'cell_name': cell_name,
                'player_name': player_name,
                'double': (dice1 == dice2),
                'timestamp': datetime.now()
            }

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"✅ Купить за ${price}",
                                      callback_data=f"buy_{game.game_id}_{current_player.position}"),
                 InlineKeyboardButton("❌ Пропустить",
                                      callback_data=f"skip_{game.game_id}_{current_player.position}")]
            ])


        elif cell_action["action"] == "pay_rent":

            rent = cell_action.get("rent", 0)

            owner_id = cell_action.get("owner_id")

            owner = game.players.get(owner_id) if owner_id else None

            if owner:

                response_lines.append("")

                response_lines.append("💸 Чужая собственность!")

                response_lines.append(f"👤 Владелец: {owner.full_name}")

                response_lines.append(f"💰 Рента: ${rent}")

                # Автоматически списываем ренту

                if current_player.deduct_money(rent):

                    owner.add_money(rent)

                    response_lines.append("✅ Рента уплачена")

                else:

                    response_lines.append("❌ Недостаточно средств!")

                    current_player.status = "bankrupt"

            # ПЕРЕДАЧА ХОДА БЕЗ КНОПКИ

            if dice1 != dice2:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response_lines.append("")
                    response_lines.append(f"⏭️ Ход переходит")
                    response_lines.append(
                        f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")
            else:
                response_lines.append("")
                response_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")

            # НЕ создаем клавиатуру - передача автоматическая

            keyboard = None


        elif cell_action["action"] == "pay_tax":
            tax = cell_action.get("amount", 0)
            response_lines.append
            response_lines.append(f"💸 Налог: ${tax}")
            if current_player.deduct_money(tax):
                game.free_parking_pot += tax
                response_lines.append("✅ Налог уплачен")
            else:
                response_lines.append("❌ Недостаточно средств!")
            # ПЕРЕДАЧА ХОДА БЕЗ КНОПКИ
            if dice1 != dice2:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response_lines.append("")
                    response_lines.append(f"⏭️ Ход переходит")
                    response_lines.append(
                        f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")
            else:
                response_lines.append("")
                response_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")
            # НЕ создаем клавиатуру
            keyboard = None


        elif cell_action["action"] == "free_parking":
            response_lines.append("")
            if game.free_parking_pot > 0:
                amount = game.free_parking_pot
                current_player.add_money(amount)
                game.free_parking_pot = 0
                response_lines.append("🎉 Бесплатная стоянка!")
                response_lines.append(f"💰 Вы получаете: ${amount}")
            else:
                response_lines.append("🅿️ Бесплатная стоянка")
                response_lines.append("💰 В банке: $0")
            # ПЕРЕДАЧА ХОДА БЕЗ КНОПКИ
            if dice1 != dice2:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response_lines.append("")
                    response_lines.append(f"⏭️ Ход переходит")
                    response_lines.append(
                        f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")
            else:
                response_lines.append("")
                response_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")
            # НЕ создаем клавиатуру
            keyboard = None



        elif cell_action["action"] in ["chance_card", "chest_card"]:
            card = cell_action.get("card")
            if card:
                response_lines.append("")
                card_text = card.get('text', '')
                response_lines.append(f"🎯 {card_text}")
                # Применяем действие карты
                card_result = game.apply_card_action(current_player, card)
                if card_result.get("message"):
                    card_msg = card_result['message']
                    response_lines.append(f"📝 {card_msg}")
            # ПЕРЕДАЧА ХОДА БЕЗ КНОПКИ
            if dice1 != dice2:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response_lines.append("")
                    response_lines.append(f"⏭️ Ход переходит")
                    response_lines.append(
                        f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")
            else:
                response_lines.append("")
                response_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")
            # НЕ создаем клавиатуру
            keyboard = None


        else:
            # Для остальных действий
            if dice1 != dice2:
                game.next_turn()
                next_player = game.get_current_player()
                if next_player:
                    response_lines.append("")
                    response_lines.append(f"⏭️ Ход переходит")
                    response_lines.append(
                        f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")
            else:
                response_lines.append("")
                response_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")
            # НЕ создаем клавиатуру
            keyboard = None
        # Создаем текстовое сообщение
        text_message = "\n".join(response_lines)

        try:
            # Создаем изображение игрового поля БЕЗ текста
            board_image = board_renderer.render_board(game_data)
            img_bytes = board_renderer.save_to_bytes(board_image)

            # Отправляем изображение с текстом как подпись
            if keyboard:
                await update.message.reply_photo(
                    photo=img_bytes,
                    caption=text_message[:1024],
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_photo(
                    photo=img_bytes,
                    caption=text_message[:1024]
                )

        except Exception as e:
            print(f"❌ Ошибка создания изображения: {e}")
            # Запасной вариант
            if keyboard:
                await update.message.reply_text(text_message, reply_markup=keyboard)
            else:
                await update.message.reply_text(text_message)

        # Сохраняем игру
        game_manager.save_game_state(game.game_id)

        print(f"=== ROLL COMMAND FINISHED ===\n")

    except Exception as e:
        print(f"\n❌❌❌ Ошибка в roll_command:")
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Сообщение: {str(e)}")
        import traceback
        traceback.print_exc()

        try:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        except:
            pass


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для покупки собственности с отображением на поле"""
    try:
        user = update.effective_user
        print(f"\n=== BUY COMMAND STARTED ===")

        # Проверяем активное предложение покупки
        buy_offer = context.user_data.get('buy_offer')

        if not buy_offer:
            await update.message.reply_text(
                "❌ Нет активного предложения покупки!\n\n"
                "Используйте /buy только когда вам предложили купить собственность."
            )
            return

        # Проверяем, что предложение для этого игрока
        if buy_offer.get('player_id') != user.id:
            await update.message.reply_text("❌ Это предложение покупки не для вас!")
            return

        # Получаем игру
        game = game_manager.get_game(buy_offer['game_id'])
        if not game:
            await update.message.reply_text("❌ Игра не найдена!")
            return

        player = game.players.get(user.id)
        if not player:
            await update.message.reply_text("❌ Игрок не найден!")
            return

        # Покупаем собственность
        success = game.board.buy_property(player, buy_offer['position'])

        # Очищаем предложение покупки
        context.user_data.pop('buy_offer', None)

        # Подготавливаем данные для отображения
        players_data = []
        properties_data = {}

        for player_id, game_player in game.players.items():
            players_data.append({
                "id": player_id,
                "name": game_player.full_name,
                "position": game_player.position,
                "color": getattr(game_player, 'color', '🔴'),
                "money": game_player.money
            })

        # Собираем обновленную информацию о собственности
        for board_cell in game.board.cells:
            if hasattr(board_cell, 'owner_id') and board_cell.owner_id:
                properties_data[board_cell.id] = {
                    "owner": board_cell.owner_id,
                    "houses": getattr(board_cell, 'houses', 0),
                    "hotel": getattr(board_cell, 'hotel', False)
                }

        game_data = {
            "players": players_data,
            "properties": properties_data
        }

        cell = game.board.get_cell(buy_offer['position'])
        cell_name = cell.name if cell else "недвижимость"

        if success:
            # Формируем сообщение об успешной покупке с ДОПОЛНИТЕЛЬНЫМ ТЕКСТОМ
            text_lines = []
            text_lines.append("✅ ПОКУПКА ОФОРМЛЕНА!")
            text_lines.append("")
            text_lines.append(f"🏠 Вы купили {cell_name}")
            text_lines.append(f"💰 Потрачено: ${cell.price if hasattr(cell, 'price') else 0}")
            text_lines.append(f"🏦 Остаток: ${player.money}")
            text_lines.append("")

            # Считаем количество собственности
            properties_count = len(getattr(player, 'properties', []))
            stations_count = len(getattr(player, 'stations', []))
            utilities_count = len(getattr(player, 'utilities', []))

            text_lines.append("🎲 Теперь у вас:")
            text_lines.append(f"• Улиц: {properties_count}")
            text_lines.append(f"• Вокзалов: {stations_count}")
            text_lines.append(f"• Предприятий: {utilities_count}")
            text_lines.append("")

            # ДОБАВЛЯЕМ НОВЫЙ ТЕКСТ - информация о клетке
            text_lines.append("📊 Информация о купленной собственности:")

            # Добавляем информацию о типе клетки
            if cell.type == CellType.PROPERTY:
                text_lines.append(f"🏘 Тип: Улица")
                if hasattr(cell, 'color_group'):
                    text_lines.append(f"🎨 Цвет: {cell.color_group}")
                if hasattr(cell, 'rent'):
                    text_lines.append(f"💵 Базовая рента: ${cell.rent}")
                    if hasattr(cell, 'rent_with_houses'):
                        text_lines.append(f"🏠 Рента с домами:")
                        for i in range(1, 5):
                            text_lines.append(f"   • {i} дом: ${cell.rent_with_houses[i - 1]}")
                        if hasattr(cell, 'rent_with_hotel'):
                            text_lines.append(f"   • 🏨 Отель: ${cell.rent_with_hotel}")
            elif cell.type == CellType.STATION:
                text_lines.append(f"🚂 Тип: Вокзал")
                if hasattr(cell, 'rent'):
                    text_lines.append(f"💵 Базовая рента: ${cell.rent}")
                    if hasattr(cell, 'rent_multipliers'):
                        text_lines.append(f"📈 Множители ренты:")
                        for i, multiplier in enumerate(cell.rent_multipliers, 1):
                            text_lines.append(f"   • {i} вокзал: ×{multiplier}")
            elif cell.type == CellType.UTILITY:
                text_lines.append(f"⚡ Тип: Предприятие")
                text_lines.append(f"🎲 Рента зависит от броска кубиков")
                if hasattr(cell, 'rent_multipliers'):
                    text_lines.append(f"📊 Множители:")
                    text_lines.append(f"   • 1 предприятие: ×{cell.rent_multipliers[0]}")
                    text_lines.append(f"   • 2 предприятия: ×{cell.rent_multipliers[1]}")

            text_lines.append("")

            # Добавляем советы
            text_lines.append("💡 Советы по управлению:")
            if cell.type == CellType.PROPERTY:
                # Проверяем, есть ли у игрока другие улицы того же цвета
                color_group_cells = [c for c in game.board.cells
                                     if hasattr(c, 'color_group')
                                     and c.color_group == cell.color_group]
                player_owns_in_group = sum(1 for c in color_group_cells
                                           if hasattr(c, 'owner_id')
                                           and c.owner_id == player.user_id)
                total_in_group = len(color_group_cells)

                text_lines.append(f"• Эта улица - часть группы {cell.color_group}")
                text_lines.append(f"• У вас {player_owns_in_group} из {total_in_group} улиц в этой группе")

                if player_owns_in_group == total_in_group:
                    text_lines.append("🎉 Вы собрали всю цветовую группу!")
                    text_lines.append("🏗️ Теперь можете строить дома!")
                else:
                    text_lines.append(f"📝 Для постройки домов нужно собрать все {total_in_group} улицы")

            elif cell.type == CellType.STATION:
                text_lines.append("• Каждый дополнительный вокзал увеличивает ренту")
                text_lines.append("• Старайтесь покупать все 4 вокзала для максимальной прибыли")

            elif cell.type == CellType.UTILITY:
                text_lines.append("• Рента зависит от суммы на кубиках")
                text_lines.append("• Владейте обоими предприятиями для увеличения дохода")

            text_lines.append("")
            text_lines.append("🎮 Что дальше:")
            if buy_offer.get('double'):
                text_lines.append("🎲 ДУБЛЬ! Ходите еще раз!")
            else:
                text_lines.append("⏭️ Ход переходит следующему игроку")

            # Создаем изображение
            text_message = "\n".join(text_lines)
            board_image = board_renderer.render_board(game_data)
            img_bytes = board_renderer.save_to_bytes(board_image)

            # Отправляем изображение с результатом покупки
            await update.message.reply_photo(
                photo=img_bytes,
                caption=text_message[:1024]  # Ограничение Telegram для подписи
            )

            # Если текст слишком длинный, отправляем остальное отдельным сообщением
            if len(text_message) > 1024:
                remaining_text = text_message[1024:]
                # Разбиваем на части по 4000 символов (ограничение Telegram)
                for i in range(0, len(remaining_text), 4000):
                    await update.message.reply_text(remaining_text[i:i + 4000])

            # Уведомляем других игроков
            for other_id, other_player in game.players.items():
                if other_id != user.id:
                    try:
                        other_text = f"🏠 {player.full_name} купил(а) {cell_name}!"

                        # Добавляем дополнительную информацию для других игроков
                        if cell.type == CellType.PROPERTY and hasattr(cell, 'color_group'):
                            other_text += f"\n🎨 Группа: {cell.color_group}"
                        other_text += f"\n💰 Цена: ${cell.price if hasattr(cell, 'price') else 0}"

                        other_board_image = board_renderer.render_board(game_data)
                        other_img_bytes = board_renderer.save_to_bytes(other_board_image)

                        await context.bot.send_photo(
                            chat_id=other_id,
                            photo=other_img_bytes,
                            caption=other_text
                        )
                    except Exception as e:
                        print(f"❌ Не удалось уведомить игрока {other_id}: {e}")

            # Переход хода (если не дубль)
            if not buy_offer.get('double'):
                game.next_turn()
                next_player = game.get_current_player()

                if next_player:
                    try:
                        # Уведомляем следующего игрока с изображением
                        next_text = f"🎯 Ваш ход!\n\nИспользуйте /roll"
                        next_board_image = board_renderer.render_board(game_data)
                        next_img_bytes = board_renderer.save_to_bytes(next_board_image)

                        await context.bot.send_photo(
                            chat_id=next_player.user_id,
                            photo=next_img_bytes,
                            caption=next_text
                        )
                    except Exception as e:
                        print(f"❌ Не удалось уведомить следующего игрока: {e}")

                    # Добавляем сообщение о передаче хода текущему игроку
                    transfer_text = f"⏭️ Ход переходит\n🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}"
                    await update.message.reply_text(transfer_text)
            else:
                # При дубле игрок ходит еще раз
                double_text = f"🎲 ДУБЛЬ!\n🎯 Ходите еще раз!\n\nИспользуйте /roll"
                double_board_image = board_renderer.render_board(game_data)
                double_img_bytes = board_renderer.save_to_bytes(double_board_image)

                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=double_img_bytes,
                    caption=double_text
                )

            print(f"=== BUY COMMAND FINISHED SUCCESS ===")

        else:
            # Покупка не удалась
            text_lines = []
            text_lines.append("❌ НЕ УДАЛОСЬ КУПИТЬ!")
            text_lines.append("")
            text_lines.append(f"🏠 {cell_name}")
            text_lines.append("")
            text_lines.append("📋 Возможные причины:")
            text_lines.append("1. Недостаточно денег")
            text_lines.append("2. Собственность уже куплена")
            text_lines.append("3. Ошибка системы")

            text_message = "\n".join(text_lines)

            # Создаем изображение для неудачной покупки
            board_image = board_renderer.render_board(game_data)
            img_bytes = board_renderer.save_to_bytes(board_image)

            await update.message.reply_photo(
                photo=img_bytes,
                caption=text_message[:1024]
            )

        # Сохраняем игру
        game_manager.save_game_state(game.game_id)

    except Exception as e:
        print(f"❌ ERROR in buy_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Ошибка при покупке: {str(e)}")


async def notify_next_player(game, context, current_user_id=None):
    """Уведомляет следующего игрока о его ходе - БЕЗ Markdown"""
    next_player = game.get_current_player()

    if not next_player:
        print("⚠️ Следующий игрок не найден")
        return

    # Проверяем, что это не тот же игрок (при дубле)
    if current_user_id and next_player.user_id == current_user_id:
        print(f"⚠️ Next player is the same ({next_player.full_name}), skipping notification")
        return  # Не уведомляем того же игрока

    print(f"📨 Отправляем уведомление игроку {next_player.full_name} (ID: {next_player.user_id})")

    # Подготавливаем данные для изображения
    players_data = []
    properties_data = {}

    for player_id, player in game.players.items():
        players_data.append({
            "id": player_id,
            "name": player.full_name,
            "position": player.position,
            "color": getattr(player, 'color', '🔴'),
            "money": player.money
        })

    # Собираем информацию о собственности
    for cell in game.board.cells:
        if hasattr(cell, 'owner_id') and cell.owner_id:
            properties_data[cell.id] = {
                "owner": cell.owner_id,
                "houses": getattr(cell, 'houses', 0),
                "hotel": getattr(cell, 'hotel', False)
            }

    game_data = {
        "players": players_data,
        "properties": properties_data
    }

    try:
        # Создаем изображение игрового поля
        board_image = board_renderer.render_board(game_data)
        img_bytes = board_renderer.save_to_bytes(board_image)

        # Отправляем личное сообщение с изображением
        next_player_color = next_player.color if hasattr(next_player, 'color') else '🎲'
        caption = f"🎯 ВАШ ХОД, {next_player.full_name}!\n\n"
        caption += f"📊 Игроков: {len(game.players)}\n"
        caption += f"💰 Ваш баланс: ${next_player.money}\n\n"
        caption += f"Используйте /roll чтобы бросить кубики"

        await context.bot.send_photo(
            chat_id=next_player.user_id,
            photo=img_bytes,
            caption=caption
        )
        print(f"✅ Уведомление с изображением отправлено игроку {next_player.full_name}")

    except Exception as e:
        print(f"❌ Не удалось отправить уведомление с изображением игроку {next_player.user_id}: {e}")

        # Запасной вариант - текстовое сообщение
        try:
            await context.bot.send_message(
                chat_id=next_player.user_id,
                text=f"🎯 Ваш ход, {next_player.full_name}!\n\nИспользуйте /roll для броска кубиков"
            )
            print(f"✅ Текстовое уведомление отправлено игроку {next_player.full_name}")
        except Exception as e2:
            print(f"❌ Не удалось отправить текстовое уведомление: {e2}")

async def send_combined_game_board(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   game, caption: str = "🎮 Текущее состояние игры",
                                   player_color: str = "🔴") -> bool:
    """Отправляет совмещенное изображение игрового поля с текстом"""
    try:
        # Подготавливаем данные для рендерера
        players_data = []
        properties_data = {}

        for player_id, player in game.players.items():
            players_data.append({
                "id": player_id,
                "name": player.full_name,
                "position": player.position,
                "color": getattr(player, 'color', '🔴'),
                "money": player.money
            })

        # Собираем информацию о собственности
        for cell in game.board.cells:
            if hasattr(cell, 'owner_id') and cell.owner_id:
                properties_data[cell.id] = {
                    "owner": cell.owner_id,
                    "houses": getattr(cell, 'houses', 0),
                    "hotel": getattr(cell, 'hotel', False)
                }

        # Генерируем совмещенное изображение
        game_data = {
            "players": players_data,
            "properties": properties_data
        }

        combined_bytes = get_combined_board_bytes(game_data, caption, player_color)

        # Отправляем в Telegram
        if update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=combined_bytes,
                caption=caption[:1024],  # Ограничение Telegram
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_photo(
                photo=combined_bytes,
                caption=caption[:1024],
                parse_mode="Markdown"
            )

        return True

    except Exception as e:
        print(f"❌ Ошибка при отправке совмещенного поля: {e}")
        import traceback
        traceback.print_exc()
        return False


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для пропуска покупки"""
    try:
        user = update.effective_user
        print(f"\n=== SKIP COMMAND STARTED ===")

        # Проверяем активное предложение покупки
        buy_offer = context.user_data.get('buy_offer')

        if not buy_offer:
            await update.message.reply_text(
                "❌ Нет активного предложения покупки!\n\n"
                "Используйте /skip только когда вам предложили купить собственность."
            )
            return

        # Проверяем, что предложение для этого игрока
        if buy_offer.get('player_id') != user.id:
            await update.message.reply_text("❌ Это предложение покупки не для вас!")
            return

        # Получаем игру
        game = game_manager.get_game(buy_offer['game_id'])
        if not game:
            await update.message.reply_text("❌ Игра не найдена!")
            return

        player = game.players.get(user.id)
        if not player:
            await update.message.reply_text("❌ Игрок не найден!")
            return

        cell = game.board.get_cell(buy_offer['position'])

        # Очищаем предложение покупки
        context.user_data.pop('buy_offer', None)

        # Формируем текст уведомления
        response_lines = []
        response_lines.append("⏭️ ПОКУПКА ПРОПУЩЕНА")
        response_lines.append("")
        response_lines.append(f"🏠 Вы отказались от {cell.name if cell else 'недвижимости'}")
        response_lines.append(f"💰 Цена: ${cell.price if hasattr(cell, 'price') else 0}")
        response_lines.append(f"🏦 Ваш баланс: ${player.money}")

        # Проверяем дубль
        if buy_offer.get('double'):
            response_lines.append("")
            response_lines.append("🎲 ДУБЛЬ!")
            response_lines.append("🎯 Ходите еще раз!")
            response_lines.append("")
            response_lines.append("Используйте /roll")
            # При дубле НЕ передаем ход
        else:
            # Переход хода ТОЛЬКО если не дубль
            game.next_turn()
            next_player = game.get_current_player()

            response_lines.append("")
            response_lines.append("⏭️ Ход переходит")
            response_lines.append(
                f"🎯 {next_player.color if hasattr(next_player, 'color') else '🎲'} {next_player.full_name}")

            # Уведомляем следующего игрока
            if next_player and next_player.user_id != user.id:  # Проверяем, что это не тот же игрок
                try:
                    await context.bot.send_message(
                        chat_id=next_player.user_id,
                        text=f"🎯 Ваш ход!\n\nИспользуйте /roll"
                    )
                except Exception as e:
                    print(f"❌ Не удалось уведомить следующего игрока: {e}")

        text_message = "\n".join(response_lines)

        # Отправляем сообщение
        await update.message.reply_text(text_message)

        # Сохраняем игру
        game_manager.save_game_state(game.game_id)

        print(f"=== SKIP COMMAND FINISHED SUCCESS ===")

    except Exception as e:
        print(f"❌ ERROR in skip_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Ошибка при пропуске: {str(e)}")

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
        # Цвет игрока (добавляем в начало)
        if hasattr(player, 'color'):
            markers.append(player.color)

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
        # Проверяем, относится ли кнопка к игровым действиям
        if any(data.startswith(prefix) for prefix in ["buy_", "skip_", "pass_turn_", "jail_"]):
            # Получаем game_id из callback_data
            game_id = None
            if data.startswith("buy_") or data.startswith("skip_") or data.startswith("pass_turn_"):
                parts = data.split("_")
                if len(parts) >= 2:
                    game_id = parts[1]
            elif data.startswith("jail_"):
                parts = data.split("_")
                if len(parts) >= 3:  # jail_roll_GAME_ID или jail_pay_GAME_ID
                    game_id = parts[2]
                else:
                    await query.answer("❌ Неверный формат callback_data", show_alert=True)
                    return

            if not game_id:
                await query.answer("❌ Не удалось определить игру", show_alert=True)
                return

            # Получаем игру
            game = game_manager.get_game(game_id)
            if not game:
                await query.answer("❌ Игра не найдена", show_alert=True)
                return

            # Проверяем, что пользователь в этой игре
            player = game.players.get(user.id)
            if not player:
                await query.answer("❌ Вы не в этой игре", show_alert=True)
                return

            # Проверяем, чей сейчас ход
            current_player = game.get_current_player()
            if not current_player:
                await query.answer("❌ Нет текущего игрока", show_alert=True)
                return

            # Проверяем, что кнопку нажимает игрок, чей сейчас ход
            if current_player.user_id != user.id:
                current_player_name = current_player.full_name
                await query.answer(
                    f"⏳ Сейчас ходит {current_player_name}! Ждите своей очереди.",
                    show_alert=True
                )
                return

        # Обработка кнопки "Купить"
        if data.startswith("buy_"):
            parts = data.split("_")
            if len(parts) >= 3:
                game_id = parts[1]
                position = int(parts[2])

                game = game_manager.get_game(game_id)
                if not game:
                    await query.answer("❌ Игра не найдена", show_alert=True)
                    return

                player = game.players.get(user.id)
                if not player:
                    await query.answer("❌ Вы не в этой игре", show_alert=True)
                    return

                # Дополнительная проверка на текущего игрока (уже проверено выше, но для надежности)
                current_player = game.get_current_player()
                if current_player and current_player.user_id != user.id:
                    await query.answer(f"❌ Сейчас ходит {current_player.full_name}!", show_alert=True)
                    return

                cell = game.board.get_cell(position)
                if not cell:
                    await query.answer("❌ Клетка не найдена", show_alert=True)
                    return

                # Проверяем, что клетка свободна
                if cell.owner_id:
                    await query.answer("❌ Собственность уже куплена", show_alert=True)
                    return

                # Проверяем деньги
                price = cell.price if hasattr(cell, 'price') else 0
                if player.money < price:
                    await query.answer(f"❌ Недостаточно денег! Нужно ${price}", show_alert=True)
                    return

                # Покупаем собственность
                success = game.board.buy_property(player, position)

                if success:
                    # Очищаем предложение покупки
                    key = f'buy_offer_{game_id}_{position}'
                    context.user_data.pop(key, None)

                    # Проверяем дубль
                    double = False
                    buy_offer_key = f'buy_offer_{game_id}_{position}'
                    if buy_offer_key in context.user_data:
                        double = context.user_data[buy_offer_key].get('double', False)
                        context.user_data.pop(buy_offer_key, None)

                    # Формируем основной текст
                    text_lines = []
                    text_lines.append(f"✅ {player.full_name} купил(а) {cell.name} за ${price}!")
                    text_lines.append("")
                    text_lines.append(f"💰 Баланс: ${player.money}")
                    text_lines.append("")

                    # Считаем количество собственности
                    properties_count = len(getattr(player, 'properties', []))
                    stations_count = len(getattr(player, 'stations', []))
                    utilities_count = len(getattr(player, 'utilities', []))

                    text_lines.append("🎲 Теперь у вас:")
                    text_lines.append(f"• Улиц: {properties_count}")
                    text_lines.append(f"• Вокзалов: {stations_count}")
                    text_lines.append(f"• Предприятий: {utilities_count}")
                    text_lines.append("")

                    if not double:
                        # Переход хода
                        game.next_turn()

                        # Получаем следующего игрока
                        next_player = game.get_current_player()
                        if next_player:
                            text_lines.append(f"⏭️ Ход переходит")
                            text_lines.append(f"🎯 {next_player.full_name}")

                    else:
                        # При дубле игрок ходит еще раз
                        text_lines.append("🎲 ДУБЛЬ!")
                        text_lines.append("🎯 Ходите еще раз!")
                        text_lines.append("")
                        text_lines.append("Используйте /roll")

                    # Объединяем все строки
                    final_response = "\n".join(text_lines)

                    # Обновляем сообщение
                    await query.edit_message_caption(
                        caption=final_response,
                        parse_mode=None,
                        reply_markup=None
                    )

                    if not double:
                        # Уведомляем следующего игрока
                        next_player = game.get_current_player()
                        if next_player:
                            await notify_next_player(game, context, user.id)
                    else:
                        # При дубле отправляем сообщение игроку
                        await context.bot.send_message(
                            chat_id=user.id,
                            text=f"🎲 ДУБЛЬ!\n🎯 Ходите еще раз!\n\nИспользуйте /roll"
                        )

                    game_manager.save_game_state(game_id)

                    # Уведомляем других игроков
                    for other_id, other_player in game.players.items():
                        if other_id != user.id:
                            try:
                                next_player_info = ""
                                if not double:
                                    next_player = game.get_current_player()
                                    if next_player:
                                        next_player_info = f"\n⏭️ Следующий ход: {next_player.full_name}"

                                await context.bot.send_message(
                                    chat_id=other_id,
                                    text=f"🏠 {player.full_name} купил(а) {cell.name} за ${price}!\n"
                                         f"💰 Баланс игрока: ${player.money}"
                                         f"{next_player_info}"
                                )
                            except Exception as e:
                                print(f"❌ Не удалось уведомить игрока {other_id}: {e}")

                else:
                    await query.answer("❌ Не удалось купить", show_alert=True)

        # Обработка кнопки "Пропустить"
        elif data.startswith("skip_"):
            parts = data.split("_")
            if len(parts) >= 3:
                game_id = parts[1]
                position = int(parts[2])

                game = game_manager.get_game(game_id)
                if not game:
                    await query.answer("❌ Игра не найдена", show_alert=True)
                    return

                player = game.players.get(user.id)
                if not player:
                    await query.answer("❌ Вы не в этой игре", show_alert=True)
                    return

                cell = game.board.get_cell(position)
                if not cell:
                    await query.answer("❌ Клетка не найдена", show_alert=True)
                    return

                # Очищаем предложение покупки
                key = f'buy_offer_{game_id}_{position}'
                context.user_data.pop(key, None)

                # Проверяем дубль
                double = False
                buy_offer_key = f'buy_offer_{game_id}_{position}'
                if buy_offer_key in context.user_data:
                    double = context.user_data[buy_offer_key].get('double', False)
                    context.user_data.pop(buy_offer_key, None)

                # Формируем текст
                text_lines = []
                text_lines.append(f"⏭️ {player.full_name} пропустил(а) покупку {cell.name}")
                text_lines.append("")
                text_lines.append(f"💵 Цена: ${cell.price if hasattr(cell, 'price') else 0}")
                text_lines.append(f"💰 Ваш баланс: ${player.money}")
                text_lines.append("")

                if not double:
                    # Переход хода ТОЛЬКО если не дубль
                    game.next_turn()

                    # Получаем следующего игрока
                    next_player = game.get_current_player()
                    if next_player:
                        text_lines.append(f"⏭️ Ход переходит")
                        text_lines.append(f"🎯 {next_player.full_name}")

                else:
                    # При дубле игрок ходит еще раз
                    text_lines.append("🎲 ДУБЛЬ!")
                    text_lines.append("🎯 Ходите еще раз!")
                    text_lines.append("")
                    text_lines.append("Используйте /roll")

                # Объединяем все строки
                final_response = "\n".join(text_lines)

                # Обновляем сообщение
                await query.edit_message_caption(
                    caption=final_response,
                    parse_mode=None,
                    reply_markup=None
                )

                if not double:
                    # Уведомляем следующего игрока ТОЛЬКО если не дубль
                    next_player = game.get_current_player()
                    if next_player and next_player.user_id != user.id:
                        try:
                            await notify_next_player(game, context, user.id)
                        except Exception as e:
                            print(f"❌ Не удалось уведомить следующего игрока: {e}")
                else:
                    # При дубле отправляем сообщение игроку
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f"🎲 ДУБЛЬ!\n🎯 Ходите еще раз!\n\nИспользуйте /roll"
                    )

                game_manager.save_game_state(game_id)

                # Уведомляем других игроков о пропуске
                for other_id, other_player in game.players.items():
                    if other_id != user.id:
                        try:
                            other_text = f"⏭️ {player.full_name} пропустил(а) покупку {cell.name}"

                            # Добавляем информацию о следующем игроке только если не дубль
                            if not double:
                                next_player = game.get_current_player()
                                if next_player:
                                    other_text += f"\n⏭️ Следующий ход: {next_player.full_name}"

                            await context.bot.send_message(
                                chat_id=other_id,
                                text=other_text
                            )
                        except Exception as e:
                            print(f"❌ Не удалось уведомить игрока {other_id}: {e}")

        # Обработка кнопки "Передать ход" - ИСПРАВЛЕННАЯ ВЕРСИЯ
        # #elif data.startswith("pass_turn_"):
        #     # Разбираем callback_data: pass_turn_<game_id> или pass_turn_<game_id>_<dice1>_<dice2>
        #     parts = data.split("_")
        #
        #     if len(parts) < 3:  # pass_turn_<game_id> как минимум
        #         await query.answer("❌ Неверный формат callback_data", show_alert=True)
        #         return
        #
        #     game_id = parts[2]  # Третья часть это game_id
        #
        #     # Проверяем, есть ли информация о кубиках
        #     double_info = None
        #     if len(parts) >= 5:  # pass_turn_<game_id>_<dice1>_<dice2>
        #         try:
        #             dice1 = int(parts[3])
        #             dice2 = int(parts[4])
        #             double_info = (dice1 == dice2)
        #         except:
        #             double_info = None
        #
        #     game = game_manager.get_game(game_id)
        #     if not game:
        #         await query.answer("❌ Игра не найдена", show_alert=True)
        #         return
        #
        #     player = game.players.get(user.id)
        #     if not player:
        #         await query.answer("❌ Вы не в этой игре", show_alert=True)
        #         return
        #
        #     # Проверяем, может ли игрок передать ход
        #     current_player = game.get_current_player()
        #     if not current_player:
        #         await query.answer("❌ Нет текущего игрока", show_alert=True)
        #         return
        #
        #     # Проверяем, что кнопку нажимает текущий игрок
        #     if current_player.user_id != user.id:
        #         # Проверяем, не устарела ли кнопка
        #         # Возможно, ход уже перешел, но кнопка осталась
        #         await query.answer(
        #             f"⏳ Сейчас ходит {current_player.full_name}! Ждите своей очереди.",
        #             show_alert=True
        #         )
        #         return
        #
        #     # Сохраняем имя текущего игрока перед передачей хода
        #     old_player_name = current_player.full_name
        #     old_player_color = current_player.color if hasattr(current_player, 'color') else '🎲'
        #
        #     # ВАЖНО: Проверяем, был ли дубль
        #     # Если был дубль - НЕ передаем ход
        #     if double_info is True:
        #         # Был дубль - игрок ходит еще раз
        #         transfer_text = f"🎲 ДУБЛЬ!\n🎯 {old_player_color} {old_player_name} ходит еще раз!"
        #
        #         # Обновляем сообщение
        #         try:
        #             if query.message.caption:
        #                 await query.edit_message_caption(
        #                     caption=transfer_text,
        #                     parse_mode=None,
        #                     reply_markup=None
        #                 )
        #             else:
        #                 await query.edit_message_text(
        #                     text=transfer_text,
        #                     parse_mode=None,
        #                     reply_markup=None
        #                 )
        #         except Exception as e:
        #             print(f"❌ Ошибка при обновлении сообщения: {e}")
        #             await query.answer(transfer_text, show_alert=True)
        #
        #         # Уведомляем игрока, что он ходит еще раз
        #         await context.bot.send_message(
        #             chat_id=user.id,
        #             text=f"🎲 ДУБЛЬ!\n🎯 Ваш ход продолжается!\n\nИспользуйте /roll чтобы бросить кубики снова"
        #         )
        #
        #     else:
        #         # НЕ было дубля - передаем ход
        #         game.next_turn()
        #
        #         # Получаем следующего игрока
        #         next_player = game.get_current_player()
        #
        #         if next_player:
        #             next_player_color = next_player.color if hasattr(next_player, 'color') else '🎲'
        #             transfer_text = f"⏭️ Ход передан\n\n"
        #             transfer_text += f"🎲 Предыдущий: {old_player_color} {old_player_name}\n"
        #             transfer_text += f"🎯 Следующий: {next_player_color} {next_player.full_name}"
        #         else:
        #             transfer_text = f"⏭️ {old_player_name} передал(а) ход"
        #
        #         # Обновляем сообщение
        #         try:
        #             if query.message.caption:
        #                 await query.edit_message_caption(
        #                     caption=transfer_text,
        #                     parse_mode=None,
        #                     reply_markup=None
        #                 )
        #             else:
        #                 await query.edit_message_text(
        #                     text=transfer_text,
        #                     parse_mode=None,
        #                     reply_markup=None
        #                 )
        #         except Exception as e:
        #             print(f"❌ Ошибка при обновлении сообщения: {e}")
        #             await query.answer(transfer_text, show_alert=True)
        #
        #         # Уведомляем следующего игрока
        #         if next_player and next_player.user_id != user.id:
        #             await notify_next_player(game, context, user.id)
        #
        #     # Сохраняем состояние игры
        #     game_manager.save_game_state(game_id)

        # Обработка кнопок тюрьмы
        elif data.startswith("jail_"):
            parts = data.split("_")
            if len(parts) >= 3:
                action = parts[1]  # roll, pay, card, skip
                game_id = parts[2]

                game = game_manager.get_game(game_id)
                if not game:
                    await query.answer("❌ Игра не найдена", show_alert=True)
                    return

                player = game.players.get(user.id)
                if not player:
                    await query.answer("❌ Вы не в этой игре", show_alert=True)
                    return

                # Проверка на текущего игрока
                current_player = game.get_current_player()
                if current_player and current_player.user_id != user.id:
                    await query.answer(f"❌ Сейчас ходит {current_player.full_name}!", show_alert=True)
                    return

                if not player.in_jail:
                    await query.answer("❌ Вы не в тюрьме!", show_alert=True)
                    return

                # Обработка действий в тюрьме
                if action == "roll":
                    dice1, dice2, total = game.roll_dice()

                    if dice1 == dice2:
                        # Успешный дубль
                        player.release_from_jail()
                        response = f"🎲 ДУБЛЬ!\n🎯 {dice1} + {dice2} = {total}\n🔓 Вы вышли из тюрьмы!\n🎲 Теперь ваш ход!"
                    else:
                        # Неудачная попытка
                        player.jail_turns += 1
                        if player.jail_turns >= 3:
                            player.release_from_jail()
                            response = f"🎲 Нет дубля\n🎯 {dice1} + {dice2} = {total}\n⏰ Прошло 3 круга!\n🔓 Вы вышли автоматически!"
                            game.next_turn()
                        else:
                            response = f"🎲 Нет дубля\n🎯 {dice1} + {dice2} = {total}\n🔒 Остаётесь в тюрьме\n📅 Круг: {player.jail_turns}/3"
                            game.next_turn()

                    await query.edit_message_text(response)
                    game_manager.save_game_state(game_id)

                    # Уведомляем следующего игрока, если ход перешел
                    if not (dice1 == dice2) or player.jail_turns >= 3:
                        next_player = game.get_current_player()
                        if next_player and next_player.user_id != user.id:
                            await notify_next_player(game, context, user.id)

                elif action == "pay":
                    if player.money >= Config.JAIL_FINE:
                        player.deduct_money(Config.JAIL_FINE)
                        player.release_from_jail()
                        response = f"💵 Вы заплатили ${Config.JAIL_FINE}\n🔓 Вы вышли из тюрьмы!\n💰 Баланс: ${player.money}"
                    else:
                        player.jail_turns += 1
                        if player.jail_turns >= 3:
                            player.release_from_jail()
                            game.next_turn()
                            response = f"❌ Недостаточно денег!\n⏰ Прошло 3 круга!\n🔓 Вы вышли автоматически!"
                        else:
                            game.next_turn()
                            response = f"❌ Недостаточно денег!\n🔒 Остаётесь в тюрьме\n📅 Круг: {player.jail_turns}/3"

                    await query.edit_message_text(response)
                    game_manager.save_game_state(game_id)

                    # Уведомляем следующего игрока
                    next_player = game.get_current_player()
                    if next_player and next_player.user_id != user.id:
                        await notify_next_player(game, context, user.id)

                elif action == "card":
                    if player.get_out_of_jail_cards > 0:
                        player.get_out_of_jail_cards -= 1
                        player.release_from_jail()
                        response = f"🎫 Карта использована!\n🔓 Вы вышли из тюрьмы!\n📊 Осталось карт: {player.get_out_of_jail_cards}"
                    else:
                        player.jail_turns += 1
                        if player.jail_turns >= 3:
                            player.release_from_jail()
                            game.next_turn()
                            response = f"❌ Нет карт освобождения!\n⏰ Прошло 3 круга!\n🔓 Вы вышли автоматически!"
                        else:
                            game.next_turn()
                            response = f"❌ Нет карт освобождения!\n🔒 Остаётесь в тюрьме\n📅 Круг: {player.jail_turns}/3"

                    await query.edit_message_text(response)
                    game_manager.save_game_state(game_id)

                    # Уведомляем следующего игрока
                    next_player = game.get_current_player()
                    if next_player and next_player.user_id != user.id:
                        await notify_next_player(game, context, user.id)

        # Главное меню (доступно всем)
        elif data == "menu_new_game":
            await newgame_command(query.message, context)

        elif data == "menu_join_game":
            await query.edit_message_text(
                "👥 Присоединиться к игре\n\n"
                "Введите команду:\n"
                "/join КОД_ИГРЫ\n\n"
                "Или посмотрите доступные игры: /games"
            )

        elif data == "menu_rules":
            await help_command(query.message, context)

        elif data == "menu_profile":
            await myid_command(query.message, context)

        # Лобби (доступно участникам лобби)
        elif data.startswith("lobby_start_"):
            game_id = data.replace("lobby_start_", "")
            game = game_manager.get_game(game_id)

            if game and user.id == game.creator_id:
                await startgame_command(query.message, context)
            else:
                await query.answer("❌ Только создатель может начать игру!", show_alert=True)

        elif data.startswith("lobby_invite_"):
            game_id = data.replace("lobby_invite_", "")
            game = game_manager.get_game(game_id)

            if game and user.id in game.players:
                await query.message.reply_text(
                    f"👥 Приглашение в игра\n\n"
                    f"Код игры: {game_id}\n\n"
                    f"Отправьте друзьям эту команду:\n"
                    f"/join {game_id}"
                )
            else:
                await query.answer("❌ Вы не в этой игре!", show_alert=True)

        elif data.startswith("lobby_stats_"):
            game_id = data.replace("lobby_stats_", "")
            game = game_manager.get_game(game_id)

            if game and user.id in game.players:
                players_list = "\n".join([
                    f"• {player.full_name}" +
                    (" 👑" if player.user_id == game.creator_id else "")
                    for player in game.players.values()
                ])

                await query.message.reply_text(
                    f"📊 Статистика лобби\n\n"
                    f"🎮 Игра: {game.game_id}\n"
                    f"👥 Игроков: {len(game.players)}/{Config.MAX_PLAYERS}\n\n"
                    f"Участники:\n{players_list}"
                )
            else:
                await query.answer("❌ Вы не в этой игре!", show_alert=True)

        elif data == "lobby_leave":
            await leave_command(query.message, context)

        # Игровые действия (проверяем, что игрок в игре)
        elif data == "game_roll_dice":
            game = game_manager.get_player_game(user.id)
            if game:
                current_player = game.get_current_player()
                if current_player and current_player.user_id == user.id:
                    await roll_command(query.message, context)
                else:
                    await query.answer("❌ Не ваш ход!", show_alert=True)
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

        elif data == "game_view_board":
            game = game_manager.get_player_game(user.id)
            if game:
                await board_command(query.message, context)
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

        elif data == "game_my_properties":
            game = game_manager.get_player_game(user.id)
            if game:
                await properties_command(query.message, context)
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

        elif data == "game_players":
            game = game_manager.get_player_game(user.id)
            if game:
                await status_command(query.message, context)
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

        elif data == "game_leave":
            game = game_manager.get_player_game(user.id)
            if game:
                await leave_command(query.message, context)
            else:
                await query.answer("❌ Вы не в игре!", show_alert=True)

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
    player_color = player.color if hasattr(player, 'color') else "🎲"
    response = f"{player_color} *СОБСТВЕННОСТЬ {escape_markdown(getattr(player, 'full_name', 'Игрок'))}*\n\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ОСНОВНАЯ ИНФОРМАЦИЯ
    response += f"💰 *Баланс:* ${getattr(player, 'money', 0)}\n"
    response += f"📍 *Позиция:* {getattr(player, 'position', 0)}\n"
    response += f"🎨 *Цвет фишки:* {player_color}\n"
    response += f"🎮 *Статус:* {escape_markdown(getattr(getattr(player, 'status', None), 'value', 'активен'))}\n\n"

    response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # УЛИЦЫ (С ДОПОЛНЕНИЕМ ИНФОРМАЦИИ О ДОМАХ)
    properties = getattr(player, 'properties', [])
    if properties:
        response += f"🏠 *УЛИЦЫ ({len(properties)}):*\n"
        for prop_id in properties:
            cell = game.board.get_cell(prop_id)
            if cell and hasattr(cell, 'name'):
                # Информация о домах/отеле
                houses_info = ""
                if hasattr(cell, 'hotel') and cell.hotel:
                    houses_info = "🏨 ОТЕЛЬ"
                elif hasattr(cell, 'houses') and cell.houses > 0:
                    houses_info = f"🏠×{cell.houses}"

                # Информация о залоге
                mortgaged_info = "💳 ЗАЛОЖЕНА" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""

                # Цветовая группа
                color_info = f"🎨 {cell.color_group}" if hasattr(cell, 'color_group') else ""

                response += f"• *{escape_markdown(cell.name)}* ({prop_id})"
                if houses_info:
                    response += f" {houses_info}"
                if mortgaged_info:
                    response += f" {mortgaged_info}"
                if color_info:
                    response += f" {color_info}"
                response += f"\n"
    else:
        response += "🏠 *УЛИЦЫ:* нет\n"

    response += "\n"

    # ВОКЗАЛЫ
    stations = getattr(player, 'stations', [])
    if stations:
        response += f"🚂 *МЕТРО ({len(stations)}):*\n"
        for station_id in stations:
            cell = game.board.get_cell(station_id)
            if cell and hasattr(cell, 'name'):
                mortgaged_info = "💳 ЗАЛОЖЕН" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""
                response += f"• *{escape_markdown(cell.name)}* {mortgaged_info}\n"
    else:
        response += "🚂 *МЕТРО:* нет\n"

    response += "\n"

    # ПРЕДПРИЯТИЯ
    utilities = getattr(player, 'utilities', [])
    if utilities:
        response += f"⚡️ *ПРЕДПРИЯТИЯ ({len(utilities)}):*\n"
        for util_id in utilities:
            cell = game.board.get_cell(util_id)
            if cell and hasattr(cell, 'name'):
                mortgaged_info = "💳 ЗАЛОЖЕНО" if hasattr(cell, 'mortgaged') and cell.mortgaged else ""
                response += f"• *{escape_markdown(cell.name)}* {mortgaged_info}\n"
    else:
        response += "⚡️ *ПРЕДПРИЯТИЯ:* нет\n"

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
    response += f"• Куплено недвижимости: {len(properties)}\n"
    response += f"• Карт освобождения: {getattr(player, 'get_out_of_jail_cards', 0)}\n"

    # ДОБАВЛЯЕМ РАЗДЕЛ С КОМАНДАМИ ДЛЯ УПРАВЛЕНИЯ ДОМАМИ
    response += "\n🏗 *УПРАВЛЕНИЕ ДОМАМИ:*\n"
    response += "• `/houses` - информация о домах\n"
    response += "• `/build_house` - построить дом\n"
    response += "• `/build_hotel` - построить отель\n"
    response += "• `/sell_house` - продать дом/отель\n"

    # Добавляем кнопки управления (если они есть)
    await update.message.reply_text(
        response,
        parse_mode="Markdown"
    )

    print(f"✅ Информация отправлена пользователю {user.id}")
async def build_house_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для постройки дома"""
    try:
        user = update.effective_user

        # Получаем игру
        game = game_manager.get_player_game(user.id)
        if not game:
            await update.message.reply_text(
                "❌ *Вы не в игре!*",
                parse_mode="Markdown"
            )
            return

        player = game.players.get(user.id)
        if not player:
            await update.message.reply_text("❌ Игрок не найден!")
            return

        # Проверяем аргументы
        if not context.args:
            # Показываем список доступных для строительства улиц
            available_properties = []

            for prop_id in player.properties:
                check_result = game.board.can_build_house(prop_id, player.user_id)
                if check_result.get("can_build"):
                    cell = game.board.get_cell(prop_id)
                    available_properties.append({
                        "id": prop_id,
                        "name": cell.name,
                        "houses": cell.houses,
                        "price": check_result.get("house_price", 0)
                    })

            if not available_properties:
                await update.message.reply_text(
                    "❌ *Нет доступных улиц для строительства!*\n\n"
                    "📋 *Условия для строительства:*\n"
                    "1. Владеть всей цветовой группой\n"
                    "2. Равномерная застройка (нельзя отставать на 2 дома)\n"
                    "3. Не более 4 домов на улице\n"
                    "4. Улица не в залоге\n"
                    "5. Есть деньги для строительства\n\n"
                    "💰 *Стоимость дома:* $50-200 в зависимости от улицы",
                    parse_mode="Markdown"
                )
                return

            # Формируем список доступных улиц
            response = f"🏗 *ДОСТУПНЫЕ ДЛЯ СТРОИТЕЛЬСТВА УЛИЦЫ*\n\n"

            for i, prop in enumerate(available_properties, 1):
                response += f"{i}. *{prop['name']}*\n"
                response += f"   📍 Клетка: {prop['id']}\n"
                response += f"   🏠 Домов: {prop['houses']}/4\n"
                response += f"   💵 Стоимость: ${prop['price']}\n"
                response += f"   👉 Команда: `/build_house {prop['id']}`\n\n"

            response += "🎯 *Как построить:*\n"
            response += "`/build_house НОМЕР_КЛЕТКИ`\n"
            response += "Пример: `/build_house 1`"

            await update.message.reply_text(response, parse_mode="Markdown")
            return

        # Обработка команды с аргументом
        try:
            property_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ *Неверный формат!*\n"
                "Используйте: `/build_house НОМЕР_КЛЕТКИ`\n"
                "Пример: `/build_house 1`",
                parse_mode="Markdown"
            )
            return

        # Проверяем, что игрок владеет этой недвижимостью
        if property_id not in player.properties:
            await update.message.reply_text(
                "❌ *Вы не владеете этой недвижимостью!*",
                parse_mode="Markdown"
            )
            return

        # Проверяем возможность строительства
        check_result = game.board.can_build_house(property_id, player.user_id)

        if not check_result.get("can_build"):
            reason = check_result.get("reason", "Неизвестная причина")
            await update.message.reply_text(
                f"❌ *Нельзя построить дом!*\n\n"
                f"📋 *Причина:* {reason}",
                parse_mode="Markdown"
            )
            return

        # Проверяем деньги
        house_price = check_result.get("house_price", 0)


        if player.money < house_price:
            await update.message.reply_text(
                f"❌ *Недостаточно денег!*\n\n"
                f"💰 *Нужно:* ${house_price}\n"
                f"💵 *У вас:* ${player.money}",
                parse_mode="Markdown"
            )
            return

        # Строим дом
        cell = game.board.get_cell(property_id)

        # Списываем деньги
        player.deduct_money(house_price)

        # Строим дом
        cell.houses += 1

        # Обновляем статистику
        if hasattr(player, 'houses_built'):
            player.houses_built += 1

        # Формируем ответ
        response = f"✅ *ДОМ ПОСТРОЕН!*\n\n"
        response += f"🏠 *Улица:* {cell.name}\n"
        response += f"🎨 *Цвет:* {cell.color_group}\n"
        response += f"🏗 *Домов теперь:* {cell.houses}/4\n"
        response += f"💸 *Потрачено:* ${house_price}\n"
        response += f"💰 *Остаток:* ${player.money}\n\n"

        # Проверяем, можно ли строить отель
        if cell.houses == 4:
            response += f"🎉 *Достигнут максимум домов!*\n"
            response += f"🏨 *Теперь можно построить отель:*\n"
            response += f"💰 Стоимость: ${getattr(cell, 'hotel_price', house_price * 5)}\n"
            response += f"👉 Команда: `/build_hotel {property_id}`\n\n"

        response += f"📈 *Рента теперь:* ${cell.get_rent()}"

        await update.message.reply_text(response, parse_mode="Markdown")

        # Сохраняем состояние игры
        game_manager.save_game_state(game.game_id)

    except Exception as e:
        print(f"❌ Ошибка в build_house_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def build_hotel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для постройки отеля"""
    try:
        user = update.effective_user

        # Получаем игру
        game = game_manager.get_player_game(user.id)
        if not game:
            await update.message.reply_text(
                "❌ *Вы не в игре!*",
                parse_mode="Markdown"
            )
            return

        player = game.players.get(user.id)
        if not player:
            await update.message.reply_text("❌ Игрок не найден!")
            return

        # Проверяем аргументы
        if not context.args:
            # Показываем список доступных для отелей улиц
            available_hotels = []

            for prop_id in player.properties:
                check_result = game.board.can_build_hotel(prop_id, player.user_id)
                if check_result.get("can_build"):
                    cell = game.board.get_cell(prop_id)
                    available_hotels.append({
                        "id": prop_id,
                        "name": cell.name,
                        "hotel_price": check_result.get("hotel_price", 0)
                    })

            if not available_hotels:
                await update.message.reply_text(
                    "❌ *Нет доступных улиц для постройки отеля!*\n\n"
                    "📋 *Условия для отеля:*\n"
                    "1. Иметь 4 дома на улице\n"
                    "2. Владеть всей цветовой группой\n"
                    "3. Улица не в залоге\n"
                    "4. Есть деньги для строительства\n\n"
                    "💰 *Стоимость отеля:* $200-1000 в зависимости от улицы",
                    parse_mode="Markdown"
                )
                return

            # Формируем список
            response = f"🏨 *ДОСТУПНЫЕ ДЛЯ ОТЕЛЯ УЛИЦЫ*\n\n"

            for i, prop in enumerate(available_hotels, 1):
                response += f"{i}. *{prop['name']}*\n"
                response += f"   📍 Клетка: {prop['id']}\n"
                response += f"   💵 Стоимость отеля: ${prop['hotel_price']}\n"
                response += f"   👉 Команда: `/build_hotel {prop['id']}`\n\n"

            await update.message.reply_text(response, parse_mode="Markdown")
            return


        # Обработка команды с аргументом
        try:
            property_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ *Неверный формат!*\n"
                "Используйте: `/build_hotel НОМЕР_КЛЕТКИ`",
                parse_mode="Markdown"
            )
            return

        # Проверяем владение
        if property_id not in player.properties:
            await update.message.reply_text(
                "❌ *Вы не владеете этой недвижимостью!*",
                parse_mode="Markdown"
            )
            return

        # Проверяем возможность строительства отеля
        check_result = game.board.can_build_hotel(property_id, player.user_id)

        if not check_result.get("can_build"):
            reason = check_result.get("reason", "Неизвестная причина")
            await update.message.reply_text(
                f"❌ *Нельзя построить отель!*\n\n"
                f"📋 *Причина:* {reason}",
                parse_mode="Markdown"
            )
            return

        # Проверяем деньги
        hotel_price = check_result.get("hotel_price", 0)

        if player.money < hotel_price:
            await update.message.reply_text(
                f"❌ *Недостаточно денег!*\n\n"
                f"💰 *Нужно:* ${hotel_price}\n"
                f"💵 *У вас:* ${player.money}",
                parse_mode="Markdown"
            )
            return

        # Строим отель
        cell = game.board.get_cell(property_id)

        # Списываем деньги
        player.deduct_money(hotel_price)

        # Строим отель
        cell.hotel = True
        cell.houses = 0

        # Обновляем статистику
        if hasattr(player, 'hotels_built'):
            player.hotels_built += 1

        # Формируем ответ
        response = f"🎉 *ОТЕЛЬ ПОСТРОЕН!*\n\n"
        response += f"🏨 *Улица:* {cell.name}\n"
        response += f"🎨 *Цвет:* {cell.color_group}\n"
        response += f"💸 *Потрачено:* ${hotel_price}\n"
        response += f"💰 *Остаток:* ${player.money}\n"
        response += f"📈 *Рента теперь:* ${cell.get_rent()}\n\n"
        response += f"⚠️ *Внимание:* Отель нельзя разделить обратно на дома!\n"
        response += f"💰 Продать можно только целиком за ${hotel_price // 2}"

        await update.message.reply_text(response, parse_mode="Markdown")

        # Сохраняем состояние игры
        game_manager.save_game_state(game.game_id)

    except Exception as e:
        print(f"❌ Ошибка в build_hotel_command: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def sell_house_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для продажи дома/отеля"""
    try:
        user = update.effective_user

        # Получаем игру
        game = game_manager.get_player_game(user.id)
        if not game:
            await update.message.reply_text(
                "❌ *Вы не в игре!*",
                parse_mode="Markdown"
            )
            return

        player = game.players.get(user.id)
        if not player:
            await update.message.reply_text("❌ Игрок не найден!")
            return

        # Проверяем аргументы
        if not context.args:
            # Показываем список доступных для продажи
            available_sales = []

            for prop_id in player.properties:
                check_result = game.board.can_sell_house(prop_id, player.user_id)
                if check_result.get("can_sell"):
                    cell = game.board.get_cell(prop_id)

                    if check_result.get("is_hotel"):
                        sale_type = "Отель"
                        price = check_result.get("sell_price", 0)
                    else:
                        sale_type = f"Дом ({cell.houses} шт.)"
                        price = check_result.get("sell_price", 0)

                    available_sales.append({
                        "id": prop_id,
                        "name": cell.name,
                        "type": sale_type,
                        "price": price
                    })


            if not available_sales:
                await update.message.reply_text(
                    "❌ *Нет доступных домов/отелей для продажи!*\n\n"
                    "📋 *Условия для продажи:*\n"
                    "1. На улице должны быть дома или отель\n"
                    "2. Равномерность застройки (нельзя быть впереди)\n"
                    "3. Продажа возможна только банку за полцены\n",
                    parse_mode="Markdown"
                )
                return

            # Формируем список
            response = f"💰 *ДОСТУПНЫЕ ДЛЯ ПРОДАЖИ*\n\n"

            for i, sale in enumerate(available_sales, 1):
                response += f"{i}. *{sale['name']}*\n"
                response += f"   📍 Клетка: {sale['id']}\n"
                response += f"   🏠 Что: {sale['type']}\n"
                response += f"   💵 Выручка: ${sale['price']}\n"
                response += f"   👉 Команда: `/sell_house {sale['id']}`\n\n"

            await update.message.reply_text(response, parse_mode="Markdown")
            return

        # Обработка команды с аргументом
        try:
            property_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ *Неверный формат!*\n"
                "Используйте: `/sell_house НОМЕР_КЛЕТКИ`",
                parse_mode="Markdown"
            )
            return

        # Проверяем владение
        if property_id not in player.properties:
            await update.message.reply_text(
                "❌ *Вы не владеете этой недвижимостью!*",
                parse_mode="Markdown"
            )
            return

        # Проверяем возможность продажи
        check_result = game.board.can_sell_house(property_id, player.user_id)

        if not check_result.get("can_sell"):
            reason = check_result.get("reason", "Неизвестная причина")
            await update.message.reply_text(
                f"❌ *Нельзя продать!*\n\n"
                f"📋 *Причина:* {reason}",
                parse_mode="Markdown"
            )
            return

        # Продаем
        cell = game.board.get_cell(property_id)
        sell_price = check_result.get("sell_price", 0)

        # Начисляем деньги
        player.add_money(sell_price)

        if check_result.get("is_hotel"):
            # Продаем отель
            cell.hotel = False
            cell.houses = 4

            response = f"🏨 *ОТЕЛЬ ПРОДАН!*\n\n"
            response += f"💰 *Выручка:* ${sell_price}\n"
            response += f"🏠 *Теперь на {cell.name}:* 4 дома\n"
        else:
            # Продаем дом
            cell.houses -= 1

            response = f"🏠 *ДОМ ПРОДАН!*\n\n"
            response += f"💰 *Выручка:* ${sell_price}\n"
            response += f"🏠 *Теперь на {cell.name}:* {cell.houses} домов\n"

        response += f"💵 *Баланс:* ${player.money}"

        await update.message.reply_text(response, parse_mode="Markdown")

        # Сохраняем состояние игры
        game_manager.save_game_state(game.game_id)

    except Exception as e:
        print(f"❌ Ошибка в sell_house_command: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def houses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра информации о домах"""
    user = update.effective_user

    game = game_manager.get_player_game(user.id)
    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    player = game.players.get(user.id)
    if not player:
        await update.message.reply_text("❌ Игрок не найден!")
        return

    response = f"🏗 *УПРАВЛЕНИЕ ДОМАМИ*\n\n"
    response += f"👤 *Игрок:* {player.full_name}\n"
    response += f"💰 *Баланс:* ${player.money}\n\n"


    # Информация о цветовых группах
    color_groups = {}
    for prop_id in player.properties:
        cell = game.board.get_cell(prop_id)
        if isinstance(cell, PropertyCell):
            if cell.color_group not in color_groups:
                color_groups[cell.color_group] = []
            color_groups[cell.color_group].append(cell)

    response += f"🎨 *ЦВЕТОВЫЕ ГРУППЫ:*\n"

    for color, properties in color_groups.items():
        total_in_group = len([c for c in game.board.cells
                              if isinstance(c, PropertyCell) and c.color_group == color])

        owned = len(properties)
        houses_count = sum(p.houses for p in properties)
        hotels_count = sum(1 for p in properties if p.hotel)

        status = "✅ Полная" if owned == total_in_group else f"❌ {owned}/{total_in_group}"

        response += f"\n*{color.upper()}*: {status}\n"

        for prop in properties:
            house_info = ""
            if prop.hotel:
                house_info = "🏨 ОТЕЛЬ"
            elif prop.houses > 0:
                house_info = f"🏠×{prop.houses}"
            else:
                house_info = "🏘 Нет домов"

            mortgaged_info = "💳 Заложена" if prop.mortgaged else ""

            response += f"  • {prop.name} ({prop.id}) - {house_info} {mortgaged_info}\n"

    response += f"\n📋 *КОМАНДЫ:*\n"
    response += f"• `/build_house` - показать доступные для строительства\n"
    response += f"• `/build_hotel` - показать доступные для отелей\n"
    response += f"• `/sell_house` - продать дом/отель\n"
    response += f"• `/properties` - полная информация о недвижимости\n"

    await update.message.reply_text(response, parse_mode="Markdown")



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

    # Проверяем, в тюрьме ли игрок
    if not player.in_jail:
        await update.message.reply_text(
            f"❌ *Вы не в тюрьме!*\n\n"
            f"📍 Ваша позиция: {player.position}\n"
            f"🎮 Статус: {player.status.value}",
            parse_mode="Markdown"
        )
        return

    # Проверяем, не истекли ли 3 хода в тюрьме
    if player.jail_turns >= 3:
        # Автоматический выход с оплатой штрафа после 3 ходов
        if player.money >= Config.JAIL_FINE:
            player.deduct_money(Config.JAIL_FINE)
            player.in_jail = False
            player.jail_turns = 0
            player.status = PlayerStatus.ACTIVE

            await update.message.reply_text(
                f"⏰ *Прошло 3 хода в тюрьме!*\n"
                f"💸 Автоматически списан штраф: ${Config.JAIL_FINE}\n"
                f"🔓 Вы вышли из тюрьмы!\n"
                f"💰 Ваш баланс: ${player.money}",
                parse_mode="Markdown"
            )

            # Сохраняем изменения
            game_manager.save_game_state(game.game_id)
            return
        else:
            # Игрок банкрот
            player.status = PlayerStatus.BANKRUPT
            await update.message.reply_text(
                f"💥 *БАНКРОТСТВО!*\n"
                f"❌ Не хватает денег на штраф ${Config.JAIL_FINE}\n"
                f"💸 Ваш баланс: ${player.money}\n"
                f"🏁 Вы выбываете из игры!",
                parse_mode="Markdown"
            )

            # Сохраняем изменения
            game_manager.save_game_state(game.game_id)
            return

    # Получаем цвет игрока
    player_color = player.color if hasattr(player, 'color') else "🔒"

    # Создаем клавиатуру для действий в тюрьме
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Попытать удачу (бросить кубики)", callback_data=f"jail_roll_{game.game_id}")],
        [InlineKeyboardButton(f"💵 Заплатить ${Config.JAIL_FINE}", callback_data=f"jail_pay_{game.game_id}")],
        [InlineKeyboardButton("🎫 Использовать карту освобождения", callback_data=f"jail_card_{game.game_id}")],
        [InlineKeyboardButton("⏳ Остаться еще ход", callback_data=f"jail_skip_{game.game_id}")],
    ])

    await update.message.reply_text(
        f"{player_color} *ВЫ В ТЮРЬМЕ!*\n\n"
        f"Ход в тюрьме: {player.jail_turns + 1}/3\n\n"
        f"👤 *Игрок:* {player.full_name}\n"
        f"📍 *Позиция:* 10 (ТЮРЬМА)\n"
        f"💰 *Баланс:* {format_money(player.money)}\n"
        f"🎫 *Карт освобождения:* {player.get_out_of_jail_cards}\n\n"
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
        f"🎮 *Выберите действие:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def send_game_board(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          game, caption: str = "🎮 Текущее состояние игры"):
    """Отправляет изображение игрового поля"""
    try:
        # Подготавливаем данные для рендерера
        players_data = []
        for player_id, player in game.players.items():
            players_data.append({
                "id": player_id,
                "name": player.full_name,
                "position": player.position,
                "color": getattr(player, 'color', '🔴'),
                "money": player.money
            })

        # Собираем информацию о собственности
        properties_data = {}
        for cell in game.board.cells:
            if hasattr(cell, 'owner_id') and cell.owner_id:
                properties_data[cell.id] = {
                    "owner": cell.owner_id,
                    "houses": getattr(cell, 'houses', 0),
                    "hotel": getattr(cell, 'hotel', False)
                }

        # Генерируем изображение
        game_data = {
            "players": players_data,
            "properties": properties_data
        }

        board_image = board_renderer.render_board(game_data)

        # Конвертируем в bytes
        img_bytes = board_renderer.save_to_bytes(board_image)

        # Отправляем в Telegram
        if update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=img_bytes,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_photo(
                photo=img_bytes,
                caption=caption,
                parse_mode="Markdown"
            )

        return True

    except Exception as e:
        print(f"❌ Ошибка при отправке поля: {e}")
        import traceback
        traceback.print_exc()
        return False


# Команда для просмотра поля
async def board_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать игровое поле"""
    user = update.effective_user
    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    # Формируем подпись
    caption = f"🎮 *Игровое поле*\n"
    caption += f"🎲 Ход: {game.turn_count}\n"
    caption += f"👥 Игроков: {len(game.players)}\n\n"

    current = game.get_current_player()
    if current:
        caption += f"🎯 *Сейчас ходит:* {current.full_name}\n\n"

    # Отправляем поле
    success = await send_game_board(update, context, game, caption)

    if not success:
        await update.message.reply_text(
            f"❌ Не удалось загрузить изображение поля\n\n{caption}",
            parse_mode="Markdown"
        )

async def jail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню тюрьмы - показывает опции"""
    user = update.effective_user
    game = game_manager.get_player_game(user.id)

    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    player = game.players.get(user.id)
    if not player or not player.in_jail:
        await update.message.reply_text("❌ Вы не в тюрьме!", parse_mode="Markdown")
        return

    current_player = game.get_current_player()
    if not current_player or current_player.user_id != user.id:
        await update.message.reply_text(
            f"⏳ *Ждите своего хода!*\n"
            f"Сейчас ходит: {escape_markdown(current_player.full_name)}",
            parse_mode="Markdown"
        )
        return

    # Создаем клавиатуру
    keyboard = []

    # Проверяем доступные опции
    if player.get_out_of_jail_cards > 0:
        keyboard.append(
            [InlineKeyboardButton("🎫 Использовать карту освобождения", callback_data=f"jail_card_{game.game_id}")])

    keyboard.append(
        [InlineKeyboardButton(f"💵 Заплатить ${Config.JAIL_FINE}", callback_data=f"jail_pay_{game.game_id}")])
    keyboard.append([InlineKeyboardButton("🎲 Попытаться выбросить дубль", callback_data=f"jail_roll_{game.game_id}")])

    await update.message.reply_text(
        f"🔒 *ТЮРЬМА - Круг {player.jail_turns + 1}/3*\n\n"
        f"👤 *Игрок:* {player.full_name}\n"
        f"💰 *Баланс:* ${player.money}\n"
        f"🎫 *Карт освобождения:* {player.get_out_of_jail_cards}\n\n"
        f"*Выберите действие:*\n"
        f"• `/jail_pay` - заплатить ${Config.JAIL_FINE}\n"
        f"• `/jail_roll` - попытать удачу\n"
        f"• `/jail_card` - использовать карту",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def jail_pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game = game_manager.get_player_game(user.id)
    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    player = game.players.get(user.id)  # ← отдельное присваивание
    if not player or not player.in_jail:
        await update.message.reply_text("❌ Вы не в тюрьме!", parse_mode="Markdown")
        return

    current_player = game.get_current_player()
    if not current_player or current_player.user_id != user.id:
        await update.message.reply_text("⏳ *Не ваш ход!*", parse_mode="Markdown")
        return

    if game.get_current_player().user_id != user.id:
        await update.message.reply_text("⏳ Ждите своего хода!", parse_mode="Markdown")
        return

    if player.money >= Config.JAIL_FINE:
        player.deduct_money(Config.JAIL_FINE)
        player.release_from_jail()
        await update.message.reply_text(
            f"💵 *Вы заплатили за выход!*\n"
            f"💸 Списан: ${Config.JAIL_FINE}\n"
            f"🔓 Вы вышли из тюрьмы!\n"
            f"💰 Баланс: ${player.money}\n"
            f"🎲 Теперь ваш ход! Используйте /roll.",
            parse_mode="Markdown"
        )
        # ← НЕ передаем ход! Игрок вышел и может ходить сразу
    else:
        # ← ДОБАВИТЬ ЗДЕСЬ: увеличиваем круг и передаем ход
        player.jail_turns += 1


        if player.jail_turns >= 3:
            # Автоматический выход через 3 круга
            player.release_from_jail()
            await update.message.reply_text(
                f"❌ Недостаточно денег!\n"
                f"⏰ Прошло 3 круга!\n"
                f"🔓 Вы автоматически вышли из тюрьмы!\n"
                f"🎲 Теперь ваш ход! Используйте /roll.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Недостаточно денег!\n"
                f"💸 Нужно: ${Config.JAIL_FINE}\n"
                f"💰 У вас: ${player.money}\n"
                f"🔒 Остаётесь в тюрьме.\n"
                f"📅 Круг: {player.jail_turns}/3\n"
                f"⏭️ Ход переходит следующему игроку.",
                parse_mode="Markdown"
            )
            # ← ПЕРЕДАЧА ХОДА ЗДЕСЬ:
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                try:
                    await context.bot.send_message(
                        chat_id=next_player.user_id,
                        text=f"🎲 *Ваш ход!*\n\nИспользуйте `/roll`"
                    )
                except:
                    pass

    game_manager.save_game_state(game.game_id)


async def jail_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game = game_manager.get_player_game(user.id)
    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    player = game.players.get(user.id)  # ← отдельное присваивание
    if not player or not player.in_jail:
        await update.message.reply_text("❌ Вы не в тюрьме!", parse_mode="Markdown")
        return

    current_player = game.get_current_player()
    if not current_player or current_player.user_id != user.id:
        await update.message.reply_text("⏳ *Не ваш ход!*", parse_mode="Markdown")
        return

    if game.get_current_player().user_id != user.id:
        await update.message.reply_text("⏳ Ждите своего хода!", parse_mode="Markdown")
        return

    if player.get_out_of_jail_cards > 0:
        player.get_out_of_jail_cards -= 1
        player.release_from_jail()
        await update.message.reply_text(
            f"🎫 *Карта использована!*\n"
            f"🔓 Вы вышли из тюрьмы!\n"
            f"📊 Осталось карт: {player.get_out_of_jail_cards}\n"
            f"🎲 Теперь ваш ход! Используйте /roll.",
            parse_mode="Markdown"
        )
        # ← НЕ передаем ход! Игрок вышел и может ходить сразу
    else:
        # ← ДОБАВИТЬ ЗДЕСЬ: увеличиваем круг и передаем ход
        player.jail_turns += 1

        if player.jail_turns >= 3:
            # Автоматический выход через 3 круга
            player.release_from_jail()
            await update.message.reply_text(
                f"❌ Нет карт освобождения!\n"
                f"⏰ Прошло 3 круга!\n"
                f"🔓 Вы автоматически вышли из тюрьмы!\n"
                f"🎲 Теперь ваш ход! Используйте /roll.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Нет карт освобождения!\n"
                f"🔒 Остаётесь в тюрьме.\n"
                f"📅 Круг: {player.jail_turns}/3\n"
                f"⏭️ Ход переходит следующему игроку.",
                parse_mode="Markdown"
            )
            # ← ПЕРЕДАЧА ХОДА ЗДЕСЬ:
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                try:
                    await context.bot.send_message(
                        chat_id=next_player.user_id,
                        text=f"🎲 *Ваш ход!*\n\nИспользуйте `/roll`"
                    )
                except:
                    pass


    game_manager.save_game_state(game.game_id)
async def jail_roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game = game_manager.get_player_game(user.id)
    if not game:
        await update.message.reply_text("❌ *Вы не в игре!*", parse_mode="Markdown")
        return

    player = game.players.get(user.id)  # ← отдельное присваивание
    if not player or not player.in_jail:
        await update.message.reply_text("❌ Вы не в тюрьме!", parse_mode="Markdown")
        return

    current_player = game.get_current_player()
    if not current_player or current_player.user_id != user.id:
        await update.message.reply_text("⏳ *Не ваш ход!*", parse_mode="Markdown")
        return

    if game.get_current_player().user_id != user.id:
        await update.message.reply_text("⏳ Ждите своего хода!", parse_mode="Markdown")
        return

    dice1, dice2, total = game.roll_dice()

    if dice1 == dice2:
        # Успешный дубль — выход
        player.release_from_jail()
        await update.message.reply_text(
            f"🎲 *ДУБЛЬ!*\n"
            f"🎯 {dice1} + {dice2} = {total}\n"
            f"🔓 Вы вышли из тюрьме бесплатно!\n"
            f"🎲 Теперь ваш ход! Используйте /roll для продолжения.",
            parse_mode="Markdown"
        )
        # ← НЕ передаем ход! Игрок вышел и может ходить сразу
    else:
        # Неудачная попытка
        player.jail_turns += 1  # Увеличиваем круг

        if player.jail_turns >= 3:
            # 3-й ход — автоматический выход
            player.release_from_jail()
            await update.message.reply_text(
                f"🎲 *Нет дубля*\n"
                f"🎯 {dice1} + {dice2} = {total}\n"
                f"⏰ Прошло 3 круга!\n"
                f"🔓 Вы автоматически вышли из тюрьмы!\n"
                f"🎲 Теперь ваш ход! Используйте /roll.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"🎲 *Нет дубля*\n"
                f"🎯 {dice1} + {dice2} = {total}\n"
                f"🔒 Остаётесь в тюрьме.\n"
                f"📅 Круг: {player.jail_turns}/3\n"
                f"⏭️ Ход переходит следующему игроку.",
                parse_mode="Markdown"
            )
            # ← ПЕРЕДАЧА ХОДА ЗДЕСЬ:
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                try:
                    await context.bot.send_message(
                        chat_id=next_player.user_id,
                        text=f"🎲 *Ваш ход!*\n\n"
                             f"👤 {next_player.full_name}\n"
                             f"💰 Баланс: ${next_player.money}\n\n"
                             f"Используйте `/roll` чтобы бросить кубики",
                        parse_mode="Markdown"
                    )
                except:
                    pass

    game_manager.save_game_state(game.game_id)

async def test_jail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /roll с полной обработкой клеток"""
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

        if game.state.value != "in_game":
            print(f"❌ ERROR: Game not in progress. State: {game.state}, Value: {game.state.value}")
            await update.message.reply_text("❌ *Игра еще не началась!*", parse_mode="Markdown")
            return

        print("✅ Game is in progress")

        current_player = game.get_current_player()
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
        if current_player.in_jail:
            print("🔒 Player is in jail, showing jail menu")

            # Показываем меню тюрьмы НЕ передавая ход сразу
            await jail_command(update, context)

            # НЕ передаем ход сразу! Ждем выбора игрока
            # Игрок должен сам выбрать действие через команды:
            # /jail_pay, /jail_card, /jail_roll

            # Сохраняем игру
            game_manager.save_game_state(game.game_id)
            print("⏸️ Player in jail - waiting for jail action")
            return
            # Бросок кубиков
        # ТЕСТ: перемещение на клетку 30
        old_position = current_player.position
        target_position = 30

        # Рассчитываем сколько нужно пройти
        if old_position <= target_position:
            needed_total = target_position - old_position
        else:
            needed_total = (40 - old_position) + target_position  # Через старт

        # Создаем подходящие значения кубиков
        dice1 = needed_total // 2
        dice2 = needed_total - dice1
        # Минимум 1 на кубике
        if dice1 < 1: dice1 = 1
        if dice2 < 1: dice2 = 1
        total = dice1 + dice2

        print(f"🎲 TEST Dice: {dice1} + {dice2} = {total} (цель: позиция 30)")

        # Перемещаем на 30
        current_player.position = target_position

        # Создаем move_result вручную
        passed_start = old_position > target_position
        move_result = {
            "old_position": old_position,
            "new_position": target_position,
            "spaces_moved": needed_total,
            "passed_start": passed_start,
            "double": (dice1 == dice2)
        }

        print(f"📍 TEST Move: {old_position} → {target_position}")

        # Если прошли через старт
        if passed_start:
            current_player.add_money(Config.SALARY)
            print(f"💰 Passed START: +${Config.SALARY}")

        # Получаем клетку и обрабатываем действие
        cell = game.board.get_cell(current_player.position)
        cell_action = game.process_cell_action(current_player, total)
        if cell_action.get("action") == "go_to_jail":
            # Отправляем в тюрьму
            current_player.position = 10
            current_player.in_jail = True
            current_player.jail_turns = 0

            # ← СОЗДАЕМ НОВУЮ ПЕРЕМЕННУЮ jail_response:
            jail_response = f"{current_player.color if hasattr(current_player, 'color') else '🎲'} "
            jail_response += f"*{escape_markdown(current_player.full_name)} бросает кубики:*\n"
            jail_response += f"🎯 {dice1} + {dice2} = *{total}*\n\n"

            if move_result.get("passed_start"):
                jail_response += f"💰 *Прошли СТАРТ!* +${Config.SALARY}\n\n"

            jail_response += f"📍 *Перемещение:* {old_position} → {current_player.position}\n"
            jail_response += f"💰 *Баланс:* ${current_player.money}\n\n"
            jail_response += f"🏠 *Клетка {current_player.position}: {cell.name}*\n"
            jail_response += f"\n🔒 *ВЫ ОТПРАВЛЕНЫ В ТЮРЬМУ!*\n"
            jail_response += f"📍 Позиция: Тюрьма (клетка 10)\n"
            jail_response += f"📅 Круг: 1/3\n\n"
            jail_response += f"🎮 В следующий ваш ход используйте:\n"
            jail_response += f"• `/jail` - меню тюрьмы\n"
            jail_response += f"• `/jail_pay` - заплатить ${Config.JAIL_FINE}\n"
            jail_response += f"• `/jail_roll` - попытать удачу\n"
            jail_response += f"• `/jail_card` - использовать карту\n\n"

            # Передаем ход
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                jail_response += f"⏭️ *Следующий ход:* {next_player.color} {escape_markdown(next_player.full_name)}"

            await update.message.reply_text(jail_response, parse_mode="Markdown")  # ← используем jail_response
            game_manager.save_game_state(game.game_id)
            return

        # Формируем начальный ответ
        # ТЕСТОВЫЙ ответ
        response = f"🔧 *ТЕСТ: Активация клетки 30*\n\n"
        response += f"{current_player.color if hasattr(current_player, 'color') else '🎲'} "
        response += f"*{escape_markdown(current_player.full_name)} бросает кубики:*\n"
        response += f"🎯 {dice1} + {dice2} = *{total}* (ТЕСТ - цель: клетка 30)\n\n"

        if move_result.get("passed_start"):
            response += f"💰 *Прошли СТАРТ!* +${Config.SALARY}\n\n"

        response += f"📍 *Перемещение:* {old_position} → {current_player.position}\n"
        response += f"💰 *Баланс:* ${current_player.money}\n\n"

        # Отображаем информацию о клетке
        response += f"🏠 *Клетка {current_player.position}: {cell.name}*\n"

        # Проверяем, нужно ли обрабатывать ренту/налоги/карточки
        should_apply_action = True

        if cell_action["action"] == "buy_property":
            should_apply_action = False
            price = cell.price if hasattr(cell, 'price') else 0

            # ДОБАВЛЯЕМ ПРОВЕРКУ НА ДЕНЬГИ, НО СОХРАНЯЕМ buy_offer В ЛЮБОМ СЛУЧАЕ
            if current_player.money >= price:
                has_enough_money = True
                buy_option = "• `/buy` - купить сейчас\n"
            else:
                has_enough_money = False
                buy_option = "• ❌ `/buy` - недостаточно средств\n"

            # ВСЕГДА сохраняем предложение покупки (даже если нет денег, чтобы можно было скипнуть)
            context.user_data['buy_offer'] = {
                'game_id': game.game_id,
                'position': current_player.position,
                'price': price,
                'cell_name': cell.name,
                'player_id': user.id,
                'dice1': dice1,
                'dice2': dice2,
                'double': (dice1 == dice2),
                'cell_type': cell.type.value,
                'timestamp': datetime.now().timestamp(),
                'has_enough_money': has_enough_money  # Добавляем флаг
            }

            response += f"\n🏠 *СОБСТВЕННОСТЬ СВОБОДНА!*\n"
            response += f"🏷 *{cell.name}*\n"

            if cell.type == CellType.PROPERTY:
                response += f"🎨 Тип: Улица"
                if hasattr(cell, 'color_group'):
                    response += f" (Цвет: {cell.color_group})\n"
            elif cell.type == CellType.STATION:
                response += f"🚂 Тип: Вокзал\n"
            elif cell.type == CellType.UTILITY:
                response += f"⚡ Тип: Предприятие\n"

            response += f"💵 Цена покупки: *${price}*\n"
            response += f"💰 У вас: *${current_player.money}*\n\n"

            if current_player.money >= price:
                response += f"✅ Достаточно средств для покупки!\n\n"
            else:
                response += f"❌ Недостаточно средств!\n\n"

            response += f"📋 *Что делать:*\n"
            response += buy_option
            response += f"• `/skip` - пропустить покупку\n\n"

            # ОБЯЗАТЕЛЬНО добавляем информацию о дубле если он есть
            if dice1 == dice2:
                response += "🎲 *ДУБЛЬ! Если купите/пропустите - ходите еще раз!*\n\n"

        # Применяем другие действия клеток
        elif should_apply_action:
            action_result = game.apply_cell_action(current_player, cell_action, total)
            if action_result.get("message"):
                response += f"\n📋 *Действие:* {action_result['message']}\n"

            # Если действие не покупка, обрабатываем дубль и переход хода
            if dice1 == dice2:
                response += "\n\n🎲 *Дубль! Ходите еще раз!*"
                print("🎲 Double! Player gets another turn")
            else:
                # Передаем ход
                game.next_turn()
                next_player = game.get_current_player()

                if next_player:
                    # Добавляем цвет следующему игроку
                    next_player_color = next_player.color if hasattr(next_player, 'color') else '🎲'
                    response += f"\n\n⏭️ *Следующий ход:* {next_player_color} {escape_markdown(next_player.full_name)}"
                    print(f"⏭️ Next player: {next_player.full_name}")


        print(f"📤 Sending response to user...")

        # Отправляем сообщение
        await update.message.reply_text(
            response,
            parse_mode="Markdown"
        )

        print("✅ Response sent successfully")

        # Сохраняем игру (даже если есть предложение покупки)
        game_manager.save_game_state(game.game_id)
        print("💾 Game saved")

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

    # Добавьте обработчик ошибок перед регистрацией команд
    app.add_error_handler(error_handler)

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
        ("properties", properties_command),
        ("jail", jail_command),
        ("jail_roll", jail_roll_command),  # ← НОВАЯ КОМАНДА
        ("jail_pay", jail_pay_command),  # ← НОВАЯ КОМАНДА
        ("jail_card", jail_card_command),  # ← НОВАЯ КОМАНДА
        ("buy", buy_command),
        ("skip", skip_command),
        #("build_house", build_house_command),
        ("test_jail", test_jail_command),  # ← НОВАЯ КОМАНДА (опционально)
        #("build_house", build_house_command),
        ("board", board_command),
        ("build_house", build_house_command),
        ("build_hotel", build_hotel_command),
        ("sell_house", sell_house_command),
        ("houses", houses_command),
    ]


    # 1. ВСЕ КОМАНДЫ ПЕРВЫМИ
    print("\n📋 Регистрируем команды:")
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))
        print(f"✅ /{cmd}")

    # 2. ОБРАБОТЧИК КНОПОК ВТОРЫМ
    print("\n🔘 Регистрируем обработчик кнопок...")
    app.add_handler(CallbackQueryHandler(button_handler))
    print(f"✅ CallbackQueryHandler зарегистрирован")


    print("\n✅ Бот запущен и готов к работе!")
    print("📱 Перейдите в Telegram и начните диалог с ботом")
    print("=" * 60)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    main()