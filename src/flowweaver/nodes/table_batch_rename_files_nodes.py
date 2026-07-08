from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowweaver.nodes.builtin_table_node_types import BATCH_RENAME_FILES_NODE_TYPE
from flowweaver.nodes.table_node_common import (
    bool_status as _bool_status,
)
from flowweaver.nodes.table_node_common import (
    require_fields as _require_fields,
)
from flowweaver.nodes.table_node_common import (
    simple_schema as _simple_schema,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class BatchRenameFilesNodeHandler:
    node_type = BATCH_RENAME_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        path_field = _node_string_config(
            task.config,
            "path_field",
            node_type=self.node_type,
        )
        new_name_field = _node_string_config(
            task.config,
            "new_name_field",
            node_type=self.node_type,
        )
        _require_fields(input_ref.schema, [path_field, new_name_field])
        name_value_type = _enum_config(
            task.config,
            "name_value_type",
            default="file_name",
            allowed={"file_name", "full_path"},
            node_type=self.node_type,
        )
        new_path_field = _optional_node_string_config(
            task.config,
            "new_path_field",
            default="new_path",
            node_type=self.node_type,
        )
        status_field = _optional_node_string_config(
            task.config,
            "status_field",
            default="rename_status",
            node_type=self.node_type,
        )
        if new_path_field == status_field:
            raise _NodeValidationError(
                "BatchRenameFilesNode new_path_field and status_field must differ"
            )
        auto_append_ext = _bool_config(task.config, "auto_append_ext", default=True)
        allow_dirs = _bool_config(task.config, "allow_dirs", default=False)
        create_target_dirs = _bool_config(
            task.config,
            "create_target_dirs",
            default=False,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "skip", "overwrite", "append_number"},
            node_type=self.node_type,
        )
        actual_rename = _bool_config(task.config, "actual_rename", default=False)
        write_log = _bool_config(task.config, "write_log", default=False)
        log_path = _optional_string_config(
            task.config,
            "log_path",
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    output_rows.append(
                        _batch_rename_plan_row(
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

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_batch_rename_status_schema(
                    new_path_field=new_path_field,
                    status_field=status_field,
                ),
                row_batches=output_batches(),
            )
        ]


def _batch_rename_plan_row(
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


def _batch_rename_target_path(
    source_path: Path,
    new_name: str,
    *,
    name_value_type: str,
    auto_append_ext: bool,
) -> Path:
    if name_value_type == "full_path":
        target_path = Path(new_name).expanduser()
    else:
        target_path = source_path.with_name(new_name)
    if auto_append_ext and source_path.suffix and not target_path.suffix:
        target_path = target_path.with_suffix(source_path.suffix)
    return target_path


def _batch_rename_append_number_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    index = 2
    while True:
        candidate = target_path.with_name(
            f"{target_path.stem}_{index}{target_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        index += 1


def _batch_rename_execute(
    *,
    source_path: Path,
    target_path: Path,
    create_target_dirs: bool,
    conflict_mode: str,
) -> tuple[str, str, str, bool]:
    try:
        if create_target_dirs:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            if conflict_mode == "skip":
                return (
                    "skipped",
                    "",
                    "target path already exists",
                    False,
                )
            if conflict_mode == "error":
                return (
                    "failed",
                    "target path already exists",
                    "",
                    False,
                )
            if conflict_mode == "append_number":
                target_path = _batch_rename_append_number_path(target_path)
        source_path.replace(target_path)
        return ("renamed", "", "", True)
    except OSError as exc:
        return ("failed", str(exc), "", False)


def _batch_rename_write_log_if_requested(
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


def _batch_rename_status_row(
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


def _batch_rename_status_schema(
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


