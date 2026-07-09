from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import DEDUPLICATE_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import has_field
from flowweaver.nodes.table_row_deduplicate_markers import (
    deduplicate_marker_fields as deduplicate_marker_fields,
)
from flowweaver.nodes.table_row_deduplicate_markers import (
    deduplicate_marker_values as deduplicate_marker_values,
)
from flowweaver.nodes.table_row_deduplicate_markers import (
    deduplicate_output_schema as deduplicate_output_schema,
)
from flowweaver.nodes.table_row_deduplicate_runtime import (
    deduplicate_groups as deduplicate_groups,
)
from flowweaver.nodes.table_row_deduplicate_runtime import (
    deduplicate_key as deduplicate_key,
)
from flowweaver.nodes.table_row_deduplicate_runtime import (
    deduplicate_occurrence_index as deduplicate_occurrence_index,
)
from flowweaver.nodes.table_row_deduplicate_runtime import (
    deduplicate_output_batches as deduplicate_output_batches,
)
from flowweaver.nodes.table_row_deduplicate_runtime import (
    deduplicate_should_keep as deduplicate_should_keep,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def deduplicate_key_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    dedupe_mode = _enum_config(
        config,
        "dedupe_mode",
        default="key_fields",
        allowed={"key_fields", "entire_row"},
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    if dedupe_mode == "entire_row":
        return [field.name for field in input_ref.schema]
    key_fields = _string_list_config(
        config,
        "key_fields",
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in key_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return key_fields
