from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import DatabaseEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import NodeRunStatus, WorkflowRunStatus
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import (
    apply_node_success,
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import build_workflow_dag


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "transform",
                "node_type": "core.transform",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "c1",
                "source_node_id": "source",
                "source_port": "out",
                "target_node_id": "transform",
                "target_port": "in",
            }
        ],
    }


def create_run(store: RuntimeStore):
    workflow = store.create_workflow_definition(
        name="Controller workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition()))
    return run, process, dag


def mark_node_running(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    node_instance_id: str,
) -> None:
    node = store.get_node_run_for_instance(
        workflow_run_id=workflow_run_id,
        node_instance_id=node_instance_id,
    )
    assert node is not None
    queued = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.QUEUED,
        expected_state_version=node.state_version,
    )
    assert queued is not None
    running = store.update_node_run_status(
        queued.node_run_id,
        NodeRunStatus.RUNNING,
        expected_state_version=queued.state_version,
    )
    assert running is not None


def test_controller_initializes_node_runs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)

    initialized = initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    assert {node.node_instance_id: node.status for node in initialized} == {
        "source": NodeRunStatus.READY.value,
        "transform": NodeRunStatus.WAITING_DEPENDENCY.value,
    }
    assert store.list_runtime_events() == []


def test_node_success_advances_downstream_to_ready(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    mark_node_running(
        store,
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )

    result = apply_node_success(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
        node_instance_id="source",
        event_sink=DatabaseEventSink(store),
    )

    assert result.completed_node is not None
    assert result.completed_node.status == NodeRunStatus.SUCCEEDED.value
    assert [node.node_instance_id for node in result.newly_ready_nodes] == [
        "transform"
    ]
    node_runs = store.list_node_runs(run.workflow_run_id)
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": NodeRunStatus.SUCCEEDED.value,
        "transform": NodeRunStatus.READY.value,
    }
    assert [event.event_type for event in store.list_runtime_events()] == [
        "NODE_FINISHED"
    ]


def test_recover_ready_nodes_uses_persisted_state(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    source = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        status=NodeRunStatus.RUNNING,
    )
    store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
        node_type="core.transform",
        status=NodeRunStatus.WAITING_DEPENDENCY,
    )
    store.update_node_run_status(
        source.node_run_id,
        NodeRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=source.state_version,
    )

    recovered = recover_ready_nodes(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    assert [node.node_instance_id for node in recovered] == ["transform"]
    assert recovered[0].status == NodeRunStatus.READY.value


def test_all_successful_nodes_complete_workflow(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    mark_node_running(
        store,
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    apply_node_success(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
        node_instance_id="source",
        event_sink=DatabaseEventSink(store),
    )
    mark_node_running(
        store,
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )

    result = apply_node_success(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
        node_instance_id="transform",
        event_sink=DatabaseEventSink(store),
    )

    assert result.workflow_completed is not None
    assert result.workflow_completed.status == "SUCCEEDED"
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
