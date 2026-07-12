from __future__ import annotations

from flowweaver.common.process_job import (
    NoopProcessJob,
    WindowsKillOnCloseJob,
)


def test_noop_process_job_is_disabled() -> None:
    job = NoopProcessJob()

    job.assign(_FakeProcess())
    job.close()

    assert job.enabled is False


def test_windows_process_job_assigns_and_closes_once() -> None:
    kernel32 = _FakeKernel32()
    job = WindowsKillOnCloseJob(handle=11, kernel32=kernel32)
    process = _FakeProcess()

    job.assign(process)
    job.close()
    job.close()

    assert kernel32.assigned == [(11, 22)]
    assert kernel32.closed == [11]
    assert job.enabled is False


class _FakeProcess:
    pid = 123
    _handle = 22


class _FakeKernel32:
    def __init__(self) -> None:
        self.assigned: list[tuple[int, int]] = []
        self.closed: list[int] = []

    def AssignProcessToJobObject(self, job_handle: int, process_handle: int) -> int:
        self.assigned.append((job_handle, process_handle))
        return 1

    def CloseHandle(self, handle: int) -> int:
        self.closed.append(handle)
        return 1
