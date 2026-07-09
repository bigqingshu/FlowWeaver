from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def writeback_status_row(
    *,
    status: str,
    direction: str,
    source_table: str,
    target_type: str,
    target_table: str,
    write_mode: str,
    use_match_rules: bool,
    match_rule_count: int,
    field_mapping_count: int,
    source_row_count: int,
    enable_write: bool,
    backup_before_write: bool,
    output_preview_table: bool,
    actual_write: bool,
    affected_rows: int,
    skipped_rows: int,
    warnings: list[str],
    target_ref: TableRefModel | None,
    overwrite_policy: str,
    source_empty_policy: str,
    no_match_policy: str,
    multi_match_policy: str,
    duplicate_target_policy: str,
    match_fields: str,
    mapped_fields: str,
    skipped_reason: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "writeback_direction": direction,
        "source_table": source_table,
        "target_type": target_type,
        "target_table": target_table,
        "write_mode": write_mode,
        "use_match_rules": _bool_status(use_match_rules),
        "match_rule_count": match_rule_count,
        "field_mapping_count": field_mapping_count,
        "source_row_count": source_row_count,
        "enable_write": _bool_status(enable_write),
        "backup_before_write": _bool_status(backup_before_write),
        "output_preview_table": _bool_status(output_preview_table),
        "actual_write": _bool_status(actual_write),
        "affected_rows": affected_rows,
        "skipped_rows": skipped_rows,
        "warning_count": len(warnings),
        "warnings": "; ".join(warnings),
        "target_table_ref_id": target_ref.table_ref_id if target_ref else "",
        "overwrite_policy": overwrite_policy,
        "source_empty_policy": source_empty_policy,
        "no_match_policy": no_match_policy,
        "multi_match_policy": multi_match_policy,
        "duplicate_target_policy": duplicate_target_policy,
        "match_fields": match_fields,
        "mapped_fields": mapped_fields,
        "skipped_reason": skipped_reason,
    }


def writeback_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("writeback_direction", "TEXT", False),
            ("source_table", "TEXT", False),
            ("target_type", "TEXT", False),
            ("target_table", "TEXT", False),
            ("write_mode", "TEXT", False),
            ("use_match_rules", "TEXT", False),
            ("match_rule_count", "INTEGER", False),
            ("field_mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("output_preview_table", "TEXT", False),
            ("actual_write", "TEXT", False),
            ("affected_rows", "INTEGER", False),
            ("skipped_rows", "INTEGER", False),
            ("warning_count", "INTEGER", False),
            ("warnings", "TEXT", False),
            ("target_table_ref_id", "TEXT", False),
            ("overwrite_policy", "TEXT", False),
            ("source_empty_policy", "TEXT", False),
            ("no_match_policy", "TEXT", False),
            ("multi_match_policy", "TEXT", False),
            ("duplicate_target_policy", "TEXT", False),
            ("match_fields", "TEXT", False),
            ("mapped_fields", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )
