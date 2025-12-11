# combined_graphics.py
"""
Функции для создания совмещенных изображений с текстом и игровым полем
"""

import io
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Optional, Tuple
from .graphics import board_renderer, create_board_image, get_board_bytes

# Цвета для текста
TEXT_COLORS = {
    'title': (0, 0, 0),  # черный
    'subtitle': (50, 50, 50),  # темно-серый
    'highlight': (220, 0, 0),  # красный
    'success': (0, 150, 0),  # зеленый
    'money': (0, 100, 0),  # темно-зеленый
    'warning': (200, 100, 0),  # оранжевый
    'info': (0, 100, 200),  # синий
}

# Цвета игроков (добавьте этот словарь, или импортируйте из graphics.py)
PLAYER_COLORS_RGB = {
    "🔴": (255, 50, 50),  # Красный
    "🔵": (50, 120, 255),  # Синий
    "🟢": (50, 200, 50),  # Зеленый
    "🟡": (255, 220, 50),  # Желтый
    "🟣": (200, 50, 200),  # Фиолетовый
    "🟠": (255, 150, 50),  # Оранжевый
    "⚫": (30, 30, 30),  # Черный
    "⚪": (240, 240, 240),  # Белый
    "🟤": (160, 120, 80),  # Коричневый
    "🌊": (50, 150, 200),  # Голубой
}


def create_combined_image(game_data: Dict, text_message: str,
                          player_color: str = "🔴",
                          show_legend: bool = True) -> Image.Image:
    """
    Создает совмещенное изображение: игровое поле + текстовое сообщение

    Args:
        game_data: данные игры для отрисовки поля
        text_message: текстовое сообщение для отображения
        player_color: цвет текущего игрока
        show_legend: показывать ли легенду с игроками
    """
    # 1. Создаем изображение поля
    board_image = board_renderer.render_board(game_data, include_legend=show_legend)

    # 2. Создаем изображение с текстом
    text_image = create_text_image(text_message, board_image.width)

    # 3. Объединяем изображения вертикально
    total_height = board_image.height + text_image.height
    combined = Image.new('RGB', (board_image.width, total_height), (255, 255, 255))

    # Вставляем текстовую часть вверху
    combined.paste(text_image, (0, 0))

    # Вставляем поле под текстом
    combined.paste(board_image, (0, text_image.height))

    # 4. Добавляем рамку текущего игрока
    # ИСПРАВЛЕНО: используем PLAYER_COLORS_RGB из текущего файла
    rgb_color = PLAYER_COLORS_RGB.get(player_color, (255, 50, 50))
    draw = ImageDraw.Draw(combined)

    # Толстая цветная рамка вверху (5 пикселей)
    draw.rectangle(
        [(0, 0), (board_image.width, 5)],
        fill=rgb_color,
        outline=None,
        width=0
    )

    # Тонкая рамка вокруг всего изображения
    draw.rectangle(
        [(0, 0), (board_image.width - 1, total_height - 1)],
        outline=(200, 200, 200),
        width=2
    )

    return combined


