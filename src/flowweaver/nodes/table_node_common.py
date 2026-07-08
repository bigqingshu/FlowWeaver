from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.table_ref import FieldSchemaModel


def simple_schema(fields: list[tuple[str, str, bool]]) -> list[FieldSchemaModel]:
    return [
        FieldSchemaModel(
            field_id=name,
            name=name,
            data_type=data_type,
            nullable=nullable,
            ordinal=index,
        )
        for index, (name, data_type, nullable) in enumerate(fields)
    ]


def bool_status(value: bool) -> str:
    return "true" if value else "false"


def is_empty_cell(value: Any) -> bool:
    return value is None or value == ""


def row_matches(cell_value: Any, *, operator: str, value: Any) -> bool:
    if operator == "EQ":
        return cell_value == value
    if operator == "NE":
        return cell_value != value
    if operator == "GT":
        return cell_value > value
    if operator == "GE":
        return cell_value >= value
    if operator == "LT":
        return cell_value < value
    if operator == "LE":
        return cell_value <= value
    if operator == "CONTAINS":
        return str(value) in str(cell_value)
    if operator == "IS_NULL":
        return cell_value is None
    return False


def require_fields(
    schema: list[FieldSchemaModel],
    field_names: list[str],
) -> None:
    missing_fields = [
        field_name
        for field_name in field_names
        if find_field(schema, field_name) is None
    ]
    if missing_fields:
        raise BuiltinTableNodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
