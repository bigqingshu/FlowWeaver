from __future__ import annotations

import fnmatch
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    BATCH_RENAME_FILES_NODE_TYPE,
    LIST_FILES_NODE_TYPE,
)
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
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ListFilesNodeHandler:
    node_type = LIST_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("ListFilesNode does not accept inputs")
        directory = _list_files_directory_config(task.config)
        recursive = _bool_config(task.config, "recursive", default=False)
        include_files = _bool_config(task.config, "include_files", default=True)
        include_dirs = _bool_config(task.config, "include_dirs", default=False)
        if not include_files and not include_dirs:
            raise _NodeValidationError(
                "ListFilesNode must include files or directories"
            )
        include_hidden = _bool_config(
            task.config,
            "include_hidden",
            default=False,
        )
        extensions = _list_files_extensions_config(task.config)
        name_contains = _optional_string_config(
            task.config,
            "name_contains",
            node_type=self.node_type,
        )
        glob_pattern = _optional_string_config(
            task.config,
            "glob_pattern",
            default="*",
            node_type=self.node_type,
        )
        if not glob_pattern.strip():
            raise _NodeValidationError("ListFilesNode config.glob_pattern is required")
        max_files = _positive_int_config(
            task.config,
            "max_files",
            default=10_000,
            node_type=self.node_type,
        )
        rows = _list_file_rows(
            directory,
            recursive=recursive,
            include_files=include_files,
            include_dirs=include_dirs,
            include_hidden=include_hidden,
            extensions=extensions,
            name_contains=name_contains,
            glob_pattern=glob_pattern,
            max_files=max_files,
        )
        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=_list_files_schema(),
            row_batches=(rows,),
        )


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


def _list_files_directory_config(config: dict[str, Any]) -> Path:
    directory_value = config.get("directory")
    if not isinstance(directory_value, str) or not directory_value.strip():
        raise _NodeValidationError("ListFilesNode config.directory is required")
    directory = Path(directory_value).expanduser()
    try:
        directory = directory.resolve()
    except OSError as exc:
        raise _NodeValidationError(str(exc)) from exc
    if not directory.exists():
        raise _NodeValidationError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise _NodeValidationError(f"Path is not a directory: {directory}")
    return directory


def _list_files_extensions_config(config: dict[str, Any]) -> set[str] | None:
    value = config.get("extensions")
    if value in (None, ""):
        return None
    if not isinstance(value, list):
        raise _NodeValidationError("ListFilesNode config.extensions must be a list")
    extensions: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _NodeValidationError(
                "ListFilesNode config.extensions must contain strings"
            )
        extension = item.strip().lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        extensions.add(extension)
    return extensions or None


def _list_file_rows(
    directory: Path,
    *,
    recursive: bool,
    include_files: bool,
    include_dirs: bool,
    include_hidden: bool,
    extensions: set[str] | None,
    name_contains: str,
    glob_pattern: str,
    max_files: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pending_dirs = [directory]
    while pending_dirs and len(rows) < max_files:
        current_dir = pending_dirs.pop()
        try:
            entries = sorted(
                current_dir.iterdir(),
                key=lambda path: path.name.lower(),
            )
        except OSError as exc:
            raise _NodeValidationError(str(exc)) from exc
        for entry in entries:
            if len(rows) >= max_files:
                break
            if not include_hidden and _is_hidden_entry(entry, directory):
                continue
            try:
                is_dir = entry.is_dir()
                is_file = entry.is_file()
            except OSError:
                continue
            if recursive and is_dir and not entry.is_symlink():
                pending_dirs.append(entry)
            if not _list_files_entry_matches(
                entry,
                is_dir=is_dir,
                is_file=is_file,
                include_files=include_files,
                include_dirs=include_dirs,
                extensions=extensions,
                name_contains=name_contains,
                glob_pattern=glob_pattern,
            ):
                continue
            rows.append(
                _list_file_row(
                    entry,
                    directory,
                    is_dir=is_dir,
                    is_file=is_file,
                )
            )
    return rows


def _list_files_entry_matches(
    entry: Path,
    *,
    is_dir: bool,
    is_file: bool,
    include_files: bool,
    include_dirs: bool,
    extensions: set[str] | None,
    name_contains: str,
    glob_pattern: str,
) -> bool:
    if is_file and not include_files:
        return False
    if is_dir and not include_dirs:
        return False
    if not is_file and not is_dir:
        return False
    if is_file and extensions is not None and entry.suffix.lower() not in extensions:
        return False
    if name_contains and name_contains not in entry.name:
        return False
    return fnmatch.fnmatch(entry.name, glob_pattern)


def _is_hidden_entry(entry: Path, root: Path) -> bool:
    try:
        relative_parts = entry.relative_to(root).parts
    except ValueError:
        relative_parts = entry.parts
    return any(part.startswith(".") for part in relative_parts)


def _list_file_row(
    entry: Path,
    root: Path,
    *,
    is_dir: bool,
    is_file: bool,
) -> dict[str, Any]:
    try:
        stat_result = entry.stat()
    except OSError:
        stat_result = None
    relative_path = entry.relative_to(root).as_posix()
    return {
        "name": entry.name,
        "path": str(entry),
        "parent_path": str(entry.parent),
        "relative_path": relative_path,
        "extension": "" if is_dir else entry.suffix.lower(),
        "stem": entry.stem,
        "is_dir": _bool_status(is_dir),
        "is_file": _bool_status(is_file),
        "is_symlink": _bool_status(entry.is_symlink()),
        "size_bytes": (
            stat_result.st_size
            if stat_result is not None and is_file
            else None
        ),
        "modified_at": (
            datetime.fromtimestamp(
                stat_result.st_mtime,
                tz=UTC,
            ).isoformat()
            if stat_result is not None
            else None
        ),
    }


def _list_files_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("name", "TEXT", False),
            ("path", "TEXT", False),
            ("parent_path", "TEXT", False),
            ("relative_path", "TEXT", False),
            ("extension", "TEXT", False),
            ("stem", "TEXT", False),
            ("is_dir", "TEXT", False),
            ("is_file", "TEXT", False),
            ("is_symlink", "TEXT", False),
            ("size_bytes", "INTEGER", True),
            ("modified_at", "TEXT", True),
        ]
    )


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


