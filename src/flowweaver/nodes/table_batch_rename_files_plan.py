from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from flowweaver.nodes.table_batch_rename_files_paths import (
    batch_rename_append_number_path as _batch_rename_append_number_path,
)
from flowweaver.nodes.table_batch_rename_files_paths import (
    batch_rename_execute as _batch_rename_execute,
)
from flowweaver.nodes.table_batch_rename_files_paths import (
    batch_rename_target_path as _batch_rename_target_path,
)
from flowweaver.nodes.table_batch_rename_files_status import (
    batch_rename_status_row as _batch_rename_status_row,
)
from flowweaver.nodes.table_batch_rename_files_status import (
    batch_rename_write_log_if_requested as _batch_rename_write_log_if_requested,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.table_ref import TableRefModel


def batch_rename_plan_row(
    row: dict[str, Any],
    *,
    row_number: int,
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
) -> dict[str, Any]:
    original_value = row.get(path_field)
    new_name_value = row.get(new_name_field)
    if not isinstance(original_value, str) or not original_value.strip():
        return _batch_rename_status_row(
            row_number=row_number,
            original_path="" if original_value is None else str(original_value),
            new_path="",
            new_path_field=new_path_field,
            status_field=status_field,
            status="failed",
            error_message="source path is required",
            actual_rename=actual_rename,
            write_log=write_log,
            log_path=log_path,
        )
    if not isinstance(new_name_value, str) or not new_name_value.strip():
        return _batch_rename_status_row(
            row_number=row_number,
            original_path=original_value,
            new_path="",
            new_path_field=new_path_field,
            status_field=status_field,
            status="failed",
            error_message="new name is required",
            actual_rename=actual_rename,
            write_log=write_log,
            log_path=log_path,
        )
    if write_log and not log_path.strip():
        return _batch_rename_status_row(
            row_number=row_number,
            original_path=original_value,
            new_path="",
            new_path_field=new_path_field,
            status_field=status_field,
            status="failed",
            error_message="log_path is required when write_log is true",
            actual_rename=actual_rename,
            write_log=write_log,
            log_path=log_path,
        )
    source_path = Path(original_value).expanduser()
    target_path = _batch_rename_target_path(
        source_path,
        new_name_value.strip(),
        name_value_type=name_value_type,
        auto_append_ext=auto_append_ext,
    )
    status = "planned"
    error_message = ""
    skipped_reason = ""
    actual_rename_done = False
    try:
        source_exists = source_path.exists()
        source_is_dir = source_path.is_dir() if source_exists else False
        target_exists = target_path.exists()
    except OSError as exc:
        source_exists = False
        source_is_dir = False
        target_exists = False
        status = "failed"
        error_message = str(exc)
    if status != "failed" and not source_exists:
        status = "failed"
        error_message = "source path does not exist"
    elif status != "failed" and source_is_dir and not allow_dirs:
        status = "failed"
        error_message = "directories are not allowed"
    elif status != "failed" and source_path == target_path:
        status = "skipped"
        skipped_reason = "source and target path are identical"
    elif status != "failed" and not target_path.parent.exists():
        if create_target_dirs:
            status = "planned"
        else:
            status = "failed"
            error_message = "target directory does not exist"
    elif status != "failed" and target_exists:
        if conflict_mode == "append_number":
            target_path = _batch_rename_append_number_path(target_path)
        elif conflict_mode == "error":
            status = "failed"
            error_message = "target path already exists"
        elif conflict_mode == "skip":
            status = "skipped"
            skipped_reason = "target path already exists"
    if status == "planned" and actual_rename:
        status, error_message, skipped_reason, actual_rename_done = (
            _batch_rename_execute(
                source_path=source_path,
                target_path=target_path,
                create_target_dirs=create_target_dirs,
                conflict_mode=conflict_mode,
            )
        )
    status_row = _batch_rename_status_row(
        row_number=row_number,
        original_path=str(source_path),
        new_path=str(target_path),
        new_path_field=new_path_field,
        status_field=status_field,
        status=status,
        error_message=error_message,
        skipped_reason=skipped_reason,
        actual_rename=actual_rename,
        actual_rename_done=actual_rename_done,
        write_log=write_log,
        log_path=log_path,
    )
    _batch_rename_write_log_if_requested(status_row, write_log=write_log)
    return status_row


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
