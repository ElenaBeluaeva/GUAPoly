from telegram import Update
from telegram.ext import ContextTypes
from .game import Game

# Временное хранилище игр в памяти
active_games = {}
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

    game = Game(game_counter, user.id)
    player = Player(user.id, user.username or user.first_name)
    game.add_player(player)
    active_games[game_counter] = game

    await update.message.reply_text(
        f"🎮 Игра #{game_counter} создана!\n"
        f"Игроки могут присоединиться с помощью: /join {game_counter}\n"
        f"Игроки в лобби: {[p.username for p in game.players]}"
    )


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Базовая реализация - будет расширена
    await update.message.reply_text("Функция присоединения в разработке")