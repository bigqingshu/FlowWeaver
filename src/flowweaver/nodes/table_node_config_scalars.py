from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError


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
