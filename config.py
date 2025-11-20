import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""

    # Основные настройки
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

    # Настройки игры
    START_MONEY = 1500
    MAX_PLAYERS = 8
    BOARD_SIZE = 40

    # Админы (добавьте свои ID через запятую)
    ADMIN_IDS = [844010980, 1373462530]  # Замените на ваш ID

    @staticmethod
    def validate():
        """Проверка конфигурации"""
        print("🎲 Конфигурация Монополии:")
        print(f"✅ BOT_TOKEN: {'установлен' if Config.BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ НЕ УСТАНОВЛЕН'}")
        print(f"✅ START_MONEY: ${Config.START_MONEY}")
        print(f"✅ MAX_PLAYERS: {Config.MAX_PLAYERS}")
        print(f"✅ ADMIN_IDS: {Config.ADMIN_IDS}")

        if Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("\n⚠️  Получите токен у @BotFather и добавьте в .env файл!")


Config.validate()