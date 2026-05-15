from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import pandas as pd
from ifctester import ids

from simple_ids_creator.logger import Logger
from simple_ids_creator.utils import _ensure_parent_dir, _is_marked, _normalize_text

MODULE_NAME = "ids_builder"
_DEFAULT_SPECIFICATION_USAGE = "optional"
_DEFAULT_IFC_VERSIONS = ["IFC2X3", "IFC4", "IFC4X3_ADD2"]
_DEFAULT_PROPERTY_SET_NAME = "Параметры"
_SUPPORTED_IFC_DATA_TYPES: set[str] = set()


def build_ids_from_table(
    source_path: str | Path,
    output_path: str | Path,
    *,
    specification_usage: str = _DEFAULT_SPECIFICATION_USAGE,
    ifc_versions: list[str] | None = None,
) -> Path:
    """
    Преобразовать CSV или Excel-таблицу в IDS-файл.

    :param source_path: Путь к CSV/XLS/XLSX-файлу.
    :param output_path: Путь, по которому будет сохранен IDS.
    :param specification_usage: Использование спецификаций: `required`, `optional`, `prohibited`.
    :param ifc_versions: Список IFC-схем, которые нужно указать в IDS.
    :returns: Абсолютный путь к созданному IDS-файлу.
    :raises ValueError: Если таблица не содержит распознаваемых требований.
    """
    source_path = Path(source_path).expanduser().resolve()
    output_path = _ensure_parent_dir(output_path)
    Logger.info(f"Чтение таблицы: {source_path}", name=MODULE_NAME)
    table_frame = _read_table(source_path)
    title, requirement_rows = _extract_requirement_rows(table_frame)
    requirement_rows = _prepare_requirement_rows(requirement_rows, source_path.name)
    Logger.info(f"Извлечено строк требований: {len(requirement_rows)}", name=MODULE_NAME)

    specifications_by_class = _build_specifications_by_class(
        requirement_rows,
        specification_usage=specification_usage,
        ifc_versions=ifc_versions or list(_DEFAULT_IFC_VERSIONS),
        document_name=source_path.stem,
    )
    if not specifications_by_class:
        raise ValueError("Не удалось создать ни одной спецификации IDS из переданной таблицы.")

    ids_document = ids.Ids(title=title or source_path.stem)
    ids_document.specifications.extend(specifications_by_class.values())

    is_valid = ids_document.to_xml(str(output_path))
    Logger.info(f"IDS сохранен: {output_path}", name=MODULE_NAME)
    Logger.info(f"XMLSchema validation result: {is_valid}", name=MODULE_NAME)
    return output_path


def save_example_table(output_path: str | Path) -> Path:
    """
    Сохранить пример Excel-таблицы для ручного заполнения требований.

    Шаблон создается в формате, который ожидает текущий конвертер:
    первая строка содержит заголовок таблицы, вторая строка содержит
    заголовки колонок, далее идут строки параметров и IFC-классов.

    :param output_path: Путь к выходному `.xlsx` файлу.
    :returns: Абсолютный путь к сохраненному шаблону.
    """
    output_path = _ensure_parent_dir(output_path)
    template_rows = [
        [
            "Пример таблицы требований к информационному наполнению моделей",
            "",
            "",
            "",
            "",
            "",
            "",
        ],
        [
            "№",
            "Имя атрибута",
            "Тип значения",
            "IFC property set (опционально)",
            "IfcWall",
            "IfcDoor",
            "IfcWindow",
        ],
        ["1", "Марка", "IFCLABEL", "", "1", "1", "1"],
        ["2", "Наименование", "IFCLABEL", "", "1", "1", "1"],
        ["3", "Огнестойкость", "IFCLABEL", "Параметры", "1", "1", ""],
        ["4", "IsExternal", "IFCBOOLEAN", "Pset_WallCommon", "1", "", ""],
        ["5", "Ширина", "IFCLENGTHMEASURE", "Параметры", "", "1", "1"],
    ]
    dataframe = pd.DataFrame(template_rows)
    dataframe.to_excel(output_path, header=False, index=False)
    Logger.info(f"Сохранен пример таблицы: {output_path}", name=MODULE_NAME)
    return output_path


