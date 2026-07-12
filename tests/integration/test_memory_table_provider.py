from __future__ import annotations

from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig, MemoryTableLimits
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.memory_table_provider import (
    MEMORY_PROVIDER_ID,
    MemoryTableProvider,
)
from flowweaver.engine.memory_table_storage import MemoryTable
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.engine.table_provider_registry import (
    create_default_table_provider_registry,
)
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableRole,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

TOKEN = "test-token"


class CountingRow(Mapping[str, Any]):
    field_reads = 0

    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> Any:
        type(self).field_reads += 1
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    @classmethod
    def reset(cls) -> None:
        cls.field_reads = 0


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def make_client(
    tmp_path: Path,
    *,
    store: RuntimeStore,
    memory_provider: MemoryTableProvider,
) -> TestClient:
    config = EngineConfig(
        data_dir=tmp_path / "runtime",
        local_api_token=TOKEN,
        enforce_single_instance=False,
    )
    event_router = EventRouter(store)
    provider_registry = create_default_table_provider_registry(
        config.resolved_runtime_dir(),
        memory_provider=memory_provider,
    )
    container = ServiceContainer(
        config=config,
        runtime_store=store,
        event_router=event_router,
        table_lease_manager=TableLeaseManager(store.engine),
        supervisor=Supervisor(
            config=config,
            runtime_store=store,
            event_router=event_router,
        ),
        node_registry=NodeRegistry(),
        table_provider_registry=provider_registry,
    )
    return TestClient(create_app(container))


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    return payload["data"]


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_schema() -> list[FieldSchemaModel]:
    return [
        FieldSchemaModel(
            field_id="row_id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        ),
        FieldSchemaModel(
            field_id="amount",
            name="amount",
            data_type="FLOAT",
            nullable=False,
            ordinal=1,
        ),
    ]


def create_run_with_node(store: RuntimeStore) -> tuple[str, str]:
    workflow = store.create_workflow_definition(
        name="Memory provider workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-memory",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-memory",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="save-memory",
        node_type="SaveMemoryTableNode",
        node_run_id="node-run-memory",
    )
    return run.workflow_run_id, node.node_run_id


def create_memory_ref(
    provider: MemoryTableProvider,
    *,
    workflow_run_id: str = "run-memory",
    node_run_id: str = "node-run-memory",
    logical_table_id: str = "scratch",
) -> TableRefModel:
    return provider.create_memory_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        logical_table_id=logical_table_id,
        schema=make_schema(),
        rows=[
            {"row_id": 1, "amount": 12.5},
            {"row_id": 2, "amount": 7.0},
        ],
    )


def replace_with_counting_rows(
    tables: dict[str, MemoryTable],
    *,
    row_count: int,
) -> None:
    table = next(iter(tables.values()))
    table.rows = [
        CountingRow({"row_id": index, "amount": float(index)})
        for index in range(row_count)
    ]  # type: ignore[list-item]


def test_memory_table_provider_reads_registered_rows() -> None:
    provider = MemoryTableProvider(tables={})
    table_ref = create_memory_ref(provider)

    assert table_ref.provider_id == MEMORY_PROVIDER_ID
    assert table_ref.storage_kind == TableStorageKind.MEMORY
    assert table_ref.role == TableRole.AUXILIARY
    assert table_ref.lifecycle_status == LifecycleStatus.ACTIVE
    assert [field.name for field in provider.get_schema(table_ref)] == [
        "row_id",
        "amount",
    ]
    assert provider.count_rows(table_ref) == 2
    assert provider.read_rows(table_ref, offset=0, limit=1) == [
        {"row_id": 1, "amount": 12.5}
    ]
    assert provider.read_rows(
        table_ref,
        offset=0,
        limit=2,
        columns=["amount"],
        order_by=["-amount"],
    ) == [{"amount": 12.5}, {"amount": 7.0}]


def test_memory_table_provider_soft_limit_does_not_reject_or_evict_rows() -> None:
    provider = MemoryTableProvider(
        tables={},
        limits=MemoryTableLimits(soft_row_limit=1),
    )

    table_ref = create_memory_ref(provider)

    assert provider.limits == MemoryTableLimits(soft_row_limit=1)
    assert provider.count_rows(table_ref) == 2
    assert provider.read_rows(table_ref, offset=0, limit=10) == [
        {"row_id": 1, "amount": 12.5},
        {"row_id": 2, "amount": 7.0},
    ]


def test_memory_table_provider_unsorted_page_only_reads_selected_fields() -> None:
    tables: dict[str, MemoryTable] = {}
    provider = MemoryTableProvider(tables=tables)
    table_ref = create_memory_ref(provider)
    replace_with_counting_rows(tables, row_count=10_000)
    CountingRow.reset()

    rows = provider.read_rows(
        table_ref,
        offset=5_000,
        limit=20,
        columns=["amount"],
    )

    assert rows == [
        {"amount": float(index)} for index in range(5_000, 5_020)
    ]
    assert CountingRow.field_reads == 20


def test_memory_table_provider_count_and_schema_do_not_read_row_fields() -> None:
    tables: dict[str, MemoryTable] = {}
    provider = MemoryTableProvider(tables=tables)
    table_ref = create_memory_ref(provider)
    replace_with_counting_rows(tables, row_count=10_000)
    CountingRow.reset()

    assert provider.count_rows(table_ref) == 10_000
    assert [field.name for field in provider.get_schema(table_ref)] == [
        "row_id",
        "amount",
    ]
    assert CountingRow.field_reads == 0


