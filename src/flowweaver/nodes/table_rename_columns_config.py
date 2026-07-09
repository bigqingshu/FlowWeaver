from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import RENAME_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_rename_columns_mapping import (
    rename_columns_mapping_config as _rename_columns_mapping_config,
)
from flowweaver.nodes.table_rename_columns_scope import (
    rename_columns_scope_fields as _rename_columns_scope_fields,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def rename_columns_proposed_names(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[str]:
    mode = _enum_config(
        config,
        "mode",
        default="mappings",
        allowed={"mappings", "prefix", "suffix", "replace"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    trim_names = _bool_config(config, "trim_names", default=True)
    input_names = [field.name for field in input_ref.schema]
    missing_policy = _enum_config(
        config,
        "missing_policy",
        default="error",
        allowed={"error", "skip", "warn"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    rename_map: dict[str, str] = {}
    if mode == "mappings":
        rename_map = _rename_columns_mapping_config(
            config,
            input_ref=input_ref,
            missing_policy=missing_policy,
            trim_names=trim_names,
        )
    else:
        scope_fields = _rename_columns_scope_fields(
            config,
            input_ref=input_ref,
            missing_policy=missing_policy,
        )
        if mode == "prefix":
            prefix = _optional_string_config(
                config,
                "prefix",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {field: f"{prefix}{field}" for field in scope_fields}
        elif mode == "suffix":
            suffix = _optional_string_config(
                config,
                "suffix",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {field: f"{field}{suffix}" for field in scope_fields}
        else:
            match = _node_string_config(
                config,
                "replace_match",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            replace_value = _optional_string_config(
                config,
                "replace_value",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {
                field: field.replace(match, replace_value)
                for field in scope_fields
            }
    proposed_names: list[str] = []
    for field_name in input_names:
        proposed = rename_map.get(field_name, field_name)
        if trim_names:
            proposed = proposed.strip()
        if not proposed:
            raise _NodeValidationError("RenameColumnsNode output field name is empty")
        proposed_names.append(proposed)
    return proposed_names
