from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import IO, Any

from flowweaver.protocols.ipc_messages import IPCEnvelope


def src_path() -> Path:
    return Path(__file__).resolve().parents[2]


def child_environment(
    base_env: Mapping[str, str] | None = None,
    *,
    include_src_path: bool = True,
) -> dict[str, str]:
    env = dict(base_env) if base_env is not None else os.environ.copy()
    if not include_src_path:
        env.pop("PYTHONPATH", None)
        return env
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
    return read_response_from_child_with_limits(child)


def read_response_from_child_with_limits(
    child: subprocess.Popen,
    *,
    timeout_seconds: float | None = None,
    max_chars: int = 1024 * 1024,
) -> IPCEnvelope | None:
    stdout = child.stdout
    if stdout is None or stdout.closed:
        return None
    line = _readline(
        stdout,
        timeout_seconds=timeout_seconds,
        max_chars=max_chars,
    )
    if not line:
        return None
    if len(line) > max_chars:
        return None
    try:
        return IPCEnvelope.model_validate_json(line)
    except ValueError:
        return None


def subprocess_failure_error(
    child: subprocess.Popen,
    *,
    stderr_tail: str | None = None,
) -> dict[str, Any]:
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
    stderr = stderr_tail if stderr_tail is not None else read_stderr_tail(child)
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


class StderrTailCollector:
    def __init__(self, stream: IO[str] | None, *, max_chars: int = 2000) -> None:
        self._stream = stream
        self._max_chars = max_chars
        self._tail = ""
        self._lock = Lock()
        self._thread: Thread | None = None
        if stream is not None:
            self._thread = Thread(
                target=self._collect,
                name="flowweaver-subprocess-stderr-tail",
                daemon=True,
            )
            self._thread.start()

    def text(self) -> str:
        with self._lock:
            return self._tail.strip()

    def join(self, timeout_seconds: float = 1.0) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)

    def _collect(self) -> None:
        if self._stream is None:
            return
        try:
            while True:
                chunk = self._stream.read(1024)
                if not chunk:
                    return
                with self._lock:
                    self._tail = (self._tail + chunk)[-self._max_chars :]
        except (OSError, ValueError):
            return


def _readline(
    stream: IO[str],
    *,
    timeout_seconds: float | None,
    max_chars: int,
) -> str | None:
    if timeout_seconds is None:
        return stream.readline(max_chars + 1)
    results: Queue[str | None] = Queue(maxsize=1)

    def read() -> None:
        try:
            results.put(stream.readline(max_chars + 1))
        except (OSError, ValueError):
            results.put(None)

    reader = Thread(
        target=read,
        name="flowweaver-subprocess-stdout-read",
        daemon=True,
    )
    reader.start()
    try:
        return results.get(timeout=max(timeout_seconds, 0))
    except Empty:
        return None
