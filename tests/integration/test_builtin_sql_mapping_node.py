from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.external_sql_table_provider import (
    EXTERNAL_SQL_PROVIDER_ID,
    SQLiteExternalSqlTableProvider,
)
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.nodes.builtin_table import BuiltinTableNodeRunner
from flowweaver.nodes.default_registry import create_default_node_registry
from flowweaver.protocols.enums import (
    NodeResultStatus,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel


def make_external_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "external.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE orders (row_id INTEGER NOT NULL, amount REAL NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO orders (row_id, amount) VALUES (?, ?)",
            [(1, 8.0), (2, 12.5)],
        )
    return database_path


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def seed_node_run(store: RuntimeStore) -> tuple[str, str]:
    workflow = store.create_workflow_definition(
        name="SQL mapping",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.RUNNING,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="sql-source",
        node_type=SQL_MAPPING_NODE_TYPE,
        node_run_id="node-run-1",
    )
    return run.workflow_run_id, node.node_run_id


def make_runner(tmp_path: Path, store: RuntimeStore) -> BuiltinTableNodeRunner:
    table_provider = SQLiteRuntimeTableProvider(tmp_path / "runtime")
    return BuiltinTableNodeRunner(
        store=store,
        registry=RuntimeDataRegistry(store=store, table_provider=table_provider),
        table_provider=table_provider,
    )


def make_task(
    *,
    workflow_run_id: str,
    node_run_id: str,
    database_path: Path,
    config: dict | None = None,
    input_refs: list[str] | None = None,
) -> NodeTaskModel:
    task_config = {
        "database_path": database_path.as_posix(),
        "table_name": "orders",
        "logical_table_id": "orders",
    }
    if config is not None:
        task_config = config
    return NodeTaskModel(
        workflow_run_id=workflow_run_id,
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=node_run_id,
        node_instance_id="sql-source",
        node_type=SQL_MAPPING_NODE_TYPE,
        node_version="1.0",
        attempt=1,
        input_refs=input_refs or [],
        config=task_config,
        timeout_seconds=60,
    )


def test_default_registry_exposes_sql_mapping_node() -> None:
    registry = create_default_node_registry()
    definition = registry.get(SQL_MAPPING_NODE_TYPE, "1.0")

    assert definition is not None
    assert definition.output_ports[0].name == "out"
    assert definition.config_schema is not None
    assert "database_path" in definition.config_schema.properties


def test_sql_mapping_node_outputs_external_sql_table_ref(tmp_path: Path) -> None:
    external_database = make_external_database(tmp_path)
    store = make_store(tmp_path)
    workflow_run_id, node_run_id = seed_node_run(store)
    runner = make_runner(tmp_path, store)

    result = runner.execute(
        make_task(
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            database_path=external_database,
        ),
        executor_id="executor-1",
    )

    assert result.status == NodeResultStatus.SUCCEEDED
    assert len(result.output_refs) == 1
    table_ref = store.get_table_ref(result.output_refs[0])
    assert table_ref is not None
    assert table_ref.provider_id == EXTERNAL_SQL_PROVIDER_ID
    assert table_ref.storage_kind == TableStorageKind.EXTERNAL_SQL
    assert table_ref.opaque_handle == {
        "database_path": external_database.as_posix(),
        "table_name": "orders",
    }
    assert [field.name for field in table_ref.schema] == ["row_id", "amount"]
    assert SQLiteExternalSqlTableProvider().read_rows(
        table_ref,
        offset=0,
        limit=5,
        order_by=["row_id"],
    ) == [
        {"row_id": 1, "amount": 8.0},
        {"row_id": 2, "amount": 12.5},
    ]


def test_sql_mapping_node_rejects_invalid_config(tmp_path: Path) -> None:
    external_database = make_external_database(tmp_path)
    store = make_store(tmp_path)
    workflow_run_id, node_run_id = seed_node_run(store)
    runner = make_runner(tmp_path, store)

    result = runner.execute(
        make_task(
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            database_path=external_database,
            config={"database_path": external_database.as_posix()},
        ),
        executor_id="executor-1",
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "exactly one of table_name or query" in result.error["message"]


def test_sql_mapping_node_rejects_inputs(tmp_path: Path) -> None:
    external_database = make_external_database(tmp_path)
    store = make_store(tmp_path)
    workflow_run_id, node_run_id = seed_node_run(store)
    runner = make_runner(tmp_path, store)

    result = runner.execute(
        make_task(
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            database_path=external_database,
            input_refs=["upstream-table"],
        ),
        executor_id="executor-1",
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["message"] == "SqlMappingNode does not accept inputs"
