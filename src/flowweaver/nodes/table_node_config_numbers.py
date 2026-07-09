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
