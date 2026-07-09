from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import PARSE_DATETIME_NODE_TYPE
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.nodes.table_parse_datetime_values import (
    format_parsed_datetime as format_parsed_datetime,
)
from flowweaver.nodes.table_parse_datetime_values import (
    parse_datetime_unmatched_value as parse_datetime_unmatched_value,
)
from flowweaver.nodes.table_parse_datetime_values import (
    parse_datetime_value as parse_datetime_value,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def parse_datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="parsed_datetime" if output_mode == "new_field" else "",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def parse_datetime_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
    status_field: str | None,
) -> list[FieldSchemaModel]:
    schema = (
        append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=True,
        )
        if output_mode == "new_field"
        else replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    )
    if status_field is None:
        return schema
    if has_field(schema, status_field):
        raise _NodeValidationError(f"Field already exists: {status_field}")
    return append_field(
        schema,
        name=status_field,
        data_type="TEXT",
        nullable=False,
    )
