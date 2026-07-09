from __future__ import annotations

from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.protocols.table_ref import FieldSchemaModel


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
