from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_SELECTED_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_field_mappings_config as _write_selected_field_mappings_config,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_target_fields as _write_selected_target_fields,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_target_table_config as _write_selected_target_table_config,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


@dataclass(frozen=True)
class WriteSelectedColumnsNodeConfig:
    source_type: str
    selected_fields: list[str]
    target_type: str
    target_table: str
    write_mode: str
    field_name_mode: str
    overwrite_rule: str
    field_mappings: dict[str, str]
    target_fields: list[str]
    enable_write: bool
    backup_before_write: bool


def write_selected_columns_node_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    node_type: str = WRITE_SELECTED_COLUMNS_NODE_TYPE,
) -> WriteSelectedColumnsNodeConfig:
    source_type = _enum_config(
        config,
        "source_type",
        default="current_table",
        allowed={"current_table", "run_table", "sqlite"},
        node_type=node_type,
    )
    selected_fields = _string_list_config(
        config,
        "selected_fields",
        node_type=node_type,
    )
    missing_fields = [
        field
        for field in selected_fields
        if find_field(input_ref.schema, field) is None
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    target_type = _enum_config(
        config,
        "target_type",
        default="run_table",
        allowed={"run_table", "memory_table", "sqlite"},
        node_type=node_type,
    )
    target_table = _write_selected_target_table_config(
        config,
        target_type=target_type,
    )
    write_mode = _enum_config(
        config,
        "write_mode",
        default="overwrite",
        allowed={"create", "overwrite", "append", "upsert"},
        node_type=node_type,
    )
    field_name_mode = _enum_config(
        config,
        "field_name_mode",
        default="keep",
        allowed={"keep", "prefix", "suffix", "mapping"},
        node_type=node_type,
    )
    overwrite_rule = _enum_config(
        config,
        "overwrite_rule",
        default="all",
        allowed={"all", "empty_only", "skip_existing"},
        node_type=node_type,
    )
    field_mappings = _write_selected_field_mappings_config(
        config,
        selected_fields=selected_fields,
    )
    target_fields = _write_selected_target_fields(
        config,
        selected_fields=selected_fields,
        field_name_mode=field_name_mode,
        field_mappings=field_mappings,
    )
    enable_write = _bool_config(config, "enable_write", default=False)
    backup_before_write = _bool_config(
        config,
        "backup_before_write",
        default=False,
    )
    return WriteSelectedColumnsNodeConfig(
        source_type=source_type,
        selected_fields=selected_fields,
        target_type=target_type,
        target_table=target_table,
        write_mode=write_mode,
        field_name_mode=field_name_mode,
        overwrite_rule=overwrite_rule,
        field_mappings=field_mappings,
        target_fields=target_fields,
        enable_write=enable_write,
        backup_before_write=backup_before_write,
    )
