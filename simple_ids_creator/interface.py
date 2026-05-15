from __future__ import annotations

import logging
import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox

from simple_ids_creator.ids_builder import build_ids_from_table, save_example_table
from simple_ids_creator.logger import Logger


class Program:
    """
    Графический интерфейс генератора IDS из таблиц.

    Интерфейс намеренно оставлен тонким: он только собирает входные пути,
    инициализирует логирование и вызывает функции модуля генерации IDS.
    Вся предметная логика преобразования таблицы находится в `ids_builder`.
    """

    def __init__(self) -> None:
        """
        Подготовить начальное состояние интерфейса.
        """
        self.table_paths: tuple[str, ...] = tuple()
        self.output_dir: str = ""

    def select_table_files(self) -> None:
        """
        Выбрать одну или несколько исходных таблиц CSV или Excel.
        """
        selected_paths = filedialog.askopenfilenames(
            title="Выберите таблицы требований",
            filetypes=[
                ("Tables", "*.csv *.xlsx *.xls *.xlsm *.xlsb"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xls *.xlsm *.xlsb"),
            ],
        )
        if selected_paths:
            self.table_paths = selected_paths
            self.table_label.config(text=f"Выбрано файлов: {len(self.table_paths)}")

    def select_output_dir(self) -> None:
        """
        Выбрать папку сохранения IDS-файлов.
        """
        selected_path = filedialog.askdirectory(title="Выберите папку для сохранения IDS")
        if selected_path:
            self.output_dir = selected_path
            self.output_label.config(text=self.output_dir)

    def open_output_dir(self) -> None:
        """
        Открыть папку с созданными IDS-файлами.
        """
        if not self.output_dir:
            messagebox.showerror("Ошибка", "Не выбрана папка с IDS.")
            return

        output_path = Path(self.output_dir).expanduser().resolve()
        if not output_path.exists():
            messagebox.showerror("Ошибка", f"Папка не существует: {output_path}")
            return

        try:
            if os.name == "nt":
                os.startfile(output_path)
            else:
                subprocess.run(["open", str(output_path)], check=True)
        except Exception as error:
            Logger.error(f"Ошибка открытия папки {output_path}: {error!r}", name="interface")
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {error}")

    def save_example_table(self) -> None:
        """
        Сохранить пример Excel-таблицы для дальнейшего редактирования.
        """
        selected_dir = filedialog.askdirectory(title="Выберите папку для сохранения примера таблицы")
        if not selected_dir:
            return

        output_path = Path(selected_dir).expanduser().resolve() / "example_ids_table.xlsx"
        try:
            result_path = save_example_table(output_path)
            self.list_box.insert(tk.END, f"Пример таблицы сохранен: {result_path}")
            Logger.info(f"Пример таблицы сохранен: {result_path}", name="interface")
        except Exception as error:
            self.list_box.insert(tk.END, f"Ошибка сохранения примера таблицы: {error}")
            Logger.error(f"Ошибка сохранения примера таблицы: {error!r}", name="interface")
            messagebox.showerror("Ошибка", f"Не удалось сохранить пример таблицы: {error}")

    def generate_ids(self) -> None:
        """
        Сгенерировать IDS из выбранных таблиц.
        """
        self.list_box.delete(0, tk.END)

        if not self.table_paths:
            messagebox.showerror("Ошибка", "Не выбраны исходные таблицы.")
            return
        if not self.output_dir:
            messagebox.showerror("Ошибка", "Не выбрана папка сохранения IDS.")
            return

        log_path = str(Path(self.output_dir).expanduser().resolve() / "table_to_ids.log")
        Logger.configure(log_file=log_path, level=logging.DEBUG)
        Logger.init("table_to_ids_ui")
        Logger.info("Запуск генерации IDS через интерфейс", name="interface")
        Logger.info(f"Количество таблиц: {len(self.table_paths)}", name="interface")
        Logger.info(f"Папка вывода: {self.output_dir}", name="interface")
        Logger.separator()

        success_count = 0
        error_count = 0
        for table_path in self.table_paths:
            Logger.separator("=")
            Logger.info(f"Начало обработки файла: {table_path}", name="interface")
            try:
                output_path = self._build_output_path(table_path)
                result_path = build_ids_from_table(
                    source_path=table_path,
                    output_path=output_path,
                )
                success_count += 1
                self.list_box.insert(tk.END, f"IDS создан: {result_path}")
                Logger.info(f"IDS создан: {result_path}", name="interface")
            except Exception as error:
                error_count += 1
                self.list_box.insert(tk.END, f"Ошибка: {Path(table_path).name} - {error}")
                Logger.error(f"Ошибка генерации IDS для {table_path}: {error!r}", name="interface")

        self.list_box.insert(tk.END, f"Успешно: {success_count}, ошибок: {error_count}")
        self.list_box.insert(tk.END, f"Лог: {Logger.path()}")
        if error_count:
            messagebox.showwarning("Генерация завершена", f"Успешно: {success_count}, ошибок: {error_count}")

    def initialize(self) -> None:
        """
        Создать и запустить главное окно приложения.
        """
        self.root = tk.Tk()
        self.root.title("Генератор IDS из таблиц")

        self.button_table = tk.Button(self.root, text="Выбрать таблицы", command=self.select_table_files)
        self.button_table.grid(row=0, column=0, padx=(10, 0), pady=10)
        self.table_label = tk.Label(self.root, text="", width=90, anchor="w")
        self.table_label.grid(row=0, column=1, padx=(10, 10))

        self.button_output = tk.Button(self.root, text="Выбрать папку IDS", command=self.select_output_dir)
        self.button_output.grid(row=1, column=0, padx=(10, 0), pady=10)
        self.output_label = tk.Label(self.root, text="", width=90, anchor="w")
        self.output_label.grid(row=1, column=1, padx=(10, 10))

        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=2, column=0, padx=(10, 0), pady=10)

        self.button_generate = tk.Button(self.button_frame, text="Сгенерировать IDS", command=self.generate_ids)
        self.button_generate.pack(side=tk.TOP, pady=(0, 5))

        self.button_open_dir = tk.Button(self.button_frame, text="Открыть папку IDS", command=self.open_output_dir)
        self.button_open_dir.pack(side=tk.TOP)

        self.button_save_example = tk.Button(
            self.button_frame,
            text="Сохранить пример таблицы",
            command=self.save_example_table,
        )
        self.button_save_example.pack(side=tk.TOP, pady=(5, 0))

        self.list_box = tk.Listbox(self.root, height=8, width=120)
        self.list_box.grid(row=2, column=1, padx=(10, 10), pady=10)

        self.root.mainloop()

    def _build_output_path(self, table_path: str) -> Path:
        """
        Построить путь к выходному IDS по имени исходной таблицы.

        :param table_path: Путь к исходной таблице.
        :returns: Путь к выходному IDS-файлу.
        """
        table_name = Path(table_path).stem
        return Path(self.output_dir).expanduser().resolve() / f"{table_name}.ids"