def test_memory_table_provider_limit_zero_does_not_read_row_fields() -> None:
    tables: dict[str, MemoryTable] = {}
    provider = MemoryTableProvider(tables=tables)
    table_ref = create_memory_ref(provider)
    replace_with_counting_rows(tables, row_count=10_000)
    CountingRow.reset()

    assert provider.read_rows(table_ref, offset=0, limit=0) == []
    assert CountingRow.field_reads == 0


def test_memory_table_provider_sorted_read_uses_full_snapshot() -> None:
    tables: dict[str, MemoryTable] = {}
    provider = MemoryTableProvider(tables=tables)
    table_ref = create_memory_ref(provider)
    replace_with_counting_rows(tables, row_count=100)
    CountingRow.reset()

    rows = provider.read_rows(
        table_ref,
        offset=0,
        limit=2,
        columns=["row_id"],
        order_by=["-amount"],
    )

    assert rows == [{"row_id": 99}, {"row_id": 98}]
    assert CountingRow.field_reads >= 200


def test_memory_table_provider_concurrent_replace_returns_complete_pages() -> None:
    provider = MemoryTableProvider(tables={})
    table_ref = provider.create_memory_table(
        workflow_run_id="run-memory",
        node_run_id="node-run-memory",
        logical_table_id="concurrent",
        schema=make_schema(),
        rows=[{"row_id": index, "amount": 1.0} for index in range(100)],
    )
    barrier = Barrier(2)
    observed_generations: list[set[float]] = []

    def replace_rows() -> None:
        barrier.wait()
        for generation in range(2, 30):
            provider.replace_rows(
                table_ref,
                [
                    {"row_id": index, "amount": float(generation)}
                    for index in range(100)
                ],
            )

    def read_rows() -> None:
        barrier.wait()
        for _ in range(100):
            rows = provider.read_rows(table_ref, offset=0, limit=100)
            observed_generations.append({row["amount"] for row in rows})

    with ThreadPoolExecutor(max_workers=2) as executor:
        replace_future = executor.submit(replace_rows)
        read_future = executor.submit(read_rows)
        replace_future.result()
        read_future.result()

    assert observed_generations
    assert all(len(generation) == 1 for generation in observed_generations)


def test_memory_table_provider_creates_table_from_batches() -> None:
    provider = MemoryTableProvider(tables={})

    table_ref = provider.create_memory_table_from_batches(
        workflow_run_id="run-memory",
        node_run_id="node-run-memory",
        logical_table_id="batched",
        schema=make_schema(),
        row_batches=(
            [{"row_id": 1, "amount": 12.5}],
            [{"row_id": 2, "amount": 7.0}],
        ),
    )

    assert table_ref.logical_table_id == "batched"
    assert provider.count_rows(table_ref) == 2
    assert provider.read_rows(table_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 12.5},
        {"row_id": 2, "amount": 7.0},
    ]


def test_memory_table_provider_replaces_rows_atomically() -> None:
    provider = MemoryTableProvider(tables={})
    table_ref = create_memory_ref(provider)

    provider.replace_row_batches(
        table_ref,
        (
            [{"row_id": 3, "amount": 20.0}],
            [{"row_id": 4, "amount": 30.0}],
        ),
    )

    assert provider.count_rows(table_ref) == 2
    assert provider.read_rows(table_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 3, "amount": 20.0},
        {"row_id": 4, "amount": 30.0},
    ]


def test_memory_table_provider_failed_replace_keeps_existing_rows() -> None:
    provider = MemoryTableProvider(tables={})
    table_ref = create_memory_ref(provider)

    with pytest.raises(ValueError, match="row contains columns not declared"):
        provider.replace_rows(
            table_ref,
            [{"row_id": 3, "amount": 20.0, "unexpected": "nope"}],
        )

    assert provider.read_rows(table_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 12.5},
        {"row_id": 2, "amount": 7.0},
    ]


def test_memory_table_provider_rejects_missing_memory_table() -> None:
    provider = MemoryTableProvider(tables={})
    table_ref = create_memory_ref(provider)
    provider.drop_table(table_ref)

    with pytest.raises(ValueError, match="memory table is not available"):
        provider.count_rows(table_ref)


def test_default_provider_registry_registers_memory_provider(tmp_path: Path) -> None:
    registry = create_default_table_provider_registry(tmp_path / "runtime")

    assert isinstance(registry.get(MEMORY_PROVIDER_ID), MemoryTableProvider)
    assert registry.supports_storage_kind(
        MEMORY_PROVIDER_ID,
        TableStorageKind.MEMORY,
    )


def test_data_api_reads_memory_table_provider(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow_run_id, node_run_id = create_run_with_node(store)
    provider = MemoryTableProvider(tables={})
    table_ref = create_memory_ref(
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
    )
    store.register_table_ref(table_ref)
    client = make_client(
        tmp_path,
        store=store,
        memory_provider=provider,
    )

    summary = response_data(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/summary",
            headers=auth_headers(),
        )
    )
    rows = response_data(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
            params={"limit": 1},
        )
    )

    assert summary["storage_kind"] == "MEMORY"
    assert summary["row_count"] == 2
    assert rows["rows"] == [{"row_id": 1, "amount": 12.5}]
