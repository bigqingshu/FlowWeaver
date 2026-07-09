from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.protocols.table_ref import FieldSchemaModel

_NodeValidationError = BuiltinTableNodeValidationError


def write_selected_target_schema(
    input_schema: list[FieldSchemaModel],
    *,
    selected_fields: list[str],
    target_fields: list[str],
) -> list[FieldSchemaModel]:
    fields_by_name = {field.name: field for field in input_schema}
    return [
        FieldSchemaModel(
            field_id=target_field,
            name=target_field,
            data_type=fields_by_name[source_field].data_type,
            nullable=fields_by_name[source_field].nullable,
            ordinal=index,
        )
        for index, (source_field, target_field) in enumerate(
            zip(selected_fields, target_fields, strict=True)
        )
    ]


def write_selected_project_rows(
    source_rows: list[dict[str, Any]],
    *,
    selected_fields: list[str],
    target_fields: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            target_field: row.get(source_field)
            for source_field, target_field in zip(
                selected_fields,
                target_fields,
                strict=True,
            )
        }
        for row in source_rows
    ]


def validate_write_selected_append_schema(
    existing_schema: list[FieldSchemaModel],
    target_schema: list[FieldSchemaModel],
) -> None:
    existing = [
        (field.name, field.data_type.upper())
        for field in sorted(existing_schema, key=lambda item: item.ordinal)
    ]
    target = [
        (field.name, field.data_type.upper())
        for field in sorted(target_schema, key=lambda item: item.ordinal)
    ]
    if existing != target:
        raise _NodeValidationError(
            "WriteSelectedColumnsNode append target schema does not match"
        )
