from __future__ import annotations

from pathlib import Path
from typing import Any

from flowweaver.nodes.builtin_sql_schema import normalize_data_type
from flowweaver.protocols.table_ref import FieldSchemaModel


def required_path_config(config: dict[str, Any], key: str) -> Path:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    path = Path(value)
    if not path.exists():
        raise ValueError(f"config.{key} does not exist")
    return path


def optional_str_config(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    return value


def optional_int_config(config: dict[str, Any], key: str) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"config.{key} must be an integer")
    if value < 1:
        raise ValueError(f"config.{key} must be positive")
    return value


def optional_schema_config(
    config: dict[str, Any],
    key: str,
) -> list[FieldSchemaModel] | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ValueError(f"config.{key} must be a non-empty list")
    schema: list[FieldSchemaModel] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"config.{key}[{index}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"config.{key}[{index}].name must be a non-empty string")
        data_type = item.get("data_type", "TEXT")
        if not isinstance(data_type, str) or not data_type:
            raise ValueError(
                f"config.{key}[{index}].data_type must be a non-empty string"
            )
        nullable = item.get("nullable", True)
        if not isinstance(nullable, bool):
            raise ValueError(f"config.{key}[{index}].nullable must be a boolean")
        field_id = item.get("field_id", name)
        if not isinstance(field_id, str) or not field_id:
            raise ValueError(f"config.{key}[{index}].field_id must be a string")
        schema.append(
            FieldSchemaModel(
                field_id=field_id,
                name=name,
                data_type=normalize_data_type(data_type),
                nullable=nullable,
                ordinal=index,
            )
        )
    return schema
