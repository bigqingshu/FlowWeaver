from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_batch_rename_files_plan import (
    batch_rename_plan_row as batch_rename_plan_row,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.table_ref import TableRefModel


def batch_rename_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    path_field: str,
    new_name_field: str,
    name_value_type: str,
    new_path_field: str,
    status_field: str,
    auto_append_ext: bool,
    allow_dirs: bool,
    create_target_dirs: bool,
    conflict_mode: str,
    actual_rename: bool,
    write_log: bool,
    log_path: str,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            output_rows.append(
                batch_rename_plan_row(
                    row,
                    row_number=row_number,
                    path_field=path_field,
                    new_name_field=new_name_field,
                    name_value_type=name_value_type,
                    new_path_field=new_path_field,
                    status_field=status_field,
                    auto_append_ext=auto_append_ext,
                    allow_dirs=allow_dirs,
                    create_target_dirs=create_target_dirs,
                    conflict_mode=conflict_mode,
                    actual_rename=actual_rename,
                    write_log=write_log,
                    log_path=log_path,
                )
            )
            row_number += 1
        yield output_rows
