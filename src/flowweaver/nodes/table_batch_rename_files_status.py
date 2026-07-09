from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.protocols.table_ref import FieldSchemaModel


def batch_rename_write_log_if_requested(
    status_row: dict[str, Any],
    *,
    write_log: bool,
) -> None:
    if not write_log:
        return
    log_path = status_row.get("log_path")
    if not isinstance(log_path, str) or not log_path.strip():
        return
    try:
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(status_row, ensure_ascii=False, sort_keys=True) + "\n"
            )
    except OSError as exc:
        status_row["error_message"] = str(exc)


def batch_rename_status_row(
    *,
    row_number: int,
    original_path: str,
    new_path: str,
    new_path_field: str,
    status_field: str,
    status: str,
    error_message: str,
    actual_rename: bool,
    write_log: bool,
    log_path: str,
    skipped_reason: str = "",
    actual_rename_done: bool = False,
) -> dict[str, Any]:
    return {
        "source_row_number": row_number,
        "original_path": original_path,
        new_path_field: new_path,
        status_field: status,
        "error_message": error_message,
        "rename_requested": _bool_status(actual_rename),
        "actual_rename": _bool_status(actual_rename_done),
        "write_log": _bool_status(write_log),
        "log_path": log_path,
        "skipped_reason": skipped_reason,
    }


def batch_rename_status_schema(
    *,
    new_path_field: str,
    status_field: str,
) -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("source_row_number", "INTEGER", False),
            ("original_path", "TEXT", False),
            (new_path_field, "TEXT", False),
            (status_field, "TEXT", False),
            ("error_message", "TEXT", False),
            ("rename_requested", "TEXT", False),
            ("actual_rename", "TEXT", False),
            ("write_log", "TEXT", False),
            ("log_path", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )
