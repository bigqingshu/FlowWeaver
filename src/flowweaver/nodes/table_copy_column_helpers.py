from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


def copy_column_output_mode_config(config: dict[str, Any]) -> str:
    value = config.get("output_mode", "new_field")
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("CopyColumnNode config.output_mode is required")
    mode = value.strip().lower()
    if mode not in {"new_field", "overwrite"}:
        raise _NodeValidationError(f"Unsupported CopyColumnNode output_mode: {value}")
    return mode


def copy_column_target_field_config(
    config: dict[str, Any],
    *,
    output_mode: str,
) -> str:
    key = "new_field" if output_mode == "new_field" else "target_field"
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"CopyColumnNode config.{key} is required")
    return value.strip()


def copy_column_value(
    value: Any,
    *,
    trim_value: bool,
    empty_default: Any,
) -> Any:
    copied = value.strip() if trim_value and isinstance(value, str) else value
    if copied is None or copied == "":
        return empty_default
    return copied
