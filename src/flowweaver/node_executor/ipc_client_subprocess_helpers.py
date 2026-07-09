from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from flowweaver.protocols.ipc_messages import IPCEnvelope


def src_path() -> Path:
    return Path(__file__).resolve().parents[2]


def child_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env) if base_env is not None else os.environ.copy()
    path = src_path()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(path)
        if not existing_pythonpath
        else f"{path}{os.pathsep}{existing_pythonpath}"
    )
    return env


def write_envelope_to_child(
    child: subprocess.Popen,
    *,
    closed: bool,
    envelope: IPCEnvelope,
) -> bool:
    if closed or child.poll() is not None:
        return False
    stdin = child.stdin
    if stdin is None or stdin.closed:
        return False
    try:
        stdin.write(envelope.model_dump_json())
        stdin.write("\n")
        stdin.flush()
    except OSError:
        return False
    return True


def read_response_from_child(child: subprocess.Popen) -> IPCEnvelope | None:
    stdout = child.stdout
    if stdout is None or stdout.closed:
        return None
    line = stdout.readline()
    if not line:
        return None
    try:
        return IPCEnvelope.model_validate_json(line)
    except ValueError:
        return None


def subprocess_failure_error(child: subprocess.Popen) -> dict[str, Any]:
    exit_code = child.poll()
    if exit_code is None:
        try:
            exit_code = child.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            return {"message": "Node executor IPC response did not include a result"}
    if exit_code is None:
        return {"message": "Node executor IPC response did not include a result"}
    error: dict[str, Any] = {
        "message": "Node executor subprocess exited before completing task",
        "exit_code": exit_code,
    }
    stderr = read_stderr_tail(child)
    if stderr:
        error["stderr"] = stderr
    return error


def read_stderr_tail(child: subprocess.Popen) -> str:
    if child.poll() is None:
        return ""
    stderr = child.stderr
    if stderr is None or stderr.closed:
        return ""
    try:
        output = stderr.read().strip()
    except OSError:
        return ""
    return output[-2000:]
