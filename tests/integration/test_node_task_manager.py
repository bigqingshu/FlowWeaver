from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_event_sink import DatabaseEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.node_executor import FakeNodeExecutor
from flowweaver.protocols.enums import (
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import initialize_node_runs
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyStatus,
    NodeTaskManager,
    NodeTaskTimeoutStatus,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def linear_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
                "config": {"rows": 3},
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


def diamond_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {"node_instance_id": "a", "node_type": "core.a", "node_version": "1.0"},
            {"node_instance_id": "b", "node_type": "core.b", "node_version": "1.0"},
            {"node_instance_id": "c", "node_type": "core.c", "node_version": "1.0"},
            {"node_instance_id": "d", "node_type": "core.d", "node_version": "1.0"},
        ],
        "connections": [
            {
                "connection_id": "ab",
                "source_node_id": "a",
                "source_port": "out",
                "target_node_id": "b",
                "target_port": "in",
            },
            {
                "connection_id": "ac",
                "source_node_id": "a",
                "source_port": "out",
                "target_node_id": "c",
                "target_port": "in",
            },
            {
                "connection_id": "bd",
                "source_node_id": "b",
                "source_port": "out",
                "target_node_id": "d",
                "target_port": "in",
            },
            {
                "connection_id": "cd",
                "source_node_id": "c",
                "source_port": "out",
                "target_node_id": "d",
                "target_port": "in",
            },
        ],
    }


def create_running_process(store: RuntimeStore, definition: dict):
    workflow = store.create_workflow_definition(
        name="Node task workflow",
        definition=definition,
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    claimed_run = store.get_workflow_run(run.workflow_run_id)
    assert claimed_run is not None
    store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=claimed_run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
        owner_process_id=process.process_id,
        process_generation=process.process_generation,
    )
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition))
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    manager = NodeTaskManager(
        store=store,
        event_sink=DatabaseEventSink(store),
        dag=dag,
    )
    return run, process, manager


def submit_and_accept(
    store: RuntimeStore,
    manager: NodeTaskManager,
    *,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    node_instance_id: str,
    executor_id: str = "executor-1",
    timeout_seconds: int = 60,
):
    task = manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=workflow_process_id,
        process_generation=process_generation,
        node_instance_id=node_instance_id,
        timeout_seconds=timeout_seconds,
    )
    assert task is not None
    accepted = manager.accept_task(task_id=task.task_id, executor_id=executor_id)
    assert accepted == task
    node_run = store.get_node_run(task.node_run_id)
    assert node_run is not None
    assert node_run.status == "RUNNING"
    assert node_run.executor_id == executor_id
    assert node_run.started_at is not None
    return task


def test_ready_node_submission_and_executor_acceptance(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())

    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )

    assert task.workflow_process_id == process.process_id
    assert task.process_generation == 1
    assert task.input_refs == []
    assert task.config == {"rows": 3}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "NODE_QUEUED",
        "NODE_STARTED",
    ]


def test_success_result_is_idempotent_and_advances_downstream(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )
    result = FakeNodeExecutor(
        executor_id="executor-1",
        result_id="duplicate-result",
    ).execute(task)

    first = manager.apply_result(result)
    event_count = len(store.list_runtime_events())
    source = store.get_node_run(task.node_run_id)
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    duplicate = FakeNodeExecutor(
        executor_id="executor-1",
        result_id=result.result_id,
        node_run_id="tampered-node-run",
    ).execute(task)
    second = manager.apply_result(duplicate)
    source_after_duplicate = store.get_node_run(task.node_run_id)
    transform_after_duplicate = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )

    assert first.status == NodeTaskApplyStatus.APPLIED
    assert second.status == NodeTaskApplyStatus.ALREADY_APPLIED
    assert second.node_run_id == result.node_run_id
    assert store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    ) == result
    assert source is not None
    assert source.status == "SUCCEEDED"
    assert transform is not None
    assert transform.status == "READY"
    assert source_after_duplicate is not None
    assert source_after_duplicate.state_version == source.state_version
    assert transform_after_duplicate is not None
    assert transform_after_duplicate.state_version == transform.state_version
    assert len(store.list_runtime_events()) == event_count


