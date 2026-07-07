from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.protocols.enums import (
    LoopIterationTableRefRole,
    TableRole,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.loop_input_materialization import (
    LoopInputMaterializationStatus,
    materialize_loop_iteration_input,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_schema() -> list[FieldSchemaModel]:
    return [
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
        FieldSchemaModel(
            field_id="category",
            name="category",
            data_type="TEXT",
            nullable=False,
            ordinal=2,
        ),
    ]


def make_store_and_registry(
    tmp_path: Path,
) -> tuple[RuntimeStore, SQLiteRuntimeTableProvider, TableProviderRegistry]:
    metadata_path = tmp_path / "metadata.db"
    migrate(metadata_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = create_default_table_provider_registry(
        tmp_path / "runtime" / "workflow_runs",
        runtime_provider=provider,
    )
    return RuntimeStore.from_sqlite_path(metadata_path), provider, registry


def create_workflow_run_and_node(
    store: RuntimeStore,
    *,
    workflow_id: str = "workflow-loop-input",
    workflow_run_id: str = "run-loop-input",
    node_run_id: str = "node-source",
) -> tuple[str, str]:
    workflow = store.create_workflow_definition(
        name=f"Loop input workflow {workflow_id}",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id=workflow_id,
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id=f"{workflow_id}-source",
        node_type="builtin.source",
        node_run_id=node_run_id,
    )
    return run.workflow_run_id, node.node_run_id


def create_source_table(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
    rows: list[dict[str, object]],
    output_name: str = "orders",
) -> TableRefModel:
    staging = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        output_name=output_name,
        schema=make_schema(),
        role=TableRole.CURRENT,
    )
    provider.insert_rows(staging, rows)
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def create_loop_iteration(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    source_table_ref_id: str,
    row_index: int,
) -> str:
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="loop-judge",
        max_iterations=3,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-1",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        input_table_ref_id=source_table_ref_id,
        input_selector={"row_index": row_index},
    )
    assert iteration is not None
    return iteration.loop_iteration_id


def test_materialize_loop_iteration_input_creates_one_row_runtime_table(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_and_registry(tmp_path)
    workflow_run_id, node_run_id = create_workflow_run_and_node(store)
    source = create_source_table(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        rows=[
            {"row_id": 1, "amount": 12.5, "category": "skip"},
            {"row_id": 2, "amount": 20.0, "category": "keep"},
            {"row_id": 3, "amount": 31.5, "category": "skip"},
        ],
    )
    loop_iteration_id = create_loop_iteration(
        store,
        workflow_run_id=workflow_run_id,
        source_table_ref_id=source.table_ref_id,
        row_index=1,
    )

    result = materialize_loop_iteration_input(
        store,
        registry,
        loop_iteration_id=loop_iteration_id,
        materializer_node_run_id=node_run_id,
    )
    duplicate = materialize_loop_iteration_input(
        store,
        registry,
        loop_iteration_id=loop_iteration_id,
        materializer_node_run_id=node_run_id,
    )

    assert result.status == LoopInputMaterializationStatus.MATERIALIZED
    assert result.table_ref is not None
    assert duplicate.status == LoopInputMaterializationStatus.ALREADY_MATERIALIZED
    assert duplicate.table_ref == result.table_ref
    assert provider.count_rows(source) == 3
    assert provider.count_rows(result.table_ref) == 1
    assert provider.read_rows(result.table_ref, offset=0, limit=10) == [
        {"row_id": 2, "amount": 20.0, "category": "keep"}
    ]
    assert result.table_ref.opaque_handle["materialized_from"] == {
        "source_table_ref_id": source.table_ref_id,
        "row_index": 1,
    }
    assert [
        link.table_ref_id
        for link in store.list_loop_iteration_table_refs(
            loop_iteration_id,
            role=LoopIterationTableRefRole.INPUT,
        )
    ] == [result.table_ref.table_ref_id]


def test_materialize_loop_iteration_input_rejects_missing_rows(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_and_registry(tmp_path)
    workflow_run_id, node_run_id = create_workflow_run_and_node(store)
    source = create_source_table(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        rows=[],
    )
    loop_iteration_id = create_loop_iteration(
        store,
        workflow_run_id=workflow_run_id,
        source_table_ref_id=source.table_ref_id,
        row_index=0,
    )

    result = materialize_loop_iteration_input(
        store,
        registry,
        loop_iteration_id=loop_iteration_id,
        materializer_node_run_id=node_run_id,
    )

    assert result.status == LoopInputMaterializationStatus.SOURCE_ROW_NOT_FOUND
    assert (
        store.list_loop_iteration_table_refs(
            loop_iteration_id,
            role=LoopIterationTableRefRole.INPUT,
        )
        == []
    )


def test_materialize_loop_iteration_input_rejects_invalid_selector(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_and_registry(tmp_path)
    workflow_run_id, node_run_id = create_workflow_run_and_node(store)
    source = create_source_table(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        rows=[{"row_id": 1, "amount": 12.5, "category": "one"}],
    )
    loop_iteration_id = create_loop_iteration(
        store,
        workflow_run_id=workflow_run_id,
        source_table_ref_id=source.table_ref_id,
        row_index=0,
    )

    result = materialize_loop_iteration_input(
        store,
        registry,
        loop_iteration_id=loop_iteration_id,
        input_selector={"row_index": -1},
        materializer_node_run_id=node_run_id,
    )

    assert result.status == LoopInputMaterializationStatus.INVALID_SELECTOR


def test_materialize_loop_iteration_input_rejects_cross_run_source(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_and_registry(tmp_path)
    workflow_run_id, node_run_id = create_workflow_run_and_node(store)
    other_workflow_run_id, other_node_run_id = create_workflow_run_and_node(
        store,
        workflow_id="workflow-other",
        workflow_run_id="run-other",
        node_run_id="node-other",
    )
    foreign_source = create_source_table(
        store,
        provider,
        workflow_run_id=other_workflow_run_id,
        node_run_id=other_node_run_id,
        rows=[{"row_id": 1, "amount": 12.5, "category": "foreign"}],
    )
    own_source = create_source_table(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        rows=[{"row_id": 1, "amount": 12.5, "category": "own"}],
        output_name="own_orders",
    )
    loop_iteration_id = create_loop_iteration(
        store,
        workflow_run_id=workflow_run_id,
        source_table_ref_id=own_source.table_ref_id,
        row_index=0,
    )

    result = materialize_loop_iteration_input(
        store,
        registry,
        loop_iteration_id=loop_iteration_id,
        source_table_ref_id=foreign_source.table_ref_id,
        materializer_node_run_id=node_run_id,
    )

    assert result.status == LoopInputMaterializationStatus.SOURCE_TABLE_RUN_MISMATCH
