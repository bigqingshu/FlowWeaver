from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError


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