def test_stale_and_mismatched_results_are_rejected(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )
    event_count = len(store.list_runtime_events())
    node_before_rejections = store.get_node_run(task.node_run_id)
    assert node_before_rejections is not None

    stale_attempt = manager.apply_result(
        FakeNodeExecutor(
            executor_id="executor-1",
            result_id="attempt-result",
            attempt=0,
        ).execute(task)
    )
    stale_generation = manager.apply_result(
        FakeNodeExecutor(
            executor_id="executor-1",
            result_id="generation-result",
            process_generation=0,
        ).execute(task)
    )
    wrong_executor = manager.apply_result(
        FakeNodeExecutor(
            executor_id="old",
            result_id="executor-result",
        ).execute(task)
    )

    assert stale_attempt.status == NodeTaskApplyStatus.REJECTED_STALE_ATTEMPT
    assert stale_generation.status == NodeTaskApplyStatus.REJECTED_STALE_GENERATION
    assert wrong_executor.status == NodeTaskApplyStatus.REJECTED_EXECUTOR_MISMATCH
    assert store.get_node_task_result(
        task_id=task.task_id,
        result_id="attempt-result",
    ) is None
    assert store.get_node_task_result(
        task_id=task.task_id,
        result_id="generation-result",
    ) is None
    assert store.get_node_task_result(
        task_id=task.task_id,
        result_id="executor-result",
    ) is None
    node_after_rejections = store.get_node_run(task.node_run_id)
    assert node_after_rejections is not None
    assert node_after_rejections.status == "RUNNING"
    assert node_after_rejections.state_version == node_before_rejections.state_version
    assert len(store.list_runtime_events()) == event_count


def test_task_heartbeat_and_progress_update_node_runtime_state(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )

    heartbeat = manager.record_task_heartbeat(
        task,
        executor_id="executor-1",
        attempt=task.attempt,
    )
    progress = manager.record_task_progress(
        task,
        executor_id="executor-1",
        progress=0.5,
        current_stage="halfway",
        metrics={"rows": 10},
    )
    stale_progress = manager.record_task_progress(
        task,
        executor_id="old-executor",
        progress=0.9,
        current_stage="stale",
    )

    loaded = store.get_node_run(task.node_run_id)
    assert heartbeat is not None
    assert progress is not None
    assert stale_progress is None
    assert loaded is not None
    assert loaded.status == "RUNNING"
    assert loaded.last_heartbeat is not None
    assert loaded.progress == 0.5
    assert loaded.current_stage == "halfway"
    assert [event.event_type for event in store.list_runtime_events()] == [
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_PROGRESS",
    ]
    assert store.list_runtime_events()[-1].payload == {
        "process_id": process.process_id,
        "task_id": task.task_id,
        "executor_id": "executor-1",
        "node_instance_id": "source",
        "progress": 0.5,
        "current_stage": "halfway",
        "metrics": {"rows": 10},
    }


def test_node_task_manager_does_not_timeout_before_deadline(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
        timeout_seconds=30,
    )
    node_run = store.get_node_run(task.node_run_id)
    assert node_run is not None
    assert node_run.started_at is not None
    event_count = len(store.list_runtime_events())

    result = manager.mark_timed_out_task(
        task,
        now=node_run.started_at + timedelta(seconds=29),
    )

    assert result.status == NodeTaskTimeoutStatus.NOT_TIMED_OUT
    loaded_node = store.get_node_run(task.node_run_id)
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)
    assert loaded_node is not None
    assert loaded_workflow is not None
    assert loaded_node.status == NodeRunStatus.RUNNING.value
    assert loaded_workflow.status == WorkflowRunStatus.RUNNING.value
    assert len(store.list_runtime_events()) == event_count


