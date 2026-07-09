from __future__ import annotations

from pathlib import Path
from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

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
