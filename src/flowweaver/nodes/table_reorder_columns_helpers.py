from __future__ import annotations

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import has_field, reorder_fields
from flowweaver.protocols.table_ref import FieldSchemaModel

_NodeValidationError = BuiltinTableNodeValidationError


def reorder_columns_output_plan(
    schema: list[FieldSchemaModel],
    *,
    order: list[str],
    missing_policy: str,
    unlisted_policy: str,
) -> tuple[list[FieldSchemaModel], list[str]]:
    missing_columns = [
        column
        for column in order
        if not has_field(schema, column)
    ]
    if missing_columns and missing_policy == "error":
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_columns)}"
        )
    existing_order = [
        column
        for column in order
        if has_field(schema, column)
    ]
    input_field_names = [field.name for field in schema]
    unlisted_columns = [
        column
        for column in input_field_names
        if column not in existing_order
    ]
    if unlisted_columns and unlisted_policy == "error":
        raise _NodeValidationError(
            f"Fields are not listed: {', '.join(unlisted_columns)}"
        )
    output_schema = reorder_fields(
        schema,
        existing_order,
        include_unlisted=unlisted_policy == "append",
    )
    if not output_schema:
        raise _NodeValidationError("ReorderColumnsNode output schema is empty")
    return output_schema, [field.name for field in output_schema]
