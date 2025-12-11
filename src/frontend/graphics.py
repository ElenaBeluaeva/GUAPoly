# src/frontend/graphics.py
from PIL import Image, ImageDraw, ImageFont
import os
from typing import Dict, List, Tuple, Optional, Any
import io
import math

# Цвета игроков (RGB)
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


class BoardRenderer:
    """Класс для отрисовки игрового поля с игроками и домами"""

    def __init__(self, board_image_path: str = "../assets/board.png"):
        """
        Инициализация рендерера

        Args:
            board_image_path: путь к изображению поля
        """
        self.board_image_path = board_image_path
        self.board_image = None
        self.font_small = None
        self.font_medium = None
        self.font_large = None
        self._load_board_image()
        self._load_fonts()

        # Координаты клеток - будем загружать из Python-файла
        self.cell_coordinates = self._load_coordinates()

    def _load_board_image(self):
        """Загружаем изображение поля"""
        try:
            # Пробуем разные пути
            paths_to_try = [
                self.board_image_path,
                f"assets/{os.path.basename(self.board_image_path)}",
                f"../assets/{os.path.basename(self.board_image_path)}",
                f"src/frontend/{os.path.basename(self.board_image_path)}",
                os.path.join(os.path.dirname(__file__), self.board_image_path)
            ]

            for path in paths_to_try:
                if os.path.exists(path):
                    self.board_image = Image.open(path).convert("RGBA")
                    print(f"✅ Изображение поля загружено: {path}")
                    print(f"   Размер: {self.board_image.size}")

                    # Если изображение слишком большое, масштабируем
                    if self.board_image.width > 1800 or self.board_image.height > 1800:
                        scale_factor = 1800 / max(self.board_image.width, self.board_image.height)
                        new_size = (int(self.board_image.width * scale_factor),
                                    int(self.board_image.height * scale_factor))
                        self.board_image = self.board_image.resize(new_size, Image.Resampling.LANCZOS)
                        print(f"   Масштабировано до: {self.board_image.size}")
                    return

            # Если файл не найден, создаем заглушку
            print("⚠️ Файл поля не найден, создаем заглушку...")
            self._create_dummy_board()

        except Exception as e:
            print(f"❌ Ошибка загрузки изображения: {e}")
            self._create_dummy_board()

    def _create_dummy_board(self):
        """Создаем заглушку для поля"""
        width, height = 1805, 1804
        self.board_image = Image.new('RGBA', (width, height), (240, 240, 220, 255))
        draw = ImageDraw.Draw(self.board_image)

        # Рисуем рамку поля
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(150, 150, 150, 255), width=3)

        # Рисуем угловые клетки
        corner_size = 180
        corners = [
            (width - corner_size, height - corner_size, "СТАРТ", (200, 255, 200)),  # правый нижний
            (0, height - corner_size, "ТЮРЬМА", (255, 220, 200)),  # левый нижний
            (0, 0, "ПАРКОВКА", (200, 255, 255)),  # левый верхний
            (width - corner_size, 0, "В ТЮРЬМУ", (255, 200, 200))  # правый верхний
        ]

        for x, y, text, color in corners:
            draw.rectangle([(x, y), (x + corner_size, y + corner_size)], fill=color + (200,))
            draw.rectangle([(x, y), (x + corner_size, y + corner_size)], outline=(100, 100, 100), width=2)

            # Текст в углах
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()

            # Разбиваем текст на строки
            words = text.split()
            for i, word in enumerate(words):
                draw.text(
                    (x + corner_size // 2, y + corner_size // 2 - 20 + i * 25),
                    word,
                    fill=(0, 0, 0, 255),
                    font=font,
                    anchor='mm'
                )

        # Подпись
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        draw.text(
            (width // 2, height // 2),
            "ПОЛЕ МОНОПОЛИИ",
            fill=(100, 100, 100, 255),
            font=font,
            anchor='mm'
        )

        draw.text(
            (width // 2, height // 2 + 60),
            f"Размер: {width}x{height}",
            fill=(150, 150, 150, 255),
            font=font,
            anchor='mm'
        )

    def _load_fonts(self):
        """Загружаем шрифты разных размеров"""
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
                if os.path.exists(path):
                    font_path = path
                    break

            if font_path:
                self.font_small = ImageFont.truetype(font_path, 12)
                self.font_medium = ImageFont.truetype(font_path, 14)
                self.font_large = ImageFont.truetype(font_path, 16)
            else:
                raise FileNotFoundError("Шрифт не найден")

        except Exception as e:
            print(f"⚠️ Не удалось загрузить шрифты: {e}")
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

    def _load_coordinates(self) -> Dict[int, Tuple[int, int]]:
        """Загружает координаты из Python-файла"""
        try:
            # Пробуем разные пути для импорта
            import sys
            import os
            from pathlib import Path

            # Добавляем родительскую директорию в путь Python
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))

            # Пробуем импортировать из board_coordinates_1805.py
            try:
                from board_coordinates_1805 import CELL_COORDINATES
                print(f"✅ Загружено {len(CELL_COORDINATES)} координат из Python-файла")
                return CELL_COORDINATES.copy()
            except ImportError:
                # Пробуем импортировать из config
                try:
                    from config import CELL_COORDINATES
                    print(f"✅ Загружено {len(CELL_COORDINATES)} координат из config")
                    return CELL_COORDINATES.copy()
                except ImportError:
                    # Используем стандартные координаты
                    print("⚠️ Python-файл с координатами не найден, использую расчетные координаты")
                    return self._calculate_fallback_coordinates()

        except Exception as e:
            print(f"❌ Ошибка загрузки координат: {e}")
            return self._calculate_fallback_coordinates()

    def _calculate_fallback_coordinates(self) -> Dict[int, Tuple[int, int]]:
        """Резервный расчет координат для поля 1805x1804"""
        width, height = self.board_image.size if self.board_image else (1805, 1804)
        coords = {}

        # Параметры для расчета
        border_width = 120  # Ширина границы
        inner_width = width - 2 * border_width
        inner_height = height - 2 * border_width

        # Верхняя сторона (клетки 0-9 слева направо)
        for i in range(10):
            x = border_width + (i * inner_width // 9)
            y = height - border_width
            coords[i] = (x, y)

        # Левая сторона (клетки 10-19 снизу вверх)
        for i in range(10):
            x = border_width
            y = height - border_width - (i * inner_height // 9)
            coords[10 + i] = (x, y)

        # Нижняя сторона (клетки 20-29 справа налево)
        for i in range(10):
            x = width - border_width - (i * inner_width // 9)
            y = border_width
            coords[20 + i] = (x, y)

        # Правая сторона (клетки 30-39 сверху вниз)
        for i in range(10):
            x = width - border_width
            y = border_width + (i * inner_height // 9)
            coords[30 + i] = (x, y)

        return coords

    def _draw_player_icon(self, draw: ImageDraw, x: int, y: int,
                          color: str, player_index: int = 0, total_players: int = 1,
                          cell_size: int = 160):
        """Рисуем иконку игрока на клетке"""
        rgb_color = PLAYER_COLORS_RGB.get(color, (255, 50, 50))

        # Радиус фишки в зависимости от количества игроков
        if total_players == 1:
            radius = min(20, cell_size // 8)
        elif total_players <= 3:
            radius = min(15, cell_size // 10)
        else:
            radius = min(12, cell_size // 12)

        # Если несколько игроков на клетке, располагаем по кругу
        if total_players > 1:
            angle = (player_index / total_players) * 2 * math.pi
            spread_radius = cell_size // 4  # Радиус расстановки
            offset_x = int(spread_radius * math.cos(angle))
            offset_y = int(spread_radius * math.sin(angle))
            center_x = x + offset_x
            center_y = y + offset_y
        else:
            center_x = x
            center_y = y

        # Рисуем фишку игрока
        draw.ellipse(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            fill=rgb_color,
            outline=(0, 0, 0),
            width=2
        )

        # Белая точка в центре для лучшей видимости
        draw.ellipse(
            [(center_x - radius // 3, center_y - radius // 3),
             (center_x + radius // 3, center_y + radius // 3)],
            fill=(255, 255, 255, 180)
        )

        # Номер игрока (если несколько)
        if total_players > 1:
            draw.text(
                (center_x, center_y),
                str(player_index + 1),
                fill=(255, 255, 255),
                font=self.font_small,
                anchor='mm',
                stroke_width=1,
                stroke_fill=(0, 0, 0)
            )

    def _draw_houses(self, draw: ImageDraw, x: int, y: int, houses: int, hotel: bool, cell_size: int = 160):
        """Рисуем дома/отели на собственности"""
        house_size = min(12, cell_size // 15)
        spacing = house_size + 2

        if hotel:
            # Отель - красный квадрат с белой "H"
            hotel_x = x + cell_size // 3
            hotel_y = y - cell_size // 3

            draw.rectangle(
                [(hotel_x - house_size * 2, hotel_y - house_size * 2),
                 (hotel_x + house_size * 2, hotel_y + house_size * 2)],
                fill=(220, 0, 0),
                outline=(120, 0, 0),
                width=2
            )
            draw.text(
                (hotel_x, hotel_y),
                "H",
                fill=(255, 255, 255),
                font=self.font_medium,
                anchor='mm',
                stroke_width=1,
                stroke_fill=(100, 0, 0)
            )
        elif houses > 0:
            # Дома - зеленые треугольники в ряд
            start_x = x - (houses * spacing) // 2

            for i in range(houses):
                house_x = start_x + i * spacing
                house_y = y - cell_size // 3

                # Треугольник (дом)
                points = [
                    (house_x, house_y - house_size),  # верх
                    (house_x - house_size, house_y),  # левый низ
                    (house_x + house_size, house_y)  # правый низ
                ]
                draw.polygon(points, fill=(0, 180, 0), outline=(0, 100, 0))

    def _draw_players_legend(self, draw: ImageDraw, players: List[Dict], board_width: int, board_height: int):
        """
        Рисует легенду с игроками в правом верхнем углу

        Args:
            draw: объект для рисования
            players: список игроков
            board_width: ширина доски
            board_height: высота доски
        """
        if not players:
            return

        # Определяем область для легенды - правый верхний угол
        legend_width = 300
        legend_height = 40 + len(players) * 35  # Высота зависит от количества игроков

        # Отступы от краев (200 пикселей от верхнего и правого края)
        margin_top = 350
        margin_right = 350

        # Позиция легенды - правый верхний угол с отступами
        legend_x = board_width - legend_width - margin_right
        legend_y = margin_top

        # Фон легенды с полупрозрачностью
        draw.rectangle(
            [(legend_x, legend_y),
             (legend_x + legend_width, legend_y + legend_height)],
            fill=(255, 255, 255, 230),  # Белый с небольшой прозрачностью
            outline=(150, 150, 150),
            width=2
        )

        # Закругленные углы (рисуем круги по углам)
        corner_radius = 8
        corners = [
            (legend_x, legend_y),  # левый верхний
            (legend_x + legend_width, legend_y),  # правый верхний
            (legend_x, legend_y + legend_height),  # левый нижний
            (legend_x + legend_width, legend_y + legend_height)  # правый нижний
        ]

        for cx, cy in corners:
            draw.ellipse(
                [(cx - corner_radius, cy - corner_radius),
                 (cx + corner_radius, cy + corner_radius)],
                fill=(255, 255, 255, 230)
            )

        # Заголовок легенды
        draw.text(
            (legend_x + legend_width // 2, legend_y + 15),
            "ИГРОКИ НА ПОЛЕ",
            fill=(0, 0, 0),
            font=self.font_medium,
            anchor='mm',
            stroke_width=1,
            stroke_fill=(200, 200, 200)
        )

        # Разделительная линия
        draw.line(
            [(legend_x + 10, legend_y + 35),
             (legend_x + legend_width - 10, legend_y + 35)],
            fill=(200, 200, 200),
            width=1
        )

        # Информация об игроках в 2 колонки, если игроков много
        max_players_per_column = 6
        use_two_columns = len(players) > max_players_per_column

        if use_two_columns:
            column1_players = players[:len(players) // 2 + len(players) % 2]
            column2_players = players[len(players) // 2 + len(players) % 2:]

            # Колонка 1
            for i, player in enumerate(column1_players):
                y_pos = legend_y + 50 + i * 30
                self._draw_player_in_legend(draw, player, legend_x + 20, y_pos)

            # Колонка 2
            for i, player in enumerate(column2_players):
                y_pos = legend_y + 50 + i * 30
                self._draw_player_in_legend(draw, player, legend_x + legend_width // 2 + 20, y_pos)
        else:
            # Одна колонка
            for i, player in enumerate(players):
                y_pos = legend_y + 50 + i * 30
                self._draw_player_in_legend(draw, player, legend_x + 20, y_pos)

    def _draw_player_in_legend(self, draw: ImageDraw, player: Dict, x: int, y: int):
        """Рисует информацию об одном игроке в легенде"""
        color = player.get("color", "🔴")
        rgb_color = PLAYER_COLORS_RGB.get(color, (255, 50, 50))
        name = player.get("name", "Игрок")[:12]  # Ограничиваем длину имени
        money = player.get("money", 0)
        position = player.get("position", 0)

        # Цветной круг игрока
        draw.ellipse(
            [(x, y - 8), (x + 16, y + 8)],
            fill=rgb_color,
            outline=(0, 0, 0),
            width=1
        )

        # Текущая позиция (номер клетки)
        position_text = f"{position}"
        draw.text(
            (x + 8, y),
            position_text,
            fill=(255, 255, 255),
            font=self.font_small,
            anchor='mm',
            stroke_width=1,
            stroke_fill=(0, 0, 0)
        )

        # Имя и деньги
        info_text = f"{name}: ${money:,}"
        draw.text(
            (x + 25, y),
            info_text,
            fill=(0, 0, 0),
            font=self.font_small,
            anchor='lm'
        )

    def _draw_property_info(self, draw: ImageDraw, properties: Dict, board_width: int, board_height: int):
        """Рисует информацию о собственностях (если нужно)"""
        # Можно добавить отображение заложенных свойств и т.д.
        pass

    def render_board(self, game_data: Dict, include_legend: bool = True) -> Image.Image:
        """
        Рендерим поле с игроками и собственностью

        Args:
            game_data: {
                "players": [
                    {"id": 123, "name": "Игрок1", "position": 5, "color": "🔴", "money": 1500}
                ],
                "properties": {
                    5: {"owner": 123, "houses": 2, "hotel": False},
                    12: {"owner": 456, "houses": 0, "hotel": False}
                }
            }
            include_legend: показывать ли легенду с игроками
        """
        # Создаем копию поля
        board_copy = self.board_image.copy()
        draw = ImageDraw.Draw(board_copy, 'RGBA')

        width, height = board_copy.size

        players = game_data.get("players", [])
        properties = game_data.get("properties", {})

        # Группируем игроков по клеткам
        players_by_cell = {}
        for player in players:
            pos = player.get("position", 0)
            if pos not in players_by_cell:
                players_by_cell[pos] = []
            players_by_cell[pos].append(player)

        # 1. Сначала рисуем дома/отели (они должны быть под игроками)
        for cell_id, prop_data in properties.items():
            if cell_id in self.cell_coordinates:
                x, y = self.cell_coordinates[cell_id]
                houses = prop_data.get("houses", 0)
                hotel = prop_data.get("hotel", False)

                if houses > 0 or hotel:
                    # Предполагаемый размер клетки для масштабирования
                    cell_size = 160  # Примерный размер клетки в пикселях
                    self._draw_houses(draw, x, y, houses, hotel, cell_size)

        # 2. Рисуем игроков поверх домов
        for cell_id, cell_players in players_by_cell.items():
            if cell_id in self.cell_coordinates:
                x, y = self.cell_coordinates[cell_id]
                cell_size = 160  # Примерный размер клетки

                for i, player in enumerate(cell_players):
                    color = player.get("color", "🔴")
                    self._draw_player_icon(draw, x, y, color, i, len(cell_players), cell_size)

        # 3. Рисуем легенду с игроками (если включено)
        if include_legend and players:
            self._draw_players_legend(draw, players, width, height)

        # 4. Информация о свойствах (опционально)
        if properties:
            self._draw_property_info(draw, properties, width, height)

        return board_copy

    def render_board(self, game_data: Dict, include_legend: bool = True) -> Image.Image:
        """Рендерим поле с игроками и собственностью"""
        # Создаем копию поля
        board_copy = self.board_image.copy()
        draw = ImageDraw.Draw(board_copy, 'RGBA')

        width, height = board_copy.size

        players = game_data.get("players", [])
        properties = game_data.get("properties", {})

        # Группируем игроков по клеткам
        players_by_cell = {}
        for player in players:
            pos = player.get("position", 0)
            if pos not in players_by_cell:
                players_by_cell[pos] = []
            players_by_cell[pos].append(player)

        # 1. Рисуем обозначения собственности (сначала, под всем остальным)
        if properties:
            self._draw_property_ownership(draw, properties, players, width, height)

        # 2. Рисуем дома/отели
        for cell_id, prop_data in properties.items():
            if cell_id in self.cell_coordinates:
                x, y = self.cell_coordinates[cell_id]
                houses = prop_data.get("houses", 0)
                hotel = prop_data.get("hotel", False)

                if houses > 0 or hotel:
                    cell_size = 160
                    self._draw_houses(draw, x, y, houses, hotel, cell_size)

        # 3. Рисуем игроков поверх всего
        for cell_id, cell_players in players_by_cell.items():
            if cell_id in self.cell_coordinates:
                x, y = self.cell_coordinates[cell_id]
                cell_size = 160

                for i, player in enumerate(cell_players):
                    color = player.get("color", "🔴")
                    self._draw_player_icon(draw, x, y, color, i, len(cell_players), cell_size)

        # 4. Рисуем легенду с игроками
        if include_legend and players:
            self._draw_players_legend(draw, players, width, height)

        return board_copy

    def _draw_property_ownership(self, draw: ImageDraw, properties: Dict, players: List[Dict],
                                 width: int, height: int):
        """Рисует обозначения собственности на поле"""
        # Создаем словарь игроков для быстрого доступа
        players_dict = {p['id']: p for p in players}

        # Размер иконки собственности
        ownership_size = 12

        for cell_id, prop_data in properties.items():
            if cell_id in self.cell_coordinates:
                x, y = self.cell_coordinates[cell_id]
                owner_id = prop_data.get('owner')

                if owner_id and owner_id in players_dict:
                    owner_color = players_dict[owner_id].get('color', '🔴')
                    rgb_color = PLAYER_COLORS_RGB.get(owner_color, (255, 50, 50))

                    # Рисуем небольшой квадратик в правом верхнем углу клетки
                    marker_x = x + 60  # Смещаем вправо
                    marker_y = y - 60  # Смещаем вверх

                    draw.rectangle(
                        [(marker_x - ownership_size, marker_y - ownership_size),
                         (marker_x + ownership_size, marker_y + ownership_size)],
                        fill=rgb_color,
                        outline=(255, 255, 255),
                        width=1
                    )

                    # Белый номер или инициал владельца
                    owner_name = players_dict[owner_id].get('name', '?')
                    initial = owner_name[0].upper() if owner_name else '?'

                    try:
                        draw.text(
                            (marker_x, marker_y),
                            initial,
                            fill=(255, 255, 255),
                            font=self.font_small,
                            anchor='mm',
                            stroke_width=1,
                            stroke_fill=(0, 0, 0)
                        )
                    except:
                        pass

    def save_to_bytes(self, image: Image.Image, format: str = 'PNG', quality: int = 95) -> bytes:
        """Конвертируем изображение в bytes для отправки в Telegram"""
        img_byte_arr = io.BytesIO()

        if format.upper() == 'JPEG' or format.upper() == 'JPG':
            # Для JPEG конвертируем в RGB
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image_to_save = rgb_image
            else:
                image_to_save = image
            image_to_save.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
        else:
            # Для PNG сохраняем как есть
            image.save(img_byte_arr, format='PNG', optimize=True)

        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def save_to_file(self, image: Image.Image, filename: str = "current_board.png") -> str:
        """Сохраняем изображение в файл"""
        os.makedirs("temp", exist_ok=True)
        filepath = f"temp/{filename}"
        image.save(filepath, format='PNG', optimize=True)
        print(f"✅ Изображение сохранено: {filepath}")
        return filepath

    def create_test_image(self):
        """Создает тестовое изображение для проверки"""
        # Тестовые данные
        test_players = [
            {"id": 1, "name": "Алексей", "position": 0, "color": "🔴", "money": 1500},
            {"id": 2, "name": "Мария", "position": 5, "color": "🔵", "money": 1450},
            {"id": 3, "name": "Иван", "position": 10, "color": "🟢", "money": 2100},
            {"id": 4, "name": "Ольга", "position": 15, "color": "🟡", "money": 1200},
            {"id": 5, "name": "Дмитрий", "position": 20, "color": "🟣", "money": 1800},
            {"id": 6, "name": "Светлана", "position": 25, "color": "🟠", "money": 950},
            {"id": 7, "name": "Михаил", "position": 30, "color": "⚫", "money": 1600},
            {"id": 8, "name": "Анна", "position": 35, "color": "⚪", "money": 1300}
        ]

        test_properties = {
            5: {"owner": 2, "houses": 3, "hotel": False},
            12: {"owner": 3, "houses": 0, "hotel": False},
            18: {"owner": 4, "houses": 4, "hotel": True},
            28: {"owner": 1, "houses": 2, "hotel": False}
        }

        game_data = {
            "players": test_players,
            "properties": test_properties
        }

        return self.render_board(game_data)


# Глобальный экземпляр рендерера
board_renderer = BoardRenderer()


# Функции для быстрого доступа
def create_board_image(players: List[Dict], properties: Dict = None) -> Image.Image:
    """Создает изображение доски с игроками"""
    if properties is None:
        properties = {}

    game_data = {
        "players": players,
        "properties": properties
    }

    return board_renderer.render_board(game_data)


def save_board_to_file(players: List[Dict], filename: str = "board.png") -> str:
    """Сохраняет доску с игроками в файл"""
    image = create_board_image(players)
    return board_renderer.save_to_file(image, filename)


def get_board_bytes(players: List[Dict], properties: Dict = None) -> bytes:
    """Возвращает байты изображения доски"""
    if properties is None:
        properties = {}

    game_data = {
        "players": players,
        "properties": properties
    }

    image = board_renderer.render_board(game_data)
    return board_renderer.save_to_bytes(image)


# Если файл запускается напрямую
if __name__ == "__main__":
    print("🧪 Тестирование модуля graphics.py")
    print("=" * 50)

    # Создаем тестовое изображение
    test_image = board_renderer.create_test_image()

    # Сохраняем для проверки
    output_path = board_renderer.save_to_file(test_image, "test_output.png")

    print(f"✅ Тестовое изображение создано: {output_path}")
    print(f"   Размер: {test_image.size}")
    print(f"   Координат загружено: {len(board_renderer.cell_coordinates)}")

    # Показываем несколько координат
    print("\n📍 Пример координат клеток:")
    for i in [0, 5, 10, 15, 20, 25, 30, 35]:
        if i in board_renderer.cell_coordinates:
            x, y = board_renderer.cell_coordinates[i]
            print(f"   Клетка {i:2d}: ({x:4d}, {y:4d})")

    print("=" * 50)