from __future__ import annotations

import fnmatch
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.protocols.table_ref import FieldSchemaModel

_NodeValidationError = BuiltinTableNodeValidationError


def list_files_directory_config(config: dict[str, Any]) -> Path:
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


def list_files_extensions_config(config: dict[str, Any]) -> set[str] | None:
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


def list_file_rows(
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


def list_files_schema() -> list[FieldSchemaModel]:
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
