from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_ops import replace_field_schema
from flowweaver.protocols.table_ref import FieldSchemaModel


def fill_sequence_output_schema(
    schema: list[FieldSchemaModel],
    *,
    target_field: str,
    formatted: bool,
) -> list[FieldSchemaModel]:
    if not formatted:
        return schema
    return replace_field_schema(
        schema,
        target_field,
        data_type="TEXT",
        nullable=True,
    )


def format_sequence_value(
    value: float,
    *,
    zero_pad: int,
    prefix: str,
    suffix: str,
) -> Any:
    normalized = _normalize_sequence_number(value)
    if not prefix and not suffix and zero_pad <= 0:
        return normalized
    text = str(normalized)
    if zero_pad > 0:
        text = text.zfill(zero_pad)
    return f"{prefix}{text}{suffix}"


def _normalize_sequence_number(value: float) -> int | float:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