def create_text_image(text: str, width: int, padding: int = 20) -> Image.Image:
    """
    Создает изображение с текстом

    Args:
        text: текст для отображения
        width: ширина изображения
        padding: отступы по краям
    """
    # Пробуем загрузить шрифты
    try:
        # Пробуем разные шрифты
        font_paths = [
            "arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]

        font_path = None
        for path in font_paths:
            try:
                import os
                if os.path.exists(path):
                    font_path = path
                    break
            except:
                continue

        if font_path:
            title_font = ImageFont.truetype(font_path, 24)
            body_font = ImageFont.truetype(font_path, 18)
            small_font = ImageFont.truetype(font_path, 14)
        else:
            raise FileNotFoundError("Шрифт не найден")
    except:
        # Используем стандартные шрифты
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Разбиваем текст на строки
    lines = text.split('\n')

    # Рассчитываем высоту текста
    line_height = 30
    title_height = 40
    spacing = 10

    total_height = padding * 2
    for i, line in enumerate(lines):
        if i == 0:  # Первая строка - заголовок
            total_height += title_height
        else:
            total_height += line_height

        if i < len(lines) - 1:
            total_height += spacing

    # Создаем изображение для текста
    text_image = Image.new('RGB', (width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(text_image)

    # Рисуем текст
    y_position = padding
    for i, line in enumerate(lines):
        # Определяем цвет и шрифт
        if i == 0:  # Заголовок
            font = title_font
            color = TEXT_COLORS['title']
            is_bold = True
        elif line.startswith('💰') or line.startswith('🎯') or line.startswith('📍'):  # Важная информация
            font = body_font
            color = TEXT_COLORS['highlight']
            is_bold = True
        elif 'покупает' in line.lower() or 'купил' in line.lower():  # Покупка
            font = body_font
            color = TEXT_COLORS['success']
            is_bold = True
        elif 'платит' in line.lower() or 'оплата' in line.lower():  # Платежи
            font = body_font
            color = TEXT_COLORS['money']
            is_bold = False
        else:  # Обычный текст
            font = small_font
            color = TEXT_COLORS['subtitle']
            is_bold = False

        # Рисуем текст
        try:
            # Позиционируем по центру
            text_width = draw.textlength(line, font=font)
            x_position = (width - text_width) // 2

            if is_bold:
                # Рисуем текст с обводкой для жирности
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        draw.text(
                            (x_position + dx, y_position + dy),
                            line,
                            fill=color,
                            font=font,
                            stroke_width=0
                        )

            draw.text(
                (x_position, y_position),
                line,
                fill=color,
                font=font,
                stroke_width=0
            )
        except:
            # Если не удалось нарисовать, используем стандартный метод
            draw.text(
                (padding, y_position),
                line,
                fill=color,
                font=font
            )

        # Увеличиваем позицию Y
        if i == 0:  # Заголовок
            y_position += title_height + spacing
        else:
            y_position += line_height + spacing

    return text_image


def get_combined_board_bytes(game_data: Dict, text_message: str,
                             player_color: str = "🔴") -> bytes:
    """
    Возвращает байты совмещенного изображения
    """
    combined_image = create_combined_image(game_data, text_message, player_color)

    # Конвертируем в bytes для Telegram
    img_byte_arr = io.BytesIO()
    combined_image.save(img_byte_arr, format='PNG', optimize=True)
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()


# Функция для быстрого создания сообщения с полем
def create_game_message_with_board(game_data: Dict,
                                   player_name: str,
                                   dice_result: Tuple[int, int, int] = None,
                                   action: str = "",
                                   details: str = "") -> Tuple[str, bytes]:
    """
    Создает текстовое сообщение и изображение для отправки в игре
    """
    dice1, dice2, total = dice_result or (0, 0, 0)

    # Формируем текст
    text_lines = []

    if dice_result:
        text_lines.append(f"🎲 {player_name} бросает кубики")
        text_lines.append(f"🎯 {dice1} + {dice2} = {total}")
        text_lines.append("")

    if action:
        if action == "buy":
            text_lines.append("✅ ПОКУПКА СОБСТВЕННОСТИ")
        elif action == "rent":
            text_lines.append("💸 ОПЛАТА РЕНТЫ")
        elif action == "tax":
            text_lines.append("💰 ОПЛАТА НАЛОГА")
        elif action == "jail":
            text_lines.append("🔒 ОТПРАВЛЕН В ТЮРЬМУ")
        elif action == "free":
            text_lines.append("🅿️ БЕСПЛАТНАЯ СТОЯНКА")
        elif action == "start":
            text_lines.append("🚀 ПРОЙДЕН СТАРТ")

        if details:
            text_lines.append(details)

    # Получаем цвет текущего игрока
    current_player = None
    for player in game_data.get("players", []):
        if player.get("name") == player_name:
            current_player = player
            break

    player_color = current_player.get("color", "🔴") if current_player else "🔴"

    # Создаем совмещенное изображение
    text_message = "\n".join(text_lines)
    image_bytes = get_combined_board_bytes(game_data, text_message, player_color)

    # Минимальный текст для Telegram (некоторые клиенты требуют текст)
    telegram_text = f"🎲 {player_name}"
    if dice_result:
        telegram_text += f"\n🎯 {dice1}+{dice2}={total}"

    return telegram_text, image_bytes