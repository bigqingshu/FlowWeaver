from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.memory_table_provider import (
    MEMORY_PROVIDER_ID,
    MemoryTableProvider,
)
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import BuiltinTableNodeExecutor
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeResultStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel


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
    executor, store, registry, provider, _memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    return executor, store, registry, provider


def make_executor_with_memory_provider(tmp_path: Path) -> tuple[
    BuiltinTableNodeExecutor,
    RuntimeStore,
    RuntimeDataRegistry,
    SQLiteRuntimeTableProvider,
    MemoryTableProvider,
]:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    memory_provider = MemoryTableProvider(tables={})
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-executor-1",
        store=store,
        registry=registry,
        table_provider=provider,
        memory_provider=memory_provider,
    )
    return executor, store, registry, provider, memory_provider


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


def test_generate_test_table_node_publishes_runtime_sql_table_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    task = make_task(
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
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 5,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    filter_task = make_task(
        node_type=FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-filter",
        node_instance_id="filter",
        input_refs=[input_ref.table_ref_id],
        config={"field": "amount", "operator": "GT", "value": 2.0},
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


def test_add_columns_node_publishes_table_with_new_default_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    add_task = make_task(
        node_type=ADD_COLUMNS_NODE_TYPE,
        node_run_id="node-run-add-column",
        node_instance_id="add_column",
        input_refs=[input_ref.table_ref_id],
        config={
            "column_name": "status",
            "default_value": "new",
            "data_type": "TEXT",
        },
    )

    add_result = executor.execute(add_task)

    assert add_result.status == NodeResultStatus.SUCCEEDED
    assert add_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 2
    assert [field.name for field in input_ref.schema] == ["row_id", "amount"]
    output_ref = registry.get(add_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "add_column_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "status": "new"},
        {"row_id": 2, "amount": 2.0, "status": "new"},
    ]


def test_delete_columns_node_publishes_table_without_selected_columns(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    delete_task = make_task(
        node_type=DELETE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-delete-columns",
        node_instance_id="delete_columns",
        input_refs=[input_ref.table_ref_id],
        config={"columns": ["amount"]},
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    assert delete_result.output_refs != generate_result.output_refs
    assert [field.name for field in input_ref.schema] == ["row_id", "amount", "label"]
    output_ref = registry.get(delete_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "delete_columns_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "label"]
    assert [field.ordinal for field in output_ref.schema] == [0, 1]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
    ]


def test_save_memory_table_node_outputs_current_ref_and_auxiliary_memory_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider, memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    save_task = make_task(
        node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
        node_run_id="node-run-save-memory",
        node_instance_id="save_memory",
        input_refs=[input_ref.table_ref_id],
        config={"table_name": "scratch", "mode": "overwrite"},
    )

    save_result = executor.execute(save_task)

    assert save_result.status == NodeResultStatus.SUCCEEDED
    assert save_result.output_refs[0] == input_ref.table_ref_id
    assert len(save_result.output_refs) == 2
    memory_ref = registry.get(save_result.output_refs[1])
    assert memory_ref.provider_id == MEMORY_PROVIDER_ID
    assert memory_ref.storage_kind == TableStorageKind.MEMORY
    assert memory_ref.role == TableRole.AUXILIARY
    assert memory_ref.logical_table_id == "scratch"
    assert provider.count_rows(input_ref) == 2
    assert memory_provider.count_rows(memory_ref) == 2
    assert memory_provider.read_rows(
        memory_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    ) == [
        {"row_id": 1, "amount": 1.0},
        {"row_id": 2, "amount": 2.0},
    ]


def test_add_columns_node_returns_validation_error_for_duplicate_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    add_task = make_task(
        node_type=ADD_COLUMNS_NODE_TYPE,
        node_run_id="node-run-add-column",
        node_instance_id="add_column",
        input_refs=generate_result.output_refs,
        config={
            "column_name": "amount",
            "default_value": "new",
            "data_type": "TEXT",
        },
    )

    result = executor.execute(add_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field already exists" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_filter_rows_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    filter_task = make_task(
        node_type=FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-filter",
        node_instance_id="filter",
        input_refs=generate_result.output_refs,
        config={"field": "missing", "operator": "EQ", "value": 1},
    )

    result = executor.execute(filter_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_delete_columns_node_returns_validation_error_for_missing_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    delete_task = make_task(
        node_type=DELETE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-delete-columns",
        node_instance_id="delete_columns",
        input_refs=generate_result.output_refs,
        config={"columns": ["missing"]},
    )

    result = executor.execute(delete_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2
