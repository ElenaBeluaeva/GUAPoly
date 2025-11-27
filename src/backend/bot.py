from telegram import Update
from telegram.ext import ContextTypes
from src.backend.game import Game, active_games
from src.backend.player import Player


# Временное хранилище игр в памяти
game_counter = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 Добро пожаловать в Монополию!\n"
        "Используйте /newgame чтобы создать новую игру\n"
        "Используйте /join чтобы присоединиться к игре"
    )

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global game_counter
        user = update.effective_user
        game_counter += 1

        print(">>> NEWGAME handler triggered")  # тестовый вывод в консоль

        # Создаем объект игры
        game = Game(game_counter, user.id)

        # Создаем игрока и добавляем его в игру
        player = Player(user.id, user.username or user.first_name)
        game.add_player(player)

        # <<< ВОТ ТУТ СТАВИМ
        active_games[game_counter] = game
        context.chat_data["active_game"] = game_counter

        # Здесь уже можно отправить сообщение, клавиатуру и т.д.
        await update.message.reply_text("Игра создана! Ожидание других игроков...")

        await update.message.reply_text(
             f"🎮 Игра #{game_counter} создана!\n"
             f"Игроки могут присоединиться: /join {game_counter}\n"
             f"Игроки в лобби: {[p.username for p in game.players]}"
         )



async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text("Укажите номер игры: /join <id>")
        return

    game_id = int(args[0])

    if game_id not in active_games:
        await update.message.reply_text("❌ Игры с таким ID нет")
        return

    game = active_games[game_id]

    player = Player(user.id, user.username)
    if not game.add_player(player):
        await update.message.reply_text("⚠ Вы уже в игре или игра уже началась")
        return

    await update.message.reply_text(
        f"👤 {user.username} присоединился!\n"
        f"Игроки в лобби: {[p.username for p in game.players]}"
    )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        return await update.message.reply_text("Укажите ID игры: /startgame <id>")

    game_id = int(args[0])
    if game_id not in active_games:
        return await update.message.reply_text("❌ Игра не найдена")

    game = active_games[game_id]

    if game.start_game():
        await update.message.reply_text(
            f"🚀 Игра #{game_id} началась!\n"
            f"Первый игрок: {game.current_player.username}\n"
            f"Бросайте кубики командой: /roll {game_id}"
        )
    else:
        await update.message.reply_text("❌ Нужны минимум 2 игрока")

async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game_id = context.chat_data.get("active_game")

    if not game_id or game_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры в этом чате!")
        return

    game = active_games[game_id]

    d1, d2, cell = game.move_current_player()

    await update.message.reply_text(
        f"🎲 {user.username} бросил кубики: {d1} + {d2} = {d1+d2}\n"
        f"📍 Вы попали на: {cell.name}"
    )

