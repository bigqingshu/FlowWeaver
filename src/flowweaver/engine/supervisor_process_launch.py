from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def launch_child_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    stdin: Any,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen:
    stdout_file = stdout_path.open("ab")
    stderr_file = stderr_path.open("ab")
    try:
        return subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=stdin,
            stdout=stdout_file,
            stderr=stderr_file,
        )
    finally:
        stdout_file.close()
        stderr_file.close()
