import inspect
import logging
import os
from typing import Optional


class NonLockingFileHandler(logging.FileHandler):
    """
    Обработчик логов, который открывает файл только на время записи.

    Это упрощает работу с лог-файлом на Windows и позволяет безопаснее
    перемещать или удалять лог после завершения работы скрипта.
    """

    def emit(self, record):
        """Записать лог-сообщение, открывая и закрывая файл для каждой записи."""
        if self.stream is None:
            self.stream = self._open()

        try:
            logging.StreamHandler.emit(self, record)
            self.flush()
        finally:
            self.close()


class Logger:
    """
    Фасад над стандартным `logging` для простого файлового логирования.

    Класс скопирован и адаптирован из `ifc_checker_script`, чтобы сохранить
    знакомый формат и сценарий использования в текущем проекте.

    Example:
        >>> Logger.configure(log_file="log/app.log", level=logging.DEBUG)
        >>> Logger.init("table_to_ids")
        >>> Logger.info("Запуск конвертации")
    """

    _initialized: bool = False
    _log_file: str = "log/app.log"
    _level: int = logging.DEBUG
    _logger: Optional[logging.Logger] = None

    @classmethod
    def _ensure_initialized(cls) -> None:
        """
        Инициализировать корневой логгер один раз.

        :raises OSError: Если не удалось создать директорию для лог-файла.
        """
        if cls._initialized:
            return

        cls._log_file = os.path.abspath(cls._log_file)
        log_dir = os.path.dirname(cls._log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(name)s%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = NonLockingFileHandler(cls._log_file, encoding="utf-8", delay=True)
        file_handler.setLevel(cls._level)
        file_handler.setFormatter(formatter)

        cls._logger = logging.getLogger()
        if cls._logger.hasHandlers():
            cls._logger.handlers.clear()
        cls._logger.setLevel(cls._level)
        cls._logger.addHandler(file_handler)
        cls._logger.propagate = False
        cls._initialized = True

    @classmethod
    def configure(cls, log_file: str = "app.log", level: int = logging.INFO) -> None:
        """
        Настроить путь к лог-файлу и уровень логирования.

        :param log_file: Путь к лог-файлу.
        :param level: Уровень логирования.
        :raises ValueError: Если путь к лог-файлу пустой.
        :raises TypeError: Если `level` не является целым числом.
        """
        if not isinstance(log_file, str) or not log_file.strip():
            raise ValueError("log_file must be a non-empty string.")
        if not isinstance(level, int):
            raise TypeError("level must be an integer.")
        cls._log_file = os.path.abspath(log_file)
        cls._level = level
        cls._initialized = False

    @classmethod
    def init(cls, script_name: str) -> None:
        """
        Инициализировать лог-файл и записать заголовок запуска.

        :param script_name: Название сценария или команды.
        :raises ValueError: Если `script_name` пустой.
        """
        if not script_name or not isinstance(script_name, str):
            raise ValueError("script_name must be a non-empty string.")

        cls._ensure_initialized()

        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"{'=' * 50}\n"
            f"СКРИПТ: {script_name}\n"
            f"ЗАПУСК: {timestamp}\n"
            f"{'=' * 50}\n"
        )

        if cls._logger is not None:
            for handler in cls._logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            cls._logger.handlers.clear()
        cls._initialized = False

        log_dir = os.path.dirname(cls._log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(cls._log_file, "w", encoding="utf-8") as file_object:
            file_object.write(header)

        cls._ensure_initialized()

    @classmethod
    def separator(cls, sep: str = "-") -> None:
        """
        Записать в лог визуальный разделитель.

        :param sep: Символ разделителя.
        """
        cls._ensure_initialized()
        with open(cls._log_file, "a", encoding="utf-8") as file_object:
            file_object.write(f"{sep * 80}\n")

    @classmethod
    def _get_logger(cls, name: str) -> logging.Logger:
        """
        Получить дочерний логгер.

        :param name: Имя подсистемы.
        :returns: Дочерний логгер.
        """
        cls._ensure_initialized()
        return cls._logger.getChild(name)

    @classmethod
    def debug(cls, message: str = "", name: str = "") -> None:
        """
        Записать сообщение уровня DEBUG.

        :param message: Текст сообщения.
        :param name: Имя подсистемы.
        """
        cls._get_logger(name).debug(message, stacklevel=2)

    @classmethod
    def info(cls, message: str = "", name: str = "") -> None:
        """
        Записать сообщение уровня INFO.

        :param message: Текст сообщения.
        :param name: Имя подсистемы.
        """
        cls._get_logger(name).info(message, stacklevel=2)

    @classmethod
    def warning(cls, message: str = "", name: str = "") -> None:
        """
        Записать сообщение уровня WARNING.

        :param message: Текст сообщения.
        :param name: Имя подсистемы.
        """
        cls._get_logger(name).warning(message, stacklevel=2)

    @classmethod
    def error(cls, message: str = "", name: str = "") -> None:
        """
        Записать сообщение уровня ERROR.

        :param message: Текст сообщения.
        :param name: Имя подсистемы.
        """
        cls._get_logger(name).error(message, stacklevel=2)

    @classmethod
    def critical(cls, message: str = "", name: str = "") -> None:
        """
        Записать сообщение уровня CRITICAL.

        :param message: Текст сообщения.
        :param name: Имя подсистемы.
        """
        cls._get_logger(name).critical(message, stacklevel=2)

    @classmethod
    def path(cls) -> str:
        """
        Вернуть путь к текущему лог-файлу.

        :returns: Абсолютный путь к лог-файлу.
        """
        return cls._log_file

    @classmethod
    def data(cls, data, label: str = "", name: str = "data", max_items: int = 20) -> None:
        """
        Логировать структуру данных для отладки.

        :param data: Данные для логирования.
        :param label: Краткая подпись блока данных.
        :param name: Имя подсистемы.
        :param max_items: Максимальное число выводимых элементов.
        """
        cls._ensure_initialized()
        cls._get_logger(name).debug(msg=f"ДАННЫЕ [{label}]:", stacklevel=2)

        if isinstance(data, dict):
            cls._get_logger(name).debug(msg=f"Тип: dict, Кол-во: {len(data)}", stacklevel=2)
            for index, (key, value) in enumerate(data.items()):
                if index >= max_items:
                    cls._get_logger(name).debug(msg=f"... и ещё {len(data) - max_items}", stacklevel=2)
                    break
                value_string = str(value)
                if len(value_string) > 120:
                    value_string = value_string[:120] + "..."
                cls._get_logger(name).debug(msg=f"   [{key}] = {value_string}", stacklevel=2)
            return

        if isinstance(data, (list, tuple)):
            cls._get_logger(name).debug(msg=f"Тип: {type(data).__name__}, Кол-во: {len(data)}", stacklevel=2)
            for index, item in enumerate(data):
                if index >= max_items:
                    cls._get_logger(name).debug(msg=f"... и ещё {len(data) - max_items}", stacklevel=2)
                    break
                item_string = str(item)
                if len(item_string) > 120:
                    item_string = item_string[:120] + "..."
                cls._get_logger(name).debug(msg=f"   [{index}] {item_string}", stacklevel=2)
            return

        cls._get_logger(name).debug(msg=f"Тип: {type(data).__name__}", stacklevel=2)
        cls._get_logger(name).debug(msg=f"  Значение: {data}", stacklevel=2)

