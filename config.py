import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация бота Монополии"""

    # Токен бота
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8440935363:AAEe9pvkrYL3G-CLzcRXw9Qyy-aZLRVkX04")

    # Настройки игры
    START_MONEY = 1500
    MAX_PLAYERS = 8
    BOARD_SIZE = 40
    SALARY = 200
    JAIL_FINE = 50

    # Путь к базе данных
    DB_PATH = "data/games.db"

    # Цвета для игроков
    PLAYER_COLORS = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚫", "⚪"]


print("🎲 Конфигурация загружена")
print(f"🔧 Бот будет работать для всех пользователей!")