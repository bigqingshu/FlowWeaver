from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import BuiltinTableNodeExecutor
from flowweaver.nodes.builtin_table import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.nodes.permissions import resolve_builtin_node_permissions
from flowweaver.protocols.enums import LifecycleStatus, NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.permissions import PermissionGrantModel


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def make_executor(tmp_path: Path) -> tuple[
    BuiltinTableNodeExecutor,
    RuntimeStore,
    RuntimeDataRegistry,
    SQLiteRuntimeTableProvider,
]:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-executor-1",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    return executor, store, registry, provider


def make_task(
    *,
    node_type: str,
    node_run_id: str,
    node_instance_id: str,
    config: dict,
    input_refs: list[str] | None = None,
) -> NodeTaskModel:
    return NodeTaskModel(
        workflow_run_id="run-1",
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=node_run_id,
        node_instance_id=node_instance_id,
        node_type=node_type,
        node_version="1.0",
        attempt=1,
        input_refs=input_refs or [],
        config=config,
        timeout_seconds=60,
    )


def grant_task_permissions(store: RuntimeStore, task: NodeTaskModel) -> NodeTaskModel:
    request = resolve_builtin_node_permissions(task)
    grant = store.create_permission_grant(
        PermissionGrantModel(
            request_id=request.request_id,
            workflow_run_id=request.workflow_run_id,
            node_run_id=request.node_run_id,
            scopes=request.scopes,
            granted=True,
            audit_level=request.audit_level,
        )
    )
    return task.model_copy(
        update={"permission_handle_id": grant.permission_handle_id}
    )


def test_generate_test_table_node_publishes_runtime_sql_table_ref(
    tmp_path: Path,
) -> None:
    executor, store, registry, provider = make_executor(tmp_path)
    task = grant_task_permissions(
        store,
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 4,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "amount", "data_type": "FLOAT"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 7,
            },
        ),
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.executor_id == "builtin-executor-1"
    assert len(result.output_refs) == 1
    published = registry.get(result.output_refs[0])
    assert published.lifecycle_status == LifecycleStatus.PUBLISHED
    assert published.logical_table_id == "generate_output"
    assert provider.count_rows(published) == 4
    assert provider.read_rows(published, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "label": "label_7_1"},
        {"row_id": 2, "amount": 2.0, "label": "label_7_2"},
        {"row_id": 3, "amount": 3.0, "label": "label_7_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_7_4"},
    ]


def test_filter_rows_node_publishes_filtered_table_ref_without_mutating_input(
    tmp_path: Path,
) -> None:
    executor, store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        grant_task_permissions(
            store,
            make_task(
                node_type=GENERATE_TEST_TABLE_NODE_TYPE,
                node_run_id="node-run-generate",
                node_instance_id="generate",
                config={
                    "rows": 5,
                    "columns": ["row_id", "amount", "label"],
                    "seed": 0,
                },
            ),
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    filter_task = grant_task_permissions(
        store,
        make_task(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_run_id="node-run-filter",
            node_instance_id="filter",
            input_refs=[input_ref.table_ref_id],
            config={"field": "amount", "operator": "GT", "value": 2.0},
        ),
    )

    filter_result = executor.execute(filter_task)

    assert filter_result.status == NodeResultStatus.SUCCEEDED
    assert filter_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 5
    filtered_ref = registry.get(filter_result.output_refs[0])
    assert filtered_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert filtered_ref.logical_table_id == "filter_output"
    assert provider.count_rows(filtered_ref) == 3
    filtered_rows = provider.read_rows(
        filtered_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    )
    assert filtered_rows == [
        {"row_id": 3, "amount": 3.0, "label": "label_0_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_0_4"},
        {"row_id": 5, "amount": 5.0, "label": "label_0_5"},
    ]


def test_filter_rows_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        grant_task_permissions(
            store,
            make_task(
                node_type=GENERATE_TEST_TABLE_NODE_TYPE,
                node_run_id="node-run-generate",
                node_instance_id="generate",
                config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
            ),
        )
    )
    filter_task = grant_task_permissions(
        store,
        make_task(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_run_id="node-run-filter",
            node_instance_id="filter",
            input_refs=generate_result.output_refs,
            config={"field": "missing", "operator": "EQ", "value": 1},
        ),
    )

    result = executor.execute(filter_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_builtin_table_node_rejects_missing_publish_permission(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    task = make_task(
        node_type=GENERATE_TEST_TABLE_NODE_TYPE,
        node_run_id="node-run-generate",
        node_instance_id="generate",
        config={"rows": 1, "columns": ["row_id"], "seed": 0},
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert result.error["message"] == "Node task is missing permission_handle_id"
    assert registry.list_by_workflow_run("run-1") == []
