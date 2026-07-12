from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import RLock

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.api.run_table_cleanup import cleanup_table_refs_for_run
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.engine.table_ref_release import (
    TableRefReleaseOutcome,
    TableRefReleaseService,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class CallbackRuntimeProvider(SQLiteRuntimeTableProvider):
    def __init__(
        self,
        runtime_dir: Path,
        callback: Callable[[], None],
    ) -> None:
        super().__init__(runtime_dir)
        self._callback = callback

    def drop_table(self, table_ref: TableRefModel) -> None:
        self._callback()
        super().drop_table(table_ref)


class FailOnceRuntimeProvider(SQLiteRuntimeTableProvider):
    def __init__(self, runtime_dir: Path) -> None:
        super().__init__(runtime_dir)
        self.calls = 0

    def drop_table(self, table_ref: TableRefModel) -> None:
        self.calls += 1
        if self.calls == 1:
            raise ValueError("temporary drop failure")
        super().drop_table(table_ref)


class CountingMemoryProvider(MemoryTableProvider):
    def __init__(self) -> None:
        super().__init__({}, RLock())
        self.drop_calls = 0

    def drop_table(self, table_ref: TableRefModel) -> None:
        self.drop_calls += 1
        super().drop_table(table_ref)


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def seed_runtime_table(
    tmp_path: Path,
) -> tuple[RuntimeStore, TableRefModel, str, str]:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Release workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-release",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-release",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-release",
    )
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime-tables")
    staging = provider.create_staging_table(
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        output_name="orders",
        schema=[
            FieldSchemaModel(
                field_id="orders-row-id",
                name="row_id",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
    )
    provider.insert_rows(staging, [{"row_id": 1}])
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return store, published, workflow.workflow_id, run.workflow_run_id


def test_release_claim_prevents_new_publication_before_drop(
    tmp_path: Path,
) -> None:
    store, published, workflow_id, workflow_run_id = seed_runtime_table(tmp_path)
    callback_called = False

    def create_publication_after_claim() -> None:
        nonlocal callback_called
        callback_called = True
        with pytest.raises(ValueError, match="must be PUBLISHED"):
            store.create_shared_publication(
                share_name="daily_report",
                producer_workflow_id=workflow_id,
                producer_run_id=workflow_run_id,
                members={"orders": published.table_ref_id},
            )

    registry = TableProviderRegistry()
    registry.register(
        CallbackRuntimeProvider(
            tmp_path / "runtime-tables",
            create_publication_after_claim,
        ),
        storage_kinds=(published.storage_kind,),
    )
    service = TableRefReleaseService(store=store, provider_registry=registry)

    result = service.release(published.table_ref_id)

    loaded = store.get_table_ref(published.table_ref_id)
    assert callback_called is True
    assert result.outcome == TableRefReleaseOutcome.RELEASED
    assert loaded is not None
    assert loaded.lifecycle_status == LifecycleStatus.RELEASED
    assert store.get_latest_shared_publication("daily_report") is None


def test_release_retries_releasable_table_after_provider_failure(
    tmp_path: Path,
) -> None:
    store, published, _workflow_id, _workflow_run_id = seed_runtime_table(tmp_path)
    fail_once_provider = FailOnceRuntimeProvider(tmp_path / "runtime-tables")
    registry = TableProviderRegistry()
    registry.register(
        fail_once_provider,
        storage_kinds=(published.storage_kind,),
    )
    service = TableRefReleaseService(store=store, provider_registry=registry)

    first = service.release(published.table_ref_id)
    claimed = store.get_table_ref(published.table_ref_id)
    second = service.release(published.table_ref_id)
    released = store.get_table_ref(published.table_ref_id)

    assert first.outcome == TableRefReleaseOutcome.FAILED
    assert first.reason == "temporary drop failure"
    assert claimed is not None
    assert claimed.lifecycle_status == LifecycleStatus.RELEASABLE
    assert second.outcome == TableRefReleaseOutcome.RELEASED
    assert released is not None
    assert released.lifecycle_status == LifecycleStatus.RELEASED
    assert fail_once_provider.calls == 2


def test_release_service_drops_active_memory_table(tmp_path: Path) -> None:
    store, _published, _workflow_id, workflow_run_id = seed_runtime_table(tmp_path)
    provider = MemoryTableProvider({}, RLock())
    table_ref = provider.create_memory_table(
        workflow_run_id=workflow_run_id,
        node_run_id="node-release",
        logical_table_id="memory-orders",
        schema=[
            FieldSchemaModel(
                field_id="memory-row-id",
                name="row_id",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
        rows=[{"row_id": 1}],
    )
    store.register_table_ref(table_ref)
    registry = TableProviderRegistry()
    registry.register(provider, storage_kinds=(TableStorageKind.MEMORY,))
    service = TableRefReleaseService(store=store, provider_registry=registry)

    result = service.release(table_ref.table_ref_id)

    assert result.outcome == TableRefReleaseOutcome.RELEASED
    released = store.get_table_ref(table_ref.table_ref_id)
    assert released is not None
    assert released.lifecycle_status == LifecycleStatus.RELEASED
    with pytest.raises(ValueError, match="memory table is not available"):
        provider.read_rows(table_ref, offset=0, limit=1)


def test_release_stop_after_provider_keeps_releasable_for_restart(
    tmp_path: Path,
) -> None:
    store, published, _workflow_id, _workflow_run_id = seed_runtime_table(tmp_path)
    stopped = False

    def request_stop() -> None:
        nonlocal stopped
        stopped = True

    registry = TableProviderRegistry()
    registry.register(
        CallbackRuntimeProvider(tmp_path / "runtime-tables", request_stop),
        storage_kinds=(published.storage_kind,),
    )
    service = TableRefReleaseService(store=store, provider_registry=registry)

    result = service.release(
        published.table_ref_id,
        should_stop=lambda: stopped,
    )

    assert result.outcome == TableRefReleaseOutcome.FAILED
    assert result.reason == "release_stopped_after_provider"
    table_ref = store.get_table_ref(published.table_ref_id)
    assert table_ref is not None
    assert table_ref.lifecycle_status == LifecycleStatus.RELEASABLE


def test_cleanup_run_table_refs_continues_250_refs_in_bounded_batches(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Bounded cleanup workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-bounded-cleanup",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-bounded-cleanup",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-bounded-cleanup",
    )
    provider = CountingMemoryProvider()
    registry = TableProviderRegistry()
    registry.register(provider, storage_kinds=(TableStorageKind.MEMORY,))
    schema = [
        FieldSchemaModel(
            field_id="row-id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        )
    ]
    for index in range(250):
        table_ref = provider.create_memory_table(
            workflow_run_id=run.workflow_run_id,
            node_run_id=node.node_run_id,
            logical_table_id=f"table-{index:03d}",
            schema=schema,
            rows=[{"row_id": index}],
        )
        store.register_table_ref(table_ref)

    cursor = None
    cleaned_count = 0
    batch_count = 0
    while True:
        calls_before = provider.drop_calls
        result = cleanup_table_refs_for_run(
            workflow_run_id=run.workflow_run_id,
            store=store,
            provider_registry=registry,
            cursor=cursor,
            max_refs=10,
            time_budget_ms=10000,
        )
        batch_count += 1
        cleaned_count += int(result["cleaned_count"])
        assert int(result["processed_count"]) <= 10
        assert provider.drop_calls - calls_before <= 10
        if result["outcome"] == "COMPLETED":
            assert result["continuation_cursor"] is None
            break
        assert result["outcome"] == "RETRY_PENDING"
        cursor = str(result["continuation_cursor"])

    assert batch_count == 25
    assert cleaned_count == 250
    assert provider.drop_calls == 250


def test_cleanup_run_table_refs_stops_before_starting_ref_after_time_budget(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Timed cleanup workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-timed-cleanup",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-timed-cleanup",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-timed-cleanup",
    )
    provider = CountingMemoryProvider()
    registry = TableProviderRegistry()
    registry.register(provider, storage_kinds=(TableStorageKind.MEMORY,))
    schema = [
        FieldSchemaModel(
            field_id="row-id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        )
    ]
    for index in range(3):
        table_ref = provider.create_memory_table(
            workflow_run_id=run.workflow_run_id,
            node_run_id=node.node_run_id,
            logical_table_id=f"timed-{index}",
            schema=schema,
            rows=[],
        )
        store.register_table_ref(table_ref)
    ticks = iter([0.0, 0.0, 0.5, 1.0])

    first = cleanup_table_refs_for_run(
        workflow_run_id=run.workflow_run_id,
        store=store,
        provider_registry=registry,
        max_refs=10,
        time_budget_ms=750,
        clock=lambda: next(ticks),
    )

    assert first["outcome"] == "RETRY_PENDING"
    assert first["processed_count"] == 2
    assert first["cleaned_count"] == 2
    assert provider.drop_calls == 2
    assert first["continuation_cursor"] is not None

    second = cleanup_table_refs_for_run(
        workflow_run_id=run.workflow_run_id,
        store=store,
        provider_registry=registry,
        cursor=str(first["continuation_cursor"]),
        max_refs=10,
        time_budget_ms=750,
        clock=lambda: 0.0,
    )

    assert second["outcome"] == "COMPLETED"
    assert second["processed_count"] == 1
    assert provider.drop_calls == 3
