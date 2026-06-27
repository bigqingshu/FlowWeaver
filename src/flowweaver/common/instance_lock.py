from __future__ import annotations

import os
import sys
from pathlib import Path


class InstanceLockError(RuntimeError):
    pass


class InstanceLock:
    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._handle: int | None = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            self._handle = os.open(self.lock_path, flags)
        except FileExistsError as exc:
            if self._is_stale():
                self.lock_path.unlink(missing_ok=True)
                self._handle = os.open(self.lock_path, flags)
                os.write(self._handle, str(os.getpid()).encode("ascii"))
                return
            raise InstanceLockError(
                f"EngineHost is already running for data dir: {self.lock_path.parent}"
            ) from exc
        os.write(self._handle, str(os.getpid()).encode("ascii"))

    def release(self) -> None:
        if self._handle is not None:
            os.close(self._handle)
            self._handle = None
        self.lock_path.unlink(missing_ok=True)

    def _is_stale(self) -> bool:
        try:
            pid = int(self.lock_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return True
        if pid <= 0:
            return True
        return not _process_exists(pid)

    def __enter__(self) -> InstanceLock:
        self.acquire()
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.release()


def _process_exists(pid: int) -> bool:
    if sys.platform == "win32":
        return _windows_process_exists(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _windows_process_exists(pid: int) -> bool:
    import ctypes

    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(
        process_query_limited_information,
        False,
        pid,
    )
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)