def _read_table(source_path: Path) -> pd.DataFrame:
    """
    Прочитать табличный файл в `DataFrame`.

    :param source_path: Путь к исходному файлу.
    :returns: Прочитанная таблица без полностью пустых строк и столбцов.
    :raises ValueError: Если формат файла не поддерживается.
    """
    suffix = source_path.suffix.lower()
    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(source_path, header=None, sep=None, engine="python")
        elif suffix in {".xlsx", ".xls", ".xlsm", ".xlsb"}:
            dataframe = pd.read_excel(source_path, header=None, sheet_name=0)
        else:
            raise ValueError(f"Неподдерживаемый формат таблицы: {source_path.suffix}")
    except Exception as error:
        raise ValueError(f"Ошибка чтения файла '{source_path.name}': {error!r}") from error

    dataframe = dataframe.dropna(axis=0, how="all").dropna(axis=1, how="all")
    dataframe = dataframe.reset_index(drop=True)
    Logger.data(dataframe.head(10).to_dict(), label="Первые строки таблицы", name=MODULE_NAME)
    return dataframe


def _extract_requirement_rows(table_frame: pd.DataFrame) -> tuple[str, list[dict[str, Any]]]:
    """
    Извлечь заголовок таблицы и список строк требований.

    Ожидается структура вида:
    - первая строка: заголовок таблицы;
    - вторая строка: шапка;
    - остальные строки: данные.

    :param table_frame: Сырые табличные данные.
    :returns: Заголовок и нормализованные строки требований.
    :raises ValueError: Если таблица слишком короткая.
    """
    if len(table_frame.index) < 3:
        raise ValueError("В таблице недостаточно строк для извлечения шапки и данных.")

    title = _normalize_text(table_frame.iloc[0, 0])
    data_frame = table_frame.iloc[2:].copy()
    data_frame = data_frame.reset_index(drop=True)

    requirement_rows: list[dict[str, Any]] = []
    class_headers = [_normalize_text(value) for value in table_frame.iloc[1, 4:].tolist()]

    for _, row in data_frame.iterrows():
        source_name = _normalize_text(row.iloc[1])
        if not source_name:
            continue
        marked_classes = [
            class_name
            for class_name, cell_value in zip(class_headers, row.iloc[4:].tolist(), strict=False)
            if class_name and _is_marked(cell_value)
        ]
        if not marked_classes:
            continue
        requirement_rows.append(
            {
                "source_name": source_name,
                "value_type": _normalize_text(row.iloc[2]),
                "property_set": _normalize_text(row.iloc[3]),
                "ifc_classes": marked_classes,
                "row_number": _normalize_text(row.iloc[0]),
            }
        )

    return title, requirement_rows


def _build_specifications_by_class(
    requirement_rows: list[dict[str, Any]],
    *,
    specification_usage: str,
    ifc_versions: list[str],
    document_name: str,
) -> dict[str, ids.Specification]:
    """
    Сгруппировать табличные требования в спецификации по IFC-классам.

    :param requirement_rows: Нормализованные строки требований.
    :param specification_usage: Уровень использования спецификации.
    :param ifc_versions: Поддерживаемые IFC-версии.
    :param document_name: Имя исходного документа без расширения.
    :returns: Словарь `IfcClass -> Specification`.
    """
    specifications_by_class: dict[str, ids.Specification] = {}
    for requirement_row in requirement_rows:
        facet_blueprint = _resolve_facet_blueprint(requirement_row)
        if facet_blueprint is None:
            Logger.warning(
                f"Строка '{requirement_row['source_name']}' пропущена: не удалось определить facet.",
                name=MODULE_NAME,
            )
            continue

        for ifc_class in requirement_row["ifc_classes"]:
            specification = specifications_by_class.setdefault(
                ifc_class,
                _create_specification(
                    ifc_class,
                    specification_usage=specification_usage,
                    ifc_versions=ifc_versions,
                    document_name=document_name,
                ),
            )
            requirement_facet = _create_requirement_facet(facet_blueprint, requirement_row, ifc_class)
            if requirement_facet is not None:
                specification.requirements.append(requirement_facet)

    return specifications_by_class


