from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import EXTRACT_TEXT_NODE_TYPE
from flowweaver.nodes.table_extract_text_values import SKIP_ROW as SKIP_ROW
from flowweaver.nodes.table_extract_text_values import (
    extract_text_rule_fallback_key as extract_text_rule_fallback_key,
)
from flowweaver.nodes.table_extract_text_values import (
    extract_text_unmatched_value as extract_text_unmatched_value,
)
from flowweaver.nodes.table_extract_text_values import (
    extract_text_value as extract_text_value,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
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


def extract_text_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _node_string_config(
        config,
        key,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def extract_text_output_schema(
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
            nullable=True,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=True,
    )
