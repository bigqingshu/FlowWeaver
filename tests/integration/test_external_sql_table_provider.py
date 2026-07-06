from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.external_sql_table_provider import (
    EXTERNAL_SQL_PROVIDER_ID,
    SQLiteExternalSqlTableProvider,
)
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
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


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_external_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "external.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE orders (row_id INTEGER NOT NULL, amount REAL NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO orders (row_id, amount) VALUES (?, ?)",
            [(1, 8.0), (2, 12.5), (3, 7.0)],
        )
    return database_path


def make_external_table_ref(
    database_path: Path,
    *,
    table_ref_id: str = "external-orders",
    query: str | None = None,
) -> TableRefModel:
    opaque_handle = (
        {"database_path": database_path.as_posix(), "query": query}
        if query is not None
        else {"database_path": database_path.as_posix(), "table_name": "orders"}
    )
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.EXTERNAL_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id=EXTERNAL_SQL_PROVIDER_ID,
        logical_table_id="orders",
        opaque_handle=opaque_handle,
        schema=[
            FieldSchemaModel(
                field_id="row-id",
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
        ],
        schema_fingerprint="orders-fingerprint",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id="run-1",
        created_by_node_run_id="node-run-1",
        created_at=utc_now(),
    )


def make_client(tmp_path: Path) -> tuple[TestClient, RuntimeStore]:
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


def seed_workflow_run(store: RuntimeStore) -> None:
    workflow = store.create_workflow_definition(
        name="External SQL",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="sql-source",
        node_type="SqlMappingNode",
        node_run_id="node-run-1",
    )


def test_external_sql_provider_reads_table_mapping(tmp_path: Path) -> None:
    database_path = make_external_database(tmp_path)
    provider = SQLiteExternalSqlTableProvider()
    table_ref = make_external_table_ref(database_path)

    assert [field.name for field in provider.get_schema(table_ref)] == [
        "row_id",
        "amount",
    ]
    assert provider.count_rows(table_ref) == 3
    assert provider.read_rows(
        table_ref,
        offset=0,
        limit=2,
        columns=["row_id", "amount"],
        order_by=["-amount"],
    ) == [
        {"row_id": 2, "amount": 12.5},
        {"row_id": 1, "amount": 8.0},
    ]


def test_external_sql_provider_reads_query_mapping(tmp_path: Path) -> None:
    database_path = make_external_database(tmp_path)
    provider = SQLiteExternalSqlTableProvider()
    table_ref = make_external_table_ref(
        database_path,
        query="SELECT row_id, amount FROM orders WHERE amount >= 8",
    )

    assert provider.count_rows(table_ref) == 2
    assert provider.read_rows(
        table_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    ) == [
        {"row_id": 1, "amount": 8.0},
        {"row_id": 2, "amount": 12.5},
    ]


def test_data_api_reads_external_sql_table_ref_with_default_registry(
    tmp_path: Path,
) -> None:
    external_database_path = make_external_database(tmp_path)
    client, store = make_client(tmp_path)
    seed_workflow_run(store)
    table_ref = make_external_table_ref(external_database_path)
    store.register_table_ref(table_ref)

    summary = response_data(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/summary",
            headers=auth_headers(),
        )
    )
    rows = response_data(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            params=[("limit", "1"), ("order_by", "-amount")],
            headers=auth_headers(),
        )
    )

    assert summary["storage_kind"] == "EXTERNAL_SQL"
    assert summary["row_count"] == 3
    assert rows["rows"] == [{"row_id": 2, "amount": 12.5}]

