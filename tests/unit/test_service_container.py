from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.engine.service_container import ServiceContainer


class RecordingSupervisor:
    def __init__(self, calls: list[str], *, fail_close: bool = False) -> None:
        self._calls = calls
        self._fail_close = fail_close

    def start(self) -> None:
        self._calls.append("supervisor.start")

    def close(self) -> None:
        self._calls.append("supervisor.close")
        if self._fail_close:
            raise ValueError("supervisor close failed")


class RecordingWorker:
    def __init__(self, calls: list[str], *, fail_close: bool = False) -> None:
        self._calls = calls
        self._fail_close = fail_close

    def start(self) -> None:
        self._calls.append("worker.start")

    def close(self) -> None:
        self._calls.append("worker.close")
        if self._fail_close:
            raise ValueError("worker close failed")


class RecordingStore:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def dispose(self) -> None:
        self._calls.append("store.dispose")


class RecordingInstanceLock:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def release(self) -> None:
        self._calls.append("instance_lock.release")


def make_container(
    calls: list[str],
    *,
    worker_fail_close: bool = False,
    supervisor_fail_close: bool = False,
) -> ServiceContainer:
    return ServiceContainer(
        config=EngineConfig(),
        runtime_store=RecordingStore(calls),  # type: ignore[arg-type]
        event_router=object(),  # type: ignore[arg-type]
        table_lease_manager=object(),  # type: ignore[arg-type]
        supervisor=RecordingSupervisor(  # type: ignore[arg-type]
            calls,
            fail_close=supervisor_fail_close,
        ),
        node_registry=object(),  # type: ignore[arg-type]
        shared_publication_cleanup_worker=RecordingWorker(  # type: ignore[arg-type]
            calls,
            fail_close=worker_fail_close,
        ),
        instance_lock=RecordingInstanceLock(calls),  # type: ignore[arg-type]
    )


def test_service_container_starts_and_closes_in_dependency_order() -> None:
    calls: list[str] = []
    container = make_container(calls)

    container.start()
    container.start()
    container.close()
    container.close()

    assert calls == [
        "supervisor.start",
        "worker.start",
        "worker.close",
        "supervisor.close",
        "store.dispose",
        "instance_lock.release",
    ]


def test_service_container_continues_close_after_component_failures() -> None:
    calls: list[str] = []
    container = make_container(
        calls,
        worker_fail_close=True,
        supervisor_fail_close=True,
    )

    with pytest.raises(ExceptionGroup) as captured:
        container.close()

    assert len(captured.value.exceptions) == 2
    assert calls == [
        "worker.close",
        "supervisor.close",
        "store.dispose",
        "instance_lock.release",
    ]


def test_engine_host_lifespan_uses_container_start_and_close() -> None:
    calls: list[str] = []

    class LifespanContainer:
        def start(self) -> None:
            calls.append("container.start")

        def close(self) -> None:
            calls.append("container.close")

    with TestClient(create_app(LifespanContainer())) as client:  # type: ignore[arg-type]
        assert client.get("/api/v1/health").status_code == 200

    assert calls == ["container.start", "container.close"]
