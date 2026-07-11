from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

TOKEN = "test-token"


class FakeTableProvider:
    provider_id = "fake_provider"

    def __init__(self) -> None:
        self.schema = [
            FieldSchemaModel(
                field_id="amount",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ]
        self.rows = [{"amount": 12.5}, {"amount": 7.0}]

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        return list(self.schema)

    def count_rows(self, table_ref: TableRefModel) -> int:
        return len(self.rows)

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        selected_columns = columns or [field.name for field in self.schema]
        return [
            {column: row[column] for column in selected_columns}
            for row in self.rows[offset : offset + limit]
        ]

    def create_table(self, table_ref: TableRefModel) -> None:
        raise NotImplementedError

    def drop_table(self, table_ref: TableRefModel) -> None:
        raise NotImplementedError

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        raise NotImplementedError


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_client(
    tmp_path: Path,
    *,
    provider_registry: TableProviderRegistry,
) -> tuple[TestClient, RuntimeStore]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    config = EngineConfig(
        data_dir=tmp_path / "runtime",
        local_api_token=TOKEN,
        enforce_single_instance=False,
    )
    event_router = EventRouter(store)
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
    return TestClient(create_app(container)), store


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    return payload["data"]


def response_error(response):
    payload = response.json()
    assert payload["ok"] is False
    assert payload["data"] is None
    return payload["error"]


def seed_table_ref(
    store: RuntimeStore,
    *,
    provider_id: str = "fake_provider",
    storage_kind: TableStorageKind = TableStorageKind.MEMORY,
    capabilities: set[str] | None = None,
    lifecycle_status: LifecycleStatus = LifecycleStatus.PUBLISHED,
) -> TableRefModel:
    workflow = store.create_workflow_definition(
        name="Provider routing",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="FakeNode",
        node_run_id="node-run-1",
    )
    table_ref = TableRefModel(
        table_ref_id="table-1",
        role=TableRole.CURRENT,
        storage_kind=storage_kind,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id=provider_id,
        logical_table_id="orders",
        opaque_handle={"fake": "handle"},
        schema=[
            FieldSchemaModel(
                field_id="amount",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint="orders-fingerprint",
        version=1,
        capabilities={"READ"} if capabilities is None else capabilities,
        lifecycle_status=lifecycle_status,
        created_by_workflow_run_id=run.workflow_run_id,
        created_by_node_run_id=node.node_run_id,
        created_at=utc_now(),
    )
    store.register_table_ref(table_ref)
    return table_ref


def test_data_api_routes_reads_to_registered_provider(tmp_path: Path) -> None:
    provider = FakeTableProvider()
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        provider,
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    client, store = make_client(tmp_path, provider_registry=provider_registry)
    table_ref = seed_table_ref(store)

    schema = response_data(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/schema",
            headers=auth_headers(),
        )
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
        )
    )

    assert [field["name"] for field in schema["schema"]] == ["amount"]
    assert summary["storage_kind"] == "MEMORY"
    assert summary["row_count"] == 2
    assert rows["rows"] == [{"amount": 12.5}, {"amount": 7.0}]


def test_data_api_rejects_unknown_provider(tmp_path: Path) -> None:
    client, store = make_client(
        tmp_path,
        provider_registry=TableProviderRegistry(),
    )
    table_ref = seed_table_ref(store, provider_id="missing_provider")

    error = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
        )
    )

    assert error["error_code"] == "DATA_PROVIDER_UNSUPPORTED"


def test_data_api_rejects_unsupported_storage_kind(tmp_path: Path) -> None:
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        FakeTableProvider(),
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    client, store = make_client(tmp_path, provider_registry=provider_registry)
    table_ref = seed_table_ref(
        store,
        storage_kind=TableStorageKind.RUNTIME_SQL,
    )

    error = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
        )
    )

    assert error["error_code"] == "DATA_STORAGE_UNSUPPORTED"


def test_data_api_rejects_table_ref_without_read_capability(
    tmp_path: Path,
) -> None:
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        FakeTableProvider(),
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    client, store = make_client(tmp_path, provider_registry=provider_registry)
    table_ref = seed_table_ref(store, capabilities={"APPEND"})

    error = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
        )
    )

    assert error["error_code"] == "TABLE_REF_NOT_READABLE"


def test_data_api_rejects_unavailable_table_ref(tmp_path: Path) -> None:
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        FakeTableProvider(),
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    client, store = make_client(tmp_path, provider_registry=provider_registry)
    table_ref = seed_table_ref(
        store,
        lifecycle_status=LifecycleStatus.RELEASED,
    )

    error = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
        )
    )

    assert error["error_code"] == "TABLE_REF_NOT_AVAILABLE"


def test_data_api_rejects_releasable_table_ref(tmp_path: Path) -> None:
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        FakeTableProvider(),
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    client, store = make_client(tmp_path, provider_registry=provider_registry)
    table_ref = seed_table_ref(
        store,
        lifecycle_status=LifecycleStatus.RELEASABLE,
    )

    error = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            headers=auth_headers(),
        )
    )

    assert error["error_code"] == "TABLE_REF_NOT_AVAILABLE"
