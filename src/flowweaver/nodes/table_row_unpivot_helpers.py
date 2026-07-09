from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import UNPIVOT_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_common import require_fields as _require_fields
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_list_config as _optional_string_list_config,
)
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_row_unpivot_output import (
    unpivot_output_rows as unpivot_output_rows,
)
from flowweaver.nodes.table_row_unpivot_output import (
    unpivot_rows_output_schema as unpivot_rows_output_schema,
)
from flowweaver.nodes.table_row_unpivot_selection import (
    unpivot_row_selected as unpivot_row_selected,
)
from flowweaver.nodes.table_row_unpivot_selection import (
    unpivot_row_selector as unpivot_row_selector,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def unpivot_rows_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    value_fields = _string_list_config(
        config,
        "value_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    keep_fields = _optional_string_list_config(
        config,
        "keep_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    _require_fields(input_ref.schema, value_fields + keep_fields)
    output_value_field = _optional_node_string_config(
        config,
        "output_value_field",
        default="value",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    output_source_field = _bool_config(
        config,
        "output_source_field",
        default=True,
    )
    source_field_name = (
        _optional_node_string_config(
            config,
            "source_field_name",
            default="source_field",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_source_field
        else None
    )
    output_original_row = _bool_config(
        config,
        "output_original_row",
        default=False,
    )
    original_row_field = (
        _optional_node_string_config(
            config,
            "original_row_field",
            default="original_row",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_original_row
        else None
    )
    output_status = _bool_config(config, "output_status", default=False)
    status_field = (
        _optional_node_string_config(
            config,
            "status_field",
            default="mapping_status",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_status
        else None
    )
    output_field_names = [
        field
        for field in [
            output_value_field,
            source_field_name,
            original_row_field,
            status_field,
        ]
        if field is not None
    ]
    conflicts = sorted(set(keep_fields) & set(output_field_names))
    if conflicts:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields conflict with keep_fields: "
            f"{', '.join(conflicts)}"
        )
    duplicates = sorted(
        field
        for field in set(output_field_names)
        if output_field_names.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields are duplicated: {', '.join(duplicates)}"
        )
    return {
        "value_fields": value_fields,
        "keep_fields": keep_fields,
        "output_value_field": output_value_field,
        "source_field_name": source_field_name,
        "original_row_field": original_row_field,
        "status_field": status_field,
        "empty_mode": _enum_config(
            config,
            "empty_mode",
            default="skip",
            allowed={"skip", "empty", "fixed"},
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        ),
        "empty_fixed": config.get("empty_fixed"),
        "trim_value": _bool_config(config, "trim_value", default=False),
    }

