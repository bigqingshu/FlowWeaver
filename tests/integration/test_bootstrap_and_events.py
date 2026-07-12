from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from flowweaver.common.config import EngineConfig
from flowweaver.common.instance_lock import InstanceLockError
from flowweaver.engine.bootstrap import EngineHostBootstrap, bootstrap_default
from flowweaver.engine.event_router import EventRouter
from flowweaver.protocols.enums import EventType


class _MemoryEventStore:
    def __init__(self) -> None:
        self.sequence_number = 0

    def append_runtime_event(self, _event) -> int:
        self.sequence_number += 1
        return self.sequence_number


def test_bootstrap_creates_data_dirs_token_and_blocks_second_instance(
    tmp_path: Path,
) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    container = EngineHostBootstrap(config).initialize()
    try:
        assert config.data_dir.joinpath("metadata", "flowweaver.db").exists()
        assert config.data_dir.joinpath("config", "local_api_token").exists()
        assert container.table_provider_registry is not None
        assert container.shared_publication_lifecycle_service is not None
        assert container.shared_publication_cleanup_worker is not None
        assert (
            container.shared_publication_cleanup_worker._lifecycle_service
            is container.shared_publication_lifecycle_service
        )
        assert (
            container.shared_publication_lifecycle_service
            ._table_ref_release_service
            ._provider_registry
            is container.table_provider_registry
        )

        with pytest.raises(InstanceLockError):
            EngineHostBootstrap(config).initialize()
    finally:
        container.close()


def test_bootstrap_starts_and_stops_shared_cleanup_worker(tmp_path: Path) -> None:
    container = EngineHostBootstrap(
        EngineConfig(
            data_dir=tmp_path / "data",
            shared_publication_cleanup_enabled=True,
            shared_publication_cleanup_interval_seconds=0.05,
        )
    ).initialize()
    worker = container.shared_publication_cleanup_worker
    assert worker is not None
    try:
        container.start()
        assert worker.is_running
    finally:
        container.close()

    assert worker.is_running is False


def test_bootstrap_default_accepts_workflow_process_execution_config(
    tmp_path: Path,
) -> None:
    container = bootstrap_default(
        tmp_path / "runtime",
        workflow_process_execution_mode="threaded",
        workflow_process_max_concurrent_node_tasks="2",
    )
    try:
        assert container.config.workflow_process_execution_mode == "threaded"
        assert container.config.workflow_process_max_concurrent_node_tasks == 2
        assert (
            container.supervisor._config.workflow_process_execution_mode
            == "threaded"
        )
        assert (
            container.supervisor._config.workflow_process_max_concurrent_node_tasks
            == 2
        )
    finally:
        container.close()


def test_bootstrap_default_resolves_runtime_paths_to_absolute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    shutil.copy2(repo_root / "alembic.ini", tmp_path / "alembic.ini")
    shutil.copytree(repo_root / "migrations", tmp_path / "migrations")
    monkeypatch.chdir(tmp_path)

    container = bootstrap_default("relative-runtime")
    try:
        expected_data_dir = (tmp_path / "relative-runtime").resolve()
        assert container.config.data_dir == expected_data_dir
        assert container.config.resolved_metadata_db_path() == (
            expected_data_dir / "metadata" / "flowweaver.db"
        )
        assert container.config.resolved_runtime_dir() == (
            expected_data_dir / "workflow_runs"
        )
        assert container.config.resolved_log_dir() == expected_data_dir / "logs"
        assert container.config.resolved_temp_dir() == expected_data_dir / "temp"
        assert container.supervisor._config.data_dir == expected_data_dir
    finally:
        container.close()


@pytest.mark.asyncio
async def test_event_router_broadcasts_to_multiple_subscribers() -> None:
    event_router = EventRouter(_MemoryEventStore())
    first = await event_router.subscribe()
    second = await event_router.subscribe()

    published = await event_router.publish(
        EventType.WORKFLOW_STARTED,
        payload={"workflow_run_id": "run-1"},
    )

    assert (await asyncio.wait_for(first.get(), timeout=1)).event == published.event
    assert (await asyncio.wait_for(second.get(), timeout=1)).event == published.event
    assert published.sequence_number == 1
