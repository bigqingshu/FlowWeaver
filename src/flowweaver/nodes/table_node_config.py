from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError


def int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int):
        raise BuiltinTableNodeValidationError(f"config.{key} must be an integer")
    if value < 0:
        raise BuiltinTableNodeValidationError(f"config.{key} must be non-negative")
    return value


def positive_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
    node_type: str,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an integer"
        )
    if value < 1:
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be positive"
        )
    return value


def non_negative_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
    node_type: str,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an integer"
        )
    if value < 0:
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be non-negative"
        )
    return value


def optional_positive_int_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an integer"
        )
    if value < 1:
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be positive"
        )
    return value


def optional_non_negative_int_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an integer"
        )
    if value < 0:
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be non-negative"
        )
    return value


def string_config(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuiltinTableNodeValidationError(
            f"AddColumnsNode config.{key} is required"
        )
    return value.strip()


def node_string_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} is required"
        )
    return value.strip()


def optional_node_string_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str,
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} is required"
        )
    return value.strip()


def bool_config(
    config: dict[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    value = config.get(key, default)
    if not isinstance(value, bool):
        raise BuiltinTableNodeValidationError(f"config.{key} must be a boolean")
    return value


def enum_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str,
    allowed: set[str],
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} is required"
        )
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise BuiltinTableNodeValidationError(
            f"Unsupported {node_type} config.{key}: {value}"
        )
    return normalized


def named_output_config(
    config: dict[str, Any],
    *,
    node_type: str,
    keys: tuple[str, ...],
) -> str:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    joined_keys = " or ".join(f"config.{key}" for key in keys)
    raise BuiltinTableNodeValidationError(f"{node_type} {joined_keys} is required")


def string_list_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> list[str]:
    value = config.get(key)
    if not isinstance(value, list) or not value:
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be a non-empty string list"
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BuiltinTableNodeValidationError(
                f"{node_type} config.{key} must be a non-empty string list"
            )
        normalized = item.strip()
        if normalized in items:
            raise BuiltinTableNodeValidationError(
                f"{node_type} config.{key} contains duplicate field: {normalized}"
            )
        items.append(normalized)
    return items


def optional_string_list_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> list[str]:
    value = config.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be a string list"
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BuiltinTableNodeValidationError(
                f"{node_type} config.{key} must be a string list"
            )
        normalized = item.strip()
        if normalized in items:
            raise BuiltinTableNodeValidationError(
                f"{node_type} config.{key} contains duplicate field: {normalized}"
            )
        items.append(normalized)
    return items


def optional_string_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str = "",
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be a string"
        )
    return value


def object_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> dict[str, Any]:
    value = config.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an object"
        )
    return value


def optional_object_list_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> list[dict[str, Any]]:
    value = config.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise BuiltinTableNodeValidationError(
            f"{node_type} config.{key} must be an object list"
        )
    items: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise BuiltinTableNodeValidationError(
                f"{node_type} config.{key} must be an object list"
            )
        items.append(item)
    return items
