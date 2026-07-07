from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import initialize_node_runs
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.loop_runtime_initialization import (
    initialize_enabled_loop_runtime_state,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def enabled_loop_definition() -> WorkflowDefinitionModel:
    return WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "loop_start",
                    "node_type": "core.loop_start",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "body",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "loop_judge",
                    "node_type": "core.loop_judge",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "after_loop",
                    "node_type": "core.after_loop",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "start-to-body",
                    "source_node_id": "loop_start",
                    "source_port": "status",
                    "target_node_id": "body",
                    "target_port": "in",
                },
                {
                    "connection_id": "body-to-judge",
                    "source_node_id": "body",
                    "source_port": "out",
                    "target_node_id": "loop_judge",
                    "target_port": "in",
                },
                {
                    "connection_id": "judge-to-after",
                    "source_node_id": "loop_judge",
                    "source_port": "status",
                    "target_node_id": "after_loop",
                    "target_port": "in",
                },
            ],
            "control_protocol": {
                "mode": "enabled",
                "loop_regions": [
                    {
                        "loop_id": "orders_loop",
                        "start_node_id": "loop_start",
                        "judge_node_id": "loop_judge",
                        "body_node_ids": ["body"],
                        "end_node_id": "after_loop",
                        "max_iterations": 3,
                        "enabled": True,
                    }
                ],
            },
        }
    )


def make_store(tmp_path: Path) -> RuntimeStore:
    metadata_path = tmp_path / "metadata.db"
    migrate(metadata_path)
    return RuntimeStore.from_sqlite_path(metadata_path)


def create_running_workflow(
    store: RuntimeStore,
    definition: WorkflowDefinitionModel,
) -> tuple[str, str, int]:
    workflow = store.create_workflow_definition(
        name="Loop runtime initialization workflow",
        definition=definition.model_dump(mode="json"),
        workflow_id="workflow-loop-runtime-initialization",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-loop-runtime-initialization",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-loop-runtime-initialization",
    )
    assert process is not None
    claimed = store.get_workflow_run(run.workflow_run_id)
    assert claimed is not None
    running = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=claimed.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
        owner_process_id=process.process_id,
        process_generation=process.process_generation,
    )
    assert running is not None
    return run.workflow_run_id, process.process_id, process.process_generation


def test_enabled_loop_runtime_initialization_is_idempotent(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    definition = enabled_loop_definition()
    workflow_run_id, process_id, process_generation = create_running_workflow(
        store,
        definition,
    )
    dag = build_workflow_dag(definition)
    initialize_node_runs(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )

    first = initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    second = initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )

    loop = store.get_loop_run_for_workflow_loop(
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
    )
    assert loop is not None
    iterations = store.list_loop_iteration_runs(loop.loop_run_id)
    assert first.loop_runs_seen == 1
    assert first.loop_runs_started == 1
    assert first.first_iteration_node_links_added == 3
    assert second.loop_runs_seen == 1
    assert second.loop_runs_started == 0
    assert second.first_iteration_node_links_added == 0
    assert loop.status == LoopRunStatus.RUNNING.value
    iteration_statuses = [
        (iteration.iteration_index, iteration.status) for iteration in iterations
    ]
    assert iteration_statuses == [(0, LoopIterationRunStatus.RUNNING.value)]
    links = store.list_loop_iteration_node_runs(iterations[0].loop_iteration_id)
    assert [(link.node_instance_id, link.role) for link in links] == [
        ("body", "BODY"),
        ("loop_judge", "JUDGE"),
        ("loop_start", "ENTRY"),
    ]
    node_statuses = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(workflow_run_id)
    }
    assert node_statuses == {
        "after_loop": NodeRunStatus.WAITING_DEPENDENCY.value,
        "body": NodeRunStatus.WAITING_DEPENDENCY.value,
        "loop_judge": NodeRunStatus.WAITING_DEPENDENCY.value,
        "loop_start": NodeRunStatus.READY.value,
    }


def test_preview_control_protocol_does_not_initialize_loop_runtime(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    enabled = enabled_loop_definition().model_dump(mode="json")
    enabled["control_protocol"]["mode"] = "preview"
    enabled["control_protocol"]["loop_regions"][0]["enabled"] = False
    definition = WorkflowDefinitionModel.model_validate(enabled)
    workflow_run_id, process_id, process_generation = create_running_workflow(
        store,
        definition,
    )
    dag = build_workflow_dag(definition)
    initialize_node_runs(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )

    summary = initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )

    assert summary.loop_runs_seen == 0
    assert store.list_loop_runs(workflow_run_id) == []
