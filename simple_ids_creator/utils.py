from pathlib import Path
from typing import Any


def _ensure_parent_dir(path: str | Path) -> Path:
    """
    Создать родительскую директорию для файла при необходимости.

    :param path: Путь к целевому файлу.
    :returns: Нормализованный объект пути.
    """
    path_object = Path(path).expanduser().resolve()
    path_object.parent.mkdir(parents=True, exist_ok=True)
    return path_object
def _normalize_text(value: Any) -> str:
    """
    Нормализовать произвольное значение в очищенную строку.

    :param value: Входное значение.
    :returns: Строка без лишних пробелов и специальных `NaN`.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none"}:
        return ""
    return text


def _is_marked(value: Any) -> bool:
    """
    Проверить, что ячейка таблицы означает наличие требования.

    :param value: Значение ячейки.
    :returns: `True`, если ячейка помечена.
    """
    text = _normalize_text(value).lower()
    return text in {"1", "1.0", "true", "yes", "x", "да"}
