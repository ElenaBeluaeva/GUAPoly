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


async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        print(f"🔍 Game state type: {type(game.state)}")
        print(f"🔍 Game state value: {game.state}")
        print(f"🔍 GameState.IN_PROGRESS: {GameState.IN_PROGRESS}")
        print(f"🔍 Are they equal? {game.state == GameState.IN_PROGRESS}")

        # Вместо if game.state != GameState.IN_PROGRESS:
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

        # Бросок кубиков
        dice1, dice2, total = game.roll_dice()
        print(f"🎲 Dice roll: {dice1} + {dice2} = {total}")

        # Перемещаем игрока
        old_position = current_player.position
        move_result = game.move_player(current_player, total)
        print(f"📍 Move result: {move_result}")

        # Получаем клетку и обрабатываем действие
        cell = game.board.get_cell(current_player.position)
        cell_action = game.process_cell_action(current_player, total)

        # Формируем начальный ответ
        response = f"{current_player.color if hasattr(current_player, 'color') else '🎲'} "
        response += f"*{escape_markdown(current_player.full_name)} бросает кубики:*\n"
        response += f"🎯 {dice1} + {dice2} = *{total}*\n\n"

        if move_result.get("passed_start"):
            response += f"💰 *Прошли СТАРТ!* +${Config.SALARY}\n\n"

        response += f"📍 *Перемещение:* {old_position} → {current_player.position}\n"
        response += f"💰 *Баланс:* ${current_player.money}\n\n"

        # Отображаем информацию о клетке
        response += f"🏠 *Клетка {current_player.position}: {cell.name}*\n"

        # Проверяем, нужно ли обрабатывать ренту/налоги/карточки
        should_apply_action = True

        # Если клетка - собственность и свободна, предлагаем купить
        if cell_action["action"] == "buy_property":
            should_apply_action = False
            price = cell.price if hasattr(cell, 'price') else 0

            # Сохраняем предложение покупки
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
                'timestamp': datetime.now().timestamp()
            }
            context.user_data['buy_timer'] = True

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
            response += f"📋 *Что делать:*\n"
            response += f"• `/buy` - купить сейчас\n"
            response += f"• `/skip` - пропустить покупку\n\n"
            response += f"⏰ У вас 30 секунд на выбор!"
        # В roll_command, при попадании на клетку "Отправляйтесь в тюрьму":
        elif cell_action["action"] == "go_to_jail":
            current_player.go_to_jail()
            response += f"\n🔒 *Отправлены в тюрьму!*\n"
            response += f"📍 Позиция: 10 (ТЮРЬМА)\n"
            response += f"💡 Используйте /jail для выхода"
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
                    response += f"\n\n⏭️ *Следующий ход:* {escape_markdown(next_player.full_name)}"
                    print(f"⏭️ Next player: {next_player.full_name}")

        # Если это предложение покупки и дубль, добавляем информацию о дубле
        if cell_action["action"] == "buy_property" and dice1 == dice2:
            response += "\n\n🎲 *ДУБЛЬ! Если купите/пропустите - ходите еще раз!*"

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

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для покупки собственности после броска"""
    try:
        user = update.effective_user
        print(f"\n=== BUY COMMAND STARTED ===")

        # Проверяем активное предложение покупки
        buy_offer = context.user_data.get('buy_offer')

        if not buy_offer:
            await update.message.reply_text(
                "❌ *Нет активного предложения покупки!*\n\n"
                "Чтобы купить собственность:\n"
                "1. Бросьте кубики: `/roll`\n"
                "2. Попадите на свободный участок\n"
                "3. Используйте `/buy` в течение 30 секунд",
                parse_mode="Markdown"
            )
            return

        # Проверяем, что предложение для этого игрока
        if buy_offer.get('player_id') != user.id:
            await update.message.reply_text(
                "❌ *Это предложение покупки не для вас!*",
                parse_mode="Markdown"
            )
            return

        # Проверяем срок действия предложения (30 секунд)
        timestamp = buy_offer.get('timestamp', 0)
        current_time = datetime.now().timestamp()
        if current_time - timestamp > 30:
            await update.message.reply_text(
                "❌ *Время на покупку истекло!*",
                parse_mode="Markdown"
            )
            # Очищаем предложение
            context.user_data.pop('buy_offer', None)
            context.user_data.pop('buy_timer', None)
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

        if success:
            # Очищаем предложение покупки
            context.user_data.pop('buy_offer', None)
            context.user_data.pop('buy_timer', None)

            cell = game.board.get_cell(buy_offer['position'])
            cell_name = cell.name if cell else buy_offer['cell_name']

            response = f"✅ *ПОКУПКА ОФОРМЛЕНА!*\n\n"
            response += f"🏠 Вы купили *{cell_name}*\n"
            response += f"💰 Потрачено: *${buy_offer['price']}*\n"
            response += f"🏦 Остаток: *${player.money}*\n\n"
            response += f"🎲 Теперь у вас:\n"
            response += f"• Улиц: {len(player.properties)}\n"
            response += f"• Вокзалов: {len(player.stations)}\n"
            response += f"• Предприятий: {len(player.utilities)}"

            # Проверяем дубль
            if buy_offer.get('double'):
                response += f"\n\n🎲 *ДУБЛЬ!*\n🎯 Ходите еще раз!\n\nИспользуйте `/roll`"
                # Не передаем ход при дубле
            else:
                # Переход хода
                game.next_turn()
                next_player = game.get_current_player()
                response += f"\n\n⏭️ *Ход переходит*\n🎯 {next_player.full_name}"

                # Уведомляем следующего игрока
                try:
                    await context.bot.send_message(
                        chat_id=next_player.user_id,
                        text=f"🎯 *Ваш ход!*\n\nИспользуйте `/roll`"
                    )
                except:
                    pass

            await update.message.reply_text(response, parse_mode="Markdown")

            # Уведомляем других игроков
            for other_id, other_player in game.players.items():
                if other_id != user.id:
                    try:
                        await context.bot.send_message(
                            chat_id=other_id,
                            text=f"🏠 *{player.full_name} купил(а) {cell_name}!*",
                            parse_mode="Markdown"
                        )
                    except:
                        pass

            # Сохраняем игру
            game_manager.save_game_state(game.game_id)

            print(f"=== BUY COMMAND FINISHED SUCCESS ===")

        else:
            # Покупка не удалась
            await update.message.reply_text(
                f"❌ *Не удалось купить!*\n\n"
                f"Возможные причины:\n"
                f"1. Недостаточно денег\n"
                f"2. Собственность уже куплена\n"
                f"3. Ошибка системы\n\n"
                f"💰 Нужно: ${buy_offer['price']}\n"
                f"💳 У вас: ${player.money}",
                parse_mode="Markdown"
            )

            # Очищаем предложение
            context.user_data.pop('buy_offer', None)
            context.user_data.pop('buy_timer', None)

    except Exception as e:
        print(f"❌ ERROR in buy_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Ошибка при покупке: {str(e)}")


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для пропуска покупки"""
    try:
        user = update.effective_user
        print(f"\n=== SKIP COMMAND STARTED ===")
        print(f"User ID: {user.id}, Name: {user.full_name}")

        # Проверяем активное предложение покупки
        buy_offer = context.user_data.get('buy_offer')

        if not buy_offer:
            await update.message.reply_text(
                "❌ *Нет активного предложения покупки!*\n\n"
                "Используйте `/skip` только когда вам предложили купить собственность.",
                parse_mode="Markdown"
            )
            return

        # Проверяем, что предложение для этого игрока
        if buy_offer.get('player_id') != user.id:
            await update.message.reply_text(
                "❌ *Это предложение покупки не для вас!*",
                parse_mode="Markdown"
            )
            return

        # Проверяем срок действия предложения (30 секунд)
        timestamp = buy_offer.get('timestamp', 0)
        current_time = datetime.now().timestamp()
        if current_time - timestamp > 30:
            await update.message.reply_text(
                "❌ *Время на покупку истекло!*",
                parse_mode="Markdown"
            )
            # Очищаем предложение
            context.user_data.pop('buy_offer', None)
            context.user_data.pop('buy_timer', None)
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

        # Очищаем предложение покупки
        context.user_data.pop('buy_offer', None)
        context.user_data.pop('buy_timer', None)

        # Уведомление о пропуске
        response = f"⏭️ *ПОКУПКА ПРОПУЩЕНА*\n\n"
        response += f"🏠 Вы отказались от *{buy_offer['cell_name']}*\n"
        response += f"💰 Цена: ${buy_offer['price']}\n"
        response += f"🏦 Ваш баланс: *${player.money}*"

        # Проверяем дубль
        if buy_offer.get('double'):
            response += f"\n\n🎲 *ДУБЛЬ!*\n"
            response += f"🎯 Ходите еще раз!\n\n"
            response += f"Используйте `/roll`"
            # Не передаем ход при дубле
        else:
            # Переход хода
            game.next_turn()
            next_player = game.get_current_player()
            response += f"\n\n⏭️ *Ход переходит*\n"
            response += f"🎯 {next_player.full_name}"

            # Уведомляем следующего игрока
            try:
                await context.bot.send_message(
                    chat_id=next_player.user_id,
                    text=f"🎯 *Ваш ход!*\n\nИспользуйте `/roll`"
                )
            except:
                pass

        await update.message.reply_text(response, parse_mode="Markdown")

        # Сохраняем игру
        game_manager.save_game_state(game.game_id)

        print(f"=== SKIP COMMAND FINISHED SUCCESS ===")

    except Exception as e:
        print(f"❌ ERROR in skip_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Ошибка при пропуске: {str(e)}")

