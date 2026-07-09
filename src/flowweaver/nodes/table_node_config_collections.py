from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError


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
