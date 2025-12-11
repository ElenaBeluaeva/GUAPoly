# calibrate_1805.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os


class BoardCalibrator1805:
    def __init__(self, image_path="assets/board.png"):
        self.image_path = image_path
        self.coordinates = {}
        self.current_cell = 0
        self.points = []

        if not os.path.exists(image_path):
            print(f"❌ Файл {image_path} не найден!")
            return

        self.root = tk.Tk()
        self.root.title(f"Калибровка координат для поля 1805x1804 - Клетка {self.current_cell}")
        self.root.geometry("1200x800")  # Фиксированный размер окна

        # Загружаем изображение
        self.img = Image.open(image_path)
        print(f"✅ Загружено изображение: {self.img.size}")

        # Создаем основной фрейм
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Создаем фрейм для элементов управления
        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Подсказка
        self.label = tk.Label(
            control_frame,
            text=f"Клетка {self.current_cell}: Кликните на центр клетки\n"
                 f"Координаты будут пересчитаны на оригинальный размер 1805x1804",
            font=('Arial', 12)
        )
        self.label.pack()

        # Поле для ручного ввода
        self.manual_frame = tk.Frame(control_frame)
        self.manual_frame.pack(pady=5)

        tk.Label(self.manual_frame, text="X:").pack(side=tk.LEFT)
        self.x_entry = tk.Entry(self.manual_frame, width=8)
        self.x_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(self.manual_frame, text="Y:").pack(side=tk.LEFT)
        self.y_entry = tk.Entry(self.manual_frame, width=8)
        self.y_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(self.manual_frame, text="Ввести", command=self.manual_input).pack(side=tk.LEFT, padx=5)

        # Информация
        self.info_label = tk.Label(control_frame, text="", font=('Arial', 10))
        self.info_label.pack(pady=5)

        # Кнопки управления
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="◀ Предыдущая", command=self.prev_cell).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="▶ Следующая", command=self.next_cell).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Пропустить", command=self.skip_cell).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Очистить", command=self.clear_cell).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Сохранить JSON", command=self.save_json).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Сохранить Python", command=self.save_python).pack(side=tk.LEFT, padx=5)

        # Создаем фрейм с прокруткой для изображения
        image_frame = tk.Frame(main_frame)
        image_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем канвас с прокруткой
        self.canvas = tk.Canvas(image_frame, bg="gray")

        # Добавляем скроллбары
        h_scrollbar = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        # Упаковываем элементы
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Масштабируем изображение для отображения (опционально уменьшаем)
        scale_factor = 0.6  # Можно уменьшить еще больше если нужно
        display_size = (int(self.img.width * scale_factor), int(self.img.height * scale_factor))
        self.display_img = self.img.resize(display_size, Image.Resampling.LANCZOS)

        self.photo = ImageTk.PhotoImage(self.display_img)

        # Создаем изображение на канвасе
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Устанавливаем область прокрутки
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

        # Привязываем клик
        self.canvas.bind("<Button-1>", self.on_click)

        # Привязываем колесико мыши для прокрутки
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Для Linux
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Для Linux

        # Показываем координаты
        self.update_info()

    def _on_mousewheel(self, event):
        """Прокрутка колесиком мыши"""
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")

    def scale_coordinates(self, x, y):
        """Пересчитываем координаты на оригинальный размер"""
        scale_x = self.img.width / self.display_img.width
        scale_y = self.img.height / self.display_img.height
        return int(x * scale_x), int(y * scale_y)

    def on_click(self, event):
        """Обработка клика по изображению"""
        # Получаем координаты относительно изображения на канвасе
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        orig_x, orig_y = self.scale_coordinates(canvas_x, canvas_y)
        self.coordinates[self.current_cell] = (orig_x, orig_y)

        # Рисуем метку на дисплейном изображении
        self.canvas.create_oval(
            canvas_x - 8, canvas_y - 8, canvas_x + 8, canvas_y + 8,
            fill='red', outline='white', width=2
        )
        self.canvas.create_text(
            canvas_x, canvas_y - 20,
            text=str(self.current_cell),
            fill='red', font=('Arial', 14, 'bold')
        )

        self.points.append((canvas_x, canvas_y, self.current_cell))
        self.update_info()

    def manual_input(self):
        """Ручной ввод координат"""
        try:
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            if 0 <= x < 1805 and 0 <= y < 1804:
                self.coordinates[self.current_cell] = (x, y)
                self.update_info()
                print(f"📝 Клетка {self.current_cell}: ручной ввод ({x}, {y})")

                # Рассчитываем координаты для отображения на масштабированном изображении
                scale_x = self.display_img.width / self.img.width
                scale_y = self.display_img.height / self.img.height
                display_x = x * scale_x
                display_y = y * scale_y

                # Рисуем точку
                self.canvas.create_oval(
                    display_x - 8, display_y - 8, display_x + 8, display_y + 8,
                    fill='blue', outline='white', width=2
                )
                self.canvas.create_text(
                    display_x, display_y - 20,
                    text=str(self.current_cell),
                    fill='blue', font=('Arial', 14, 'bold')
                )

                # Прокручиваем к точке
                self.canvas.xview_moveto(display_x / self.display_img.width)
                self.canvas.yview_moveto(display_y / self.display_img.height)

            else:
                print("❌ Координаты вне диапазона!")
        except ValueError:
            print("❌ Введите целые числа!")

    def update_info(self):
        """Обновляем информацию"""
        if self.current_cell in self.coordinates:
            x, y = self.coordinates[self.current_cell]
            self.info_label.config(
                text=f"Клетка {self.current_cell}: ({x}, {y}) | "
                     f"Задано: {len(self.coordinates)}/40 клеток",
                fg="green"
            )
        else:
            self.info_label.config(
                text=f"Клетка {self.current_cell}: не задана | "
                     f"Задано: {len(self.coordinates)}/40 клеток",
                fg="red"
            )

        self.root.title(f"Калибровка координат - Клетка {self.current_cell}")
        self.label.config(text=f"Клетка {self.current_cell}: Кликните на центр клетки\n"
                               f"Координаты будут пересчитаны на оригинальный размер 1805x1804")

    def next_cell(self):
        """Следующая клетка"""
        self.current_cell = (self.current_cell + 1) % 40
        self.update_info()

    def prev_cell(self):
        """Предыдущая клетка"""
        self.current_cell = (self.current_cell - 1) % 40
        self.update_info()

    def skip_cell(self):
        """Пропустить клетку"""
        if self.current_cell in self.coordinates:
            del self.coordinates[self.current_cell]
        self.next_cell()

    def clear_cell(self):
        """Очистить текущую клетку"""
        if self.current_cell in self.coordinates:
            del self.coordinates[self.current_cell]
        # Перерисовываем канвас
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        # Рисуем остальные точки
        for px, py, cell_num in self.points:
            if cell_num != self.current_cell:
                self.canvas.create_oval(
                    px - 8, py - 8, px + 8, py + 8,
                    fill='red', outline='white', width=2
                )
                self.canvas.create_text(
                    px, py - 20,
                    text=str(cell_num),
                    fill='red', font=('Arial', 14, 'bold')
                )
        self.update_info()

    def save_json(self):
        """Сохраняем в JSON"""
        with open('board_coordinates_1805.json', 'w', encoding='utf-8') as f:
            json.dump(self.coordinates, f, indent=2, ensure_ascii=False)
        print(f"✅ Координаты сохранены в board_coordinates_1805.json")
        print(f"   Задано клеток: {len(self.coordinates)}/40")

    def save_python(self):
        """Сохраняем в Python файл"""
        python_code = '''# board_coordinates_1805.py
# Автоматически сгенерированные координаты для поля 1805x1804

BOARD_WIDTH = 1805
BOARD_HEIGHT = 1804

CELL_COORDINATES = {
'''
        for cell in sorted(self.coordinates.keys()):
            x, y = self.coordinates[cell]
            python_code += f'    {cell}: ({x}, {y}),\n'

        python_code += '}\n'

        with open('board_coordinates_1805.py', 'w', encoding='utf-8') as f:
            f.write(python_code)

        print(f"✅ Координаты сохранены в board_coordinates_1805.py")
        print(f"   Задано клеток: {len(self.coordinates)}/40")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    calibrator = BoardCalibrator1805()
    calibrator.run()