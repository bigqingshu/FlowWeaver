from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

_PLUGIN_ENVIRONMENT_KEYS = (
    "COMSPEC",
    "NUMBER_OF_PROCESSORS",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)


def plugin_process_command(
    entrypoint_path: Path,
    *,
    executor_id: str,
    python_executable: str | None = None,
) -> list[str]:
    suffix = entrypoint_path.suffix.lower()
    if suffix == ".py":
        return [
            python_executable or sys.executable,
            "-E",
            "-s",
            str(entrypoint_path),
            "--executor-id",
            executor_id,
        ]
    if suffix == ".exe":
        return [str(entrypoint_path), "--executor-id", executor_id]
    raise ValueError(f"unsupported plugin entrypoint type: {suffix or '<none>'}")


def plugin_process_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source_env = source if source is not None else os.environ
    environment = {
        key: source_env[key] for key in _PLUGIN_ENVIRONMENT_KEYS if key in source_env
    }
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUNBUFFERED"] = "1"
    return environment