@pytest.mark.parametrize(
    "active_status",
    [NodeRunStatus.RUNNING, NodeRunStatus.LONG_RUNNING],
)
def test_node_task_manager_marks_active_task_timed_out_and_fails_workflow(
    tmp_path: Path,
    active_status: NodeRunStatus,
) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
        timeout_seconds=5,
    )
    node_run = store.get_node_run(task.node_run_id)
    assert node_run is not None
    if active_status == NodeRunStatus.LONG_RUNNING:
        node_run = store.update_node_run_status(
            task.node_run_id,
            NodeRunStatus.LONG_RUNNING,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[NodeRunStatus.RUNNING],
            owner_process_id=process.process_id,
            process_generation=process.process_generation,
        )
    assert node_run is not None
    assert node_run.started_at is not None
    timed_out_at = node_run.started_at + timedelta(
        seconds=task.timeout_seconds + 1
    )

    result = manager.mark_timed_out_task(task, now=timed_out_at)
    late_success = FakeNodeExecutor(executor_id="executor-1").execute(task)
    late_apply = manager.apply_result(late_success)

    loaded_node = store.get_node_run(task.node_run_id)
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)
    assert result.status == NodeTaskTimeoutStatus.TIMED_OUT
    assert loaded_node is not None
    assert loaded_workflow is not None
    assert loaded_node.status == NodeRunStatus.TIMED_OUT.value
    assert loaded_node.finished_at == timed_out_at
    assert loaded_node.error is not None
    assert loaded_node.error["task_id"] == task.task_id
    assert loaded_workflow.status == WorkflowRunStatus.FAILED.value
    assert loaded_workflow.finished_at == timed_out_at
    assert late_apply.status == NodeTaskApplyStatus.REJECTED_NODE_TERMINAL
    assert store.get_node_task_result(
        task_id=task.task_id,
        result_id=late_success.result_id,
    ) is None
    assert [event.event_type for event in store.list_runtime_events()][-2:] == [
        "NODE_TIMEOUT",
        "WORKFLOW_FAILED",
    ]


def test_node_task_manager_does_not_timeout_terminal_node(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )
    node_run = store.get_node_run(task.node_run_id)
    assert node_run is not None
    assert node_run.started_at is not None
    success = FakeNodeExecutor(executor_id="executor-1").execute(task)
    assert manager.apply_result(success).status == NodeTaskApplyStatus.APPLIED
    event_count = len(store.list_runtime_events())

    result = manager.mark_timed_out_task(
        task,
        now=node_run.started_at + timedelta(seconds=task.timeout_seconds + 1),
    )

    loaded_node = store.get_node_run(task.node_run_id)
    assert result.status == NodeTaskTimeoutStatus.REJECTED_NODE_NOT_RUNNING
    assert loaded_node is not None
    assert loaded_node.status == NodeRunStatus.SUCCEEDED.value
    assert len(store.list_runtime_events()) == event_count


def test_late_result_cannot_revive_terminal_node(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )
    executor = FakeNodeExecutor(executor_id="executor-1")
    first = executor.execute(task)
    assert manager.apply_result(first).status == NodeTaskApplyStatus.APPLIED
    event_count = len(store.list_runtime_events())
    terminal_node = store.get_node_run(task.node_run_id)
    assert terminal_node is not None
    late = executor.execute(task).model_copy(update={"result_id": "late-result"})

    rejected = manager.apply_result(late)

    assert rejected.status == NodeTaskApplyStatus.REJECTED_NODE_TERMINAL
    assert store.get_node_task_result(
        task_id=task.task_id,
        result_id="late-result",
    ) is None
    node_after_late_result = store.get_node_run(task.node_run_id)
    assert node_after_late_result is not None
    assert node_after_late_result.status == "SUCCEEDED"
    assert node_after_late_result.state_version == terminal_node.state_version
    assert len(store.list_runtime_events()) == event_count


def test_failed_result_marks_node_and_workflow_failed(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, linear_definition())
    task = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
    )
    result = FakeNodeExecutor(
        executor_id="executor-1",
        status=NodeResultStatus.FAILED,
        error={"message": "failed"},
    ).execute(task)

    applied = manager.apply_result(result)

    assert applied.status == NodeTaskApplyStatus.APPLIED
    assert store.get_node_run(task.node_run_id).status == "FAILED"
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    ) == result
    assert [event.event_type for event in store.list_runtime_events()][-2:] == [
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_fork_and_join_dag_waits_for_all_upstreams(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, manager = create_running_process(store, diamond_definition())
    executor = FakeNodeExecutor(executor_id="executor-1")
    task_a = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="a",
    )
    assert manager.apply_result(executor.execute(task_a)).status == (
        NodeTaskApplyStatus.APPLIED
    )
    assert {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    } == {"a": "SUCCEEDED", "b": "READY", "c": "READY", "d": "WAITING_DEPENDENCY"}

    task_b = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="b",
    )
    task_c = submit_and_accept(
        store,
        manager,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="c",
    )
    assert manager.apply_result(executor.execute(task_b)).status == (
        NodeTaskApplyStatus.APPLIED
    )
    assert store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="d",
    ).status == "WAITING_DEPENDENCY"
    assert manager.apply_result(executor.execute(task_c)).status == (
        NodeTaskApplyStatus.APPLIED
    )

    join = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="d",
    )
    assert join is not None
    assert join.status == "READY"
