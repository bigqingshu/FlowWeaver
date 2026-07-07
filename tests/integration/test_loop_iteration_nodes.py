from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import NodeRunStatus, WorkflowRunStatus
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.loop_control import (
    ControlSignal,
    advance_serial_loop_from_decision,
    start_serial_loop,
)
from flowweaver.workflow_process.loop_iteration_nodes import (
    LoopIterationEntryNodeStatus,
    ensure_loop_iteration_entry_node_run,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def loop_definition() -> WorkflowDefinitionModel:
    return WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "loop-start",
                    "node_type": "core.loop_start",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "judge",
                    "node_type": "core.loop_judge",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
        }
    )


def make_store(tmp_path: Path) -> RuntimeStore:
    metadata_path = tmp_path / "metadata.db"
    migrate(metadata_path)
    return RuntimeStore.from_sqlite_path(metadata_path)


def create_running_loop(store: RuntimeStore) -> tuple[str, str, int]:
    workflow = store.create_workflow_definition(
        name="Loop entry workflow",
        definition=loop_definition().model_dump(mode="json"),
        workflow_id="workflow-loop-entry",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-loop-entry",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    claimed = store.get_workflow_run(run.workflow_run_id)
    assert claimed is not None
    store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=claimed.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
        owner_process_id=process.process_id,
        process_generation=process.process_generation,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="judge",
        max_iterations=3,
    )
    assert loop is not None
    started = start_serial_loop(store, loop_run_id=loop.loop_run_id)
    assert started.iteration is not None
    advanced = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop.loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=ControlSignal(
            signal_type="loop_decision",
            selected_branch="continue_loop",
            actual_control=True,
        ),
        next_input_selector={"row_index": 1},
    )
    assert advanced.next_iteration is not None
    return (
        advanced.next_iteration.loop_iteration_id,
        process.process_id,
        process.process_generation,
    )


def test_loop_iteration_entry_node_run_is_created_once(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    dag = build_workflow_dag(loop_definition())
    loop_iteration_id, process_id, process_generation = create_running_loop(store)

    created = ensure_loop_iteration_entry_node_run(
        store,
        dag=dag,
        loop_iteration_id=loop_iteration_id,
        owner_process_id=process_id,
        process_generation=process_generation,
    )
    duplicate = ensure_loop_iteration_entry_node_run(
        store,
        dag=dag,
        loop_iteration_id=loop_iteration_id,
        owner_process_id=process_id,
        process_generation=process_generation,
    )

    assert created.status == LoopIterationEntryNodeStatus.CREATED
    assert created.node_run is not None
    assert created.node_run.node_instance_id == "loop-start"
    assert created.node_run.status == NodeRunStatus.READY.value
    assert duplicate.status == LoopIterationEntryNodeStatus.ALREADY_EXISTS
    assert duplicate.node_run == created.node_run
    assert (
        store.list_loop_iteration_node_runs(
            loop_iteration_id,
            node_instance_id="loop-start",
            role="ENTRY",
        )[0].node_run_id
        == created.node_run.node_run_id
    )


def test_loop_iteration_entry_node_run_reports_missing_dag_node(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    loop_iteration_id, _process_id, _process_generation = create_running_loop(store)
    empty_dag = build_workflow_dag(
        WorkflowDefinitionModel.model_validate(
            {"schema_version": "1.0", "nodes": [], "connections": []}
        )
    )

    result = ensure_loop_iteration_entry_node_run(
        store,
        dag=empty_dag,
        loop_iteration_id=loop_iteration_id,
    )

    assert result.status == LoopIterationEntryNodeStatus.ENTRY_NODE_NOT_FOUND
    assert store.list_loop_iteration_node_runs(loop_iteration_id, role="ENTRY") == []
