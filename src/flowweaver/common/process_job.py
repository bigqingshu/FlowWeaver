from __future__ import annotations

import os
from typing import Protocol


class ProcessJobError(RuntimeError):
    pass


class AssignableProcess(Protocol):
    pid: int


class _Kernel32(Protocol):
    def AssignProcessToJobObject(
        self,
        job_handle: int,
        process_handle: object,
    ) -> int:
        ...

    def CloseHandle(self, handle: int) -> int:
        ...


class ProcessJob(Protocol):
    @property
    def enabled(self) -> bool:
        ...

    def assign(self, process: AssignableProcess) -> None:
        ...

    def close(self) -> None:
        ...


class NoopProcessJob:
    @property
    def enabled(self) -> bool:
        return False

    def assign(self, process: AssignableProcess) -> None:
        return None

    def close(self) -> None:
        return None


class WindowsKillOnCloseJob:
    def __init__(self, *, handle: int, kernel32: _Kernel32) -> None:
        self._handle = handle
        self._kernel32 = kernel32

    @property
    def enabled(self) -> bool:
        return self._handle != 0

    @classmethod
    def create(cls) -> WindowsKillOnCloseJob:
        import ctypes
        from ctypes import wintypes

        class JobObjectBasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JobObjectExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JobObjectBasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        job_object_extended_limit_information = 9
        job_object_limit_kill_on_job_close = 0x00002000
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            _raise_last_windows_error("Could not create Windows Job Object")
        limits = JobObjectExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = (
            job_object_limit_kill_on_job_close
        )
        if not kernel32.SetInformationJobObject(
            handle,
            job_object_extended_limit_information,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            kernel32.CloseHandle(handle)
            _raise_last_windows_error(
                "Could not configure Windows Job Object kill-on-close"
            )
        return cls(handle=handle, kernel32=kernel32)

    def assign(self, process: AssignableProcess) -> None:
        process_handle = getattr(process, "_handle", None)
        if process_handle is None:
            raise ProcessJobError(
                "Could not assign process to Windows Job Object: "
                "process handle is unavailable"
            )
        try:
            process_handle = int(process_handle)
        except (TypeError, ValueError):
            pass
        if not self._kernel32.AssignProcessToJobObject(
            self._handle,
            process_handle,
        ):
            _raise_last_windows_error(
                "Could not assign process to Windows Job Object"
            )

    def close(self) -> None:
        if self._handle == 0:
            return
        handle = self._handle
        self._handle = 0
        if not self._kernel32.CloseHandle(handle):
            _raise_last_windows_error("Could not close Windows Job Object")


def create_process_job() -> ProcessJob:
    if os.name != "nt":
        return NoopProcessJob()
    return WindowsKillOnCloseJob.create()


def _raise_last_windows_error(message: str) -> None:
    import ctypes

    error_code = ctypes.get_last_error()
    raise ProcessJobError(f"{message}. Windows error code: {error_code}")
