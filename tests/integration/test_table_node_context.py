from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import (
    NodeRunStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetKind,
    default_current_output_target,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def test_publish_output_target_rows_supports_current_memory_and_runtime(
    tmp_path: Path,
) -> None:
    context, task = make_context(tmp_path)
    schema = make_test_schema()

    current_result = context.publish_output_target_rows(
        task,
        target=default_current_output_target("out"),
        output_name="current_output",
        schema=schema,
        rows=[{"row_id": 1, "amount": 2.0}],
    )
    memory_result = context.publish_output_target_rows(
        task,
        target=new_memory_target("memory_copy", "scratch"),
        output_name="unused_memory_output_name",
        schema=schema,
        rows=[{"row_id": 2, "amount": 3.0}],
    )
    runtime_result = context.publish_output_target_rows(
        task,
        target=new_runtime_target("runtime_copy", "runtime_stage"),
        output_name="unused_runtime_output_name",
        schema=schema,
        rows=[{"row_id": 3, "amount": 4.0}],
    )

    assert current_result.affected_rows == 1
    assert current_result.table_ref.role == TableRole.CURRENT
    assert current_result.table_ref.logical_table_id == "current_output"
    assert memory_result.table_ref.storage_kind == TableStorageKind.MEMORY
    assert memory_result.table_ref.logical_table_id == "scratch"
    assert runtime_result.table_ref.storage_kind == TableStorageKind.RUNTIME_SQL
    assert runtime_result.table_ref.logical_table_id == "runtime_stage"
    assert runtime_result.to_summary() == {
        "output_slot": "runtime_copy",
        "target_type": "new_runtime_sql",
        "target_table": "runtime_stage",
        "target_table_ref_id": runtime_result.table_ref.table_ref_id,
        "storage_kind": "RUNTIME_SQL",
        "role": "AUXILIARY",
        "write_mode": "create",
        "affected_rows": 1,
        "target_existed": False,
    }
    assert context.read_all_rows(current_result.table_ref) == [
        {"row_id": 1, "amount": 2.0}
    ]
    assert context.read_all_rows(memory_result.table_ref) == [
        {"row_id": 2, "amount": 3.0}
    ]
    assert context.read_all_rows(runtime_result.table_ref) == [
        {"row_id": 3, "amount": 4.0}
    ]


def test_publish_output_target_rows_rejects_duplicate_new_target(
    tmp_path: Path,
) -> None:
    context, task = make_context(tmp_path)
    schema = make_test_schema()
    target = new_memory_target("memory_copy", "scratch")
    context.publish_output_target_rows(
        task,
        target=target,
        output_name="unused",
        schema=schema,
        rows=[{"row_id": 1, "amount": 2.0}],
    )

    with pytest.raises(
        BuiltinTableNodeValidationError,
        match="output target already exists: scratch",
    ):
        context.publish_output_target_rows(
            task,
            target=target,
            output_name="unused",
            schema=schema,
            rows=[{"row_id": 2, "amount": 3.0}],
        )


def test_replace_output_target_rows_overwrites_existing_targets(
    tmp_path: Path,
) -> None:
    context, task = make_context(tmp_path)
    schema = make_test_schema()
    memory_result = context.publish_output_target_rows(
        task,
        target=new_memory_target("memory_copy", "scratch"),
        output_name="unused_memory_output_name",
        schema=schema,
        rows=[{"row_id": 1, "amount": 2.0}],
    )
    runtime_result = context.publish_output_target_rows(
        task,
        target=new_runtime_target("runtime_copy", "runtime_stage"),
        output_name="unused_runtime_output_name",
        schema=schema,
        rows=[{"row_id": 1, "amount": 2.0}],
    )

    replaced_memory = context.replace_output_target_rows(
        task,
        target=existing_memory_target("memory_copy", "scratch"),
        schema=schema,
        rows=[{"row_id": 2, "amount": 3.0}],
    )
    replaced_runtime = context.replace_output_target_rows(
        task,
        target=existing_runtime_target("runtime_copy", "runtime_stage"),
        schema=schema,
        rows=[{"row_id": 3, "amount": 4.0}],
    )

    assert (
        replaced_memory.table_ref.table_ref_id
        == memory_result.table_ref.table_ref_id
    )
    assert replaced_memory.affected_rows == 1
    assert replaced_memory.target_existed is True
    assert replaced_memory.to_summary()["write_mode"] == "overwrite"
    assert replaced_runtime.table_ref.table_ref_id == (
        runtime_result.table_ref.table_ref_id
    )
    assert context.read_all_rows(replaced_memory.table_ref) == [
        {"row_id": 2, "amount": 3.0}
    ]
    assert context.read_all_rows(replaced_runtime.table_ref) == [
        {"row_id": 3, "amount": 4.0}
    ]


def test_replace_output_target_rows_requires_existing_target(
    tmp_path: Path,
) -> None:
    context, task = make_context(tmp_path)

    with pytest.raises(
        BuiltinTableNodeValidationError,
        match="output target does not exist: missing",
    ):
        context.replace_output_target_rows(
            task,
            target=existing_runtime_target("runtime_copy", "missing"),
            schema=make_test_schema(),
            rows=[{"row_id": 1, "amount": 2.0}],
        )


def make_context(tmp_path: Path) -> tuple[BuiltinTableNodeContext, NodeTaskModel]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Table node context workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="test.node",
        node_run_id="node-run-1",
        status=NodeRunStatus.RUNNING,
    )
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    context = BuiltinTableNodeContext(
        store=store,
        registry=registry,
        table_provider=provider,
        memory_provider=MemoryTableProvider(tables={}),
    )
    task = NodeTaskModel(
        task_id="task-1",
        workflow_run_id=run.workflow_run_id,
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=node.node_run_id,
        node_instance_id=node.node_instance_id,
        node_type=node.node_type,
        node_version="1.0",
        attempt=node.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    return context, task


def make_test_schema() -> list[FieldSchemaModel]:
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
            nullable=True,
            ordinal=1,
        ),
    ]


def new_memory_target(slot: str, table_name: str) -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.NEW_MEMORY,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
        logical_table_id=table_name,
    )


def new_runtime_target(slot: str, table_name: str) -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.NEW_RUNTIME_SQL,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        logical_table_id=table_name,
    )


def existing_memory_target(slot: str, table_name: str) -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.EXISTING_MEMORY,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
        logical_table_id=table_name,
    )


def existing_runtime_target(slot: str, table_name: str) -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.EXISTING_RUNTIME_SQL,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        logical_table_id=table_name,
    )
