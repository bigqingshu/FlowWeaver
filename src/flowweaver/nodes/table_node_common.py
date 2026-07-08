from __future__ import annotations

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
