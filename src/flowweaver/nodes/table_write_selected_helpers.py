from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_SELECTED_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_write_selected_runtime import (
    write_selected_runtime_target as write_selected_runtime_target,
)
from flowweaver.protocols.table_ref import FieldSchemaModel

_NodeValidationError = BuiltinTableNodeValidationError


def write_selected_target_table_config(
    config: dict[str, Any],
    *,
    target_type: str,
) -> str:
    if target_type in {"run_table", "memory_table"}:
        return _named_output_config(
            config,
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            keys=("target_transit_table", "target_table"),
        )
    return _named_output_config(
        config,
        node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        keys=("target_table",),
    )


def write_selected_field_mappings_config(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
) -> dict[str, str]:
    value = config.get("field_mappings", [])
    if value is None:
        return {}
    if not isinstance(value, list):
        raise _NodeValidationError(
            "WriteSelectedColumnsNode config.field_mappings must be a list"
        )
    selected = set(selected_fields)
    mappings: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteSelectedColumnsNode config.field_mappings must contain objects"
            )
        source_value = item.get("source_field", item.get("source"))
        target_value = item.get("target_field", item.get("target"))
        if not isinstance(source_value, str) or not source_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.source_field is required"
            )
        if not isinstance(target_value, str) or not target_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.target_field is required"
            )
        source_field = source_value.strip()
        target_field = target_value.strip()
        if source_field not in selected:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode mapping source is not selected: "
                f"{source_field}"
            )
        if source_field in mappings:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode duplicate mapping source: {source_field}"
            )
        mappings[source_field] = target_field
    return mappings


def write_selected_target_fields(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
    field_name_mode: str,
    field_mappings: dict[str, str],
) -> list[str]:
    if field_name_mode == "mapping":
        missing_mappings = [
            field
            for field in selected_fields
            if field not in field_mappings
        ]
        if missing_mappings:
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings missing selected fields: "
                f"{', '.join(missing_mappings)}"
            )
        target_fields = [field_mappings[field] for field in selected_fields]
    elif field_name_mode == "prefix":
        prefix = _optional_string_config(
            config,
            "field_prefix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{prefix}{field}" for field in selected_fields]
    elif field_name_mode == "suffix":
        suffix = _optional_string_config(
            config,
            "field_suffix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{field}{suffix}" for field in selected_fields]
    else:
        target_fields = list(selected_fields)
    duplicates = sorted(
        field
        for field in set(target_fields)
        if target_fields.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"WriteSelectedColumnsNode target fields are duplicated: "
            f"{', '.join(duplicates)}"
        )
    return target_fields


def write_selected_columns_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("source_type", "TEXT", False),
            ("target_type", "TEXT", False),
            ("target_table", "TEXT", False),
            ("write_mode", "TEXT", False),
            ("overwrite_rule", "TEXT", False),
            ("selected_field_count", "INTEGER", False),
            ("mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("actual_write", "TEXT", False),
            ("affected_rows", "INTEGER", False),
            ("skipped_rows", "INTEGER", False),
            ("warning_count", "INTEGER", False),
            ("warnings", "TEXT", False),
            ("target_table_ref_id", "TEXT", False),
            ("selected_fields", "TEXT", False),
            ("target_fields", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )
