from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.protocols.table_ref import FieldSchemaModel

_NodeValidationError = BuiltinTableNodeValidationError


def writeback_target_schema(
    input_schema: list[FieldSchemaModel],
    *,
    field_mappings: list[dict[str, str]],
) -> list[FieldSchemaModel]:
    fields_by_name = {field.name: field for field in input_schema}
    return [
        FieldSchemaModel(
            field_id=mapping["target_field"],
            name=mapping["target_field"],
            data_type=fields_by_name[mapping["source_field"]].data_type,
            nullable=True,
            ordinal=index,
        )
        for index, mapping in enumerate(field_mappings)
    ]


def writeback_project_rows(
    source_rows: list[dict[str, Any]],
    *,
    field_mappings: list[dict[str, str]],
    source_empty_policy: str,
) -> tuple[list[dict[str, Any]], int]:
    target_rows: list[dict[str, Any]] = []
    skipped_rows = 0
    for source_row in source_rows:
        target_row: dict[str, Any] = {}
        skip_row = False
        for mapping in field_mappings:
            value = source_row.get(mapping["source_field"])
            if writeback_is_empty_value(value):
                if source_empty_policy == "skip":
                    skip_row = True
                    break
                if source_empty_policy == "clear_target":
                    value = None
            target_row[mapping["target_field"]] = value
        if skip_row:
            skipped_rows += 1
        else:
            target_rows.append(target_row)
    return target_rows, skipped_rows


def writeback_is_empty_value(value: Any) -> bool:
    return value is None or value == ""


def validate_writeback_append_schema(
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
            "WriteBackTableNode append target schema does not match"
        )
