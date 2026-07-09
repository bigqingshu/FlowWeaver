from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
)
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
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    output_mode: str,
) -> str:
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="current_datetime" if output_mode == "new_field" else "",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def datetime_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=False,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=False,
    )


def datetime_formatted_value(
    value,
    *,
    config: dict[str, Any],
    format_mode: str,
) -> str:
    if format_mode == "iso":
        return value.isoformat()
    if format_mode == "strftime":
        template = _optional_node_string_config(
            config,
            "strftime_template",
            default="%Y-%m-%d %H:%M:%S",
            node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "template",
        default="{datetime}",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    replacements = {
        "iso": value.isoformat(),
        "date": value.date().isoformat(),
        "time": value.strftime("%H:%M:%S"),
        "datetime": value.strftime("%Y-%m-%d %H:%M:%S"),
        "year": f"{value.year:04d}",
        "month": f"{value.month:02d}",
        "day": f"{value.day:02d}",
        "hour": f"{value.hour:02d}",
        "minute": f"{value.minute:02d}",
        "second": f"{value.second:02d}",
    }
    try:
        return template.format(**replacements)
    except (KeyError, ValueError) as exc:
        raise _NodeValidationError(str(exc)) from exc