# ДОБАВЬТЕ ТАЙМЕР ДЛЯ ОЧИСТКИ ПРЕДЛОЖЕНИЙ
async def clear_buy_offer(context: ContextTypes.DEFAULT_TYPE):
    """Очистка просроченных предложений покупки"""
    for user_id in list(context.user_data.keys()):
        if 'buy_offer' in context.user_data.get(user_id, {}):
            # Проверяем время (можно добавить timestamp в buy_offer)
            # Если прошло больше 30 секунд - очищаем
            context.user_data[user_id].pop('buy_offer', None)
            context.user_data[user_id].pop('buy_timer', None)
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
        # В функции button_handler добавьте обработку тюрьмы:
        elif data.startswith("jail_roll_"):
            game_id = data.replace("jail_roll_", "")
            game = game_manager.get_game(game_id)
            if game and game.players.get(user.id):
                player = game.players[user.id]

                # Бросаем кубики
                dice1, dice2, total = game.roll_dice()

                if dice1 == dice2:
                    # Дубль - выходим из тюрьмы
                    player.in_jail = False
                    player.jail_turns = 0
                    player.status = PlayerStatus.ACTIVE

                    await query.message.edit_text(
                        f"🎲 *ДУБЛЬ!*\n"
                        f"🎯 {dice1} + {dice2} = {total}\n"
                        f"🔓 Вы вышли из тюрьмы!\n"
                        f"🎉 Бесплатно!",
                        parse_mode="Markdown"
                    )
                else:
                    # Не дубль - остаемся в тюрьме
                    player.jail_turns += 1

                    await query.message.edit_text(
                        f"🎲 *Нет дубля*\n"
                        f"🎯 {dice1} + {dice2} = {total}\n"
                        f"🔒 Остаетесь в тюрьме\n"
                        f"📈 Ходов в тюрьме: {player.jail_turns}/3",
                        parse_mode="Markdown"
                    )

                game_manager.save_game_state(game_id)

        elif data.startswith("jail_pay_"):
            game_id = data.replace("jail_pay_", "")
            game = game_manager.get_game(game_id)
            if game and game.players.get(user.id):
                player = game.players[user.id]

                if player.money >= Config.JAIL_FINE:
                    player.deduct_money(Config.JAIL_FINE)
                    player.in_jail = False
                    player.jail_turns = 0
                    player.status = PlayerStatus.ACTIVE

                    await query.message.edit_text(
                        f"💵 *Штраф оплачен!*\n"
                        f"💸 Списан: ${Config.JAIL_FINE}\n"
                        f"🔓 Вы вышли из тюрьмы!\n"
                        f"💰 Ваш баланс: ${player.money}",
                        parse_mode="Markdown"
                    )
                else:
                    await query.message.edit_text(
                        f"❌ *Недостаточно денег!*\n"
                        f"💸 Нужно: ${Config.JAIL_FINE}\n"
                        f"💰 У вас: ${player.money}\n"
                        f"🔒 Остаетесь в тюрьме",
                        parse_mode="Markdown"
                    )

                game_manager.save_game_state(game_id)

        elif data.startswith("jail_card_"):
            game_id = data.replace("jail_card_", "")
            game = game_manager.get_game(game_id)
            if game and game.players.get(user.id):
                player = game.players[user.id]

                if player.get_out_of_jail_cards > 0:
                    player.get_out_of_jail_cards -= 1
                    player.in_jail = False
                    player.jail_turns = 0
                    player.status = PlayerStatus.ACTIVE

                    await query.message.edit_text(
                        f"🎫 *Карта использована!*\n"
                        f"🔓 Вы вышли из тюрьмы!\n"
                        f"📊 Осталось карт: {player.get_out_of_jail_cards}",
                        parse_mode="Markdown"
                    )
                else:
                    await query.message.edit_text(
                        f"❌ *Нет карт освобождения!*\n"
                        f"🔒 Остаетесь в тюрьме\n"
                        f"💡 Карты можно получить из Шанса/Казна",
                        parse_mode="Markdown"
                    )

                game_manager.save_game_state(game_id)

        elif data.startswith("jail_skip_"):
            game_id = data.replace("jail_skip_", "")
            game = game_manager.get_game(game_id)
            if game and game.players.get(user.id):
                player = game.players[user.id]

                player.jail_turns += 1

                await query.message.edit_text(
                    f"⏳ *Пропускаете ход*\n"
                    f"📈 Ходов в тюрьме: {player.jail_turns}/3\n"
                    f"🔒 Остаетесь в тюрьме",
                    parse_mode="Markdown"
                )

                game_manager.save_game_state(game_id)

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
    response = f"{player_color} *СОБСТВЕННОСТЬ {getattr(player, 'full_name', 'Игрок')}*\n\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ОСНОВНАЯ ИНФОРМАЦИЯ
    response += f"💰 *Баланс:* ${getattr(player, 'money', 0)}\n"
    response += f"📍 *Позиция:* {getattr(player, 'position', 0)}\n"
    response += f"🎨 *Цвет фишки:* {player_color}\n"
    response += f"🎮 *Статус:* {getattr(getattr(player, 'status', None), 'value', 'активен')}\n\n"
    # Формируем ответ

    # ОСНОВНАЯ ИНФОРМАЦИЯ

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


