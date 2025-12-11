# frontend/__init__.py
"""
Пакет для фронтенда бота Монополии
"""

from .combined_graphics import (
    create_combined_image,
    create_text_image,
    get_combined_board_bytes,
    create_game_message_with_board,
    TEXT_COLORS
)

from .graphics import (
    BoardRenderer,
    board_renderer,  # ← ИСПРАВЬТЕ ЗДЕСЬ: board_renderer вместо board_render
    create_board_image,
    save_board_to_file,
    get_board_bytes
)