from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import RENAME_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def rename_columns_scope_fields(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    missing_policy: str,
) -> list[str]:
    scope = _enum_config(
        config,
        "scope",
        default="all",
        allowed={"all", "fields"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    if scope == "all":
        return [field.name for field in input_ref.schema]
    scope_fields = _string_list_config(
        config,
        "scope_fields",
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    input_names = {field.name for field in input_ref.schema}
    missing_fields = [
        field
        for field in scope_fields
        if field not in input_names
    ]
    if missing_fields and missing_policy == "error":
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return [
        field
        for field in scope_fields
        if field in input_names
    ]
