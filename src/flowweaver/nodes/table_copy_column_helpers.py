from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.table_ref import TableRefModel

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


def copy_column_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    source_field: str,
    target_field: str,
    trim_value: bool,
    empty_default: Any,
) -> Iterator[list[dict[str, Any]]]:
    for rows in context.iter_row_batches(input_ref):
        yield [
            row
            | {
                target_field: copy_column_value(
                    row.get(source_field),
                    trim_value=trim_value,
                    empty_default=empty_default,
                )
            }
            for row in rows
        ]