async def clear_expired_offers(context: ContextTypes.DEFAULT_TYPE):
    """Очистка просроченных предложений покупки"""
    try:
        if not context.user_data:
            return

        current_time = datetime.now().timestamp()

        # Проходим по всем пользователям в context.user_data
        for user_id, user_data in list(context.user_data.items()):
            if user_data is None:
                continue

            if isinstance(user_data, dict) and 'buy_offer' in user_data:
                buy_offer = user_data['buy_offer']
                if buy_offer is None:
                    continue

                timestamp = buy_offer.get('timestamp', 0)
                if current_time - timestamp > 30:  # 30 секунд
                    print(f"🧹 Очищаем просроченное предложение для пользователя {user_id}")

                    # Удаляем предложение
                    if 'buy_offer' in user_data:
                        del user_data['buy_offer']
                    if 'buy_timer' in user_data:
                        del user_data['buy_timer']

                    # Также можно удалить пустой словарь пользователя
                    if not user_data:
                        del context.user_data[user_id]

    except Exception as e:
        print(f"❌ Ошибка при очистке предложений: {e}")
        import traceback
        traceback.print_exc()

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

        # Добавляем задание для очистки просроченных предложений (каждые 10 секунд)
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(clear_expired_offers, interval=10, first=5)

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
        ("skip",skip_command),
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