def _prepare_requirement_rows(requirement_rows: list[dict[str, Any]], source_filename: str) -> list[dict[str, Any]]:
    """
    Подготовить строки требований перед группировкой по спецификациям.

    Здесь выполняется предварительная проверка `dataType`, чтобы не логировать
    одну и ту же ошибку для каждого IFC-класса отдельно.

    :param requirement_rows: Исходные строки требований.
    :param source_filename: Имя обрабатываемого файла.
    :returns: Обновленные строки требований.
    """
    prepared_rows: list[dict[str, Any]] = []
    for requirement_row in requirement_rows:
        row_copy = dict(requirement_row)
        row_copy["resolved_data_type"] = _resolve_ifc_data_type(
            requirement_row["value_type"],
            requirement_row["source_name"],
            source_filename,
        )
        prepared_rows.append(row_copy)
    return prepared_rows


def _create_specification(
    ifc_class: str,
    *,
    specification_usage: str,
    ifc_versions: list[str],
    document_name: str,
) -> ids.Specification:
    """
    Создать базовую IDS-спецификацию для одного IFC-класса.

    :param ifc_class: Имя IFC-класса.
    :param specification_usage: Использование спецификации.
    :param ifc_versions: Список IFC-версий.
    :param document_name: Имя исходного документа без расширения.
    :returns: Созданная спецификация.
    """
    specification = ids.Specification(
        name=f"Требования к {ifc_class}",
        ifcVersion=ifc_versions,
        description=f"Требования к {ifc_class} по документу {document_name}",
    )
    specification.set_usage(specification_usage)
    specification.applicability.append(ids.Entity(name=ifc_class.upper()))
    return specification


def _resolve_facet_blueprint(requirement_row: dict[str, Any]) -> dict[str, Any] | None:
    """
    Определить схему построения facet-а для строки таблицы.

    :param requirement_row: Строка таблицы.
    :returns: Описание facet-а или `None`, если строка не поддержана.
    """
    return {
        "facet": "property",
        "baseName": requirement_row["source_name"],
        "propertySet": requirement_row["property_set"] or _DEFAULT_PROPERTY_SET_NAME,
    }


def _create_requirement_facet(
    facet_blueprint: dict[str, Any],
    requirement_row: dict[str, Any],
    ifc_class: str,
) -> Any | None:
    """
    Создать requirement facet для конкретного IFC-класса.

    :param facet_blueprint: Шаблон facet-а.
    :param requirement_row: Исходная строка таблицы.
    :param ifc_class: Текущий IFC-класс.
    :returns: Экземпляр facet-а `ifctester.ids` или `None`.
    """
    facet_type = facet_blueprint["facet"]
    if facet_type == "property":
        property_set = facet_blueprint.get("propertySet") or _DEFAULT_PROPERTY_SET_NAME
        data_type = requirement_row.get("resolved_data_type")
        return ids.Property(
            propertySet=property_set,
            baseName=facet_blueprint["baseName"],
            dataType=data_type,
            cardinality="required",
        )

    Logger.warning(f"Неподдерживаемый тип facet-а: {facet_type}", name=MODULE_NAME)
    return None


def _resolve_ifc_data_type(value_type: str, source_name: str, source_filename: str) -> str | None:
    """
    Взять тип данных IFC прямо из таблицы и проверить его корректность.

    :param value_type: Тип данных из таблицы.
    :param source_name: Имя свойства из таблицы.
    :param source_filename: Имя исходного файла таблицы.
    :returns: Имя типа данных для IDS или `None`.
    """
    normalized_type = _normalize_text(value_type).upper()
    if not normalized_type:
        return None
    if normalized_type in _get_supported_ifc_data_types():
        return normalized_type
    Logger.error(
        f"Некорректный IFC data type '{value_type}' для свойства '{source_name}' в файле '{source_filename}'. "
        "Поле будет записано без dataType.",
        name=MODULE_NAME,
    )
    return None


def _get_supported_ifc_data_types() -> set[str]:
    """
    Получить набор поддерживаемых IFC data type из доступных схем.

    :returns: Множество имен IFC data type в верхнем регистре.
    """
    global _SUPPORTED_IFC_DATA_TYPES
    if _SUPPORTED_IFC_DATA_TYPES:
        return _SUPPORTED_IFC_DATA_TYPES

    results: set[str] = set()
    for schema_name in _DEFAULT_IFC_VERSIONS:
        schema = ifcopenshell.schema_by_name(schema_name)
        for declaration in schema.declarations():
            try:
                declaration_name = declaration.name()
            except Exception:
                continue
            if declaration_name.upper().startswith("IFC"):
                results.add(declaration_name.upper())
    _SUPPORTED_IFC_DATA_TYPES = results
    return _SUPPORTED_IFC_DATA_TYPES
