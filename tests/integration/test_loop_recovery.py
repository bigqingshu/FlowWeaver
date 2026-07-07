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
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag import WorkflowDag, build_workflow_dag
from flowweaver.workflow_process.loop_recovery import (
    recover_serial_loop_runtime_state,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def control_schema() -> list[FieldSchemaModel]:
    fields = [
        "signal_type",
        "selected_branch",
        "actual_control",
        "source_node_id",
        "target_anchor",
        "details",
    ]
    return [
        FieldSchemaModel(
            field_id=field,
            name=field,
            data_type="TEXT",
            nullable=True,
            ordinal=index,
        )
        for index, field in enumerate(fields)
    ]


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


def make_context(
    tmp_path: Path,
) -> tuple[
    RuntimeStore,
    SQLiteRuntimeTableProvider,
    TableProviderRegistry,
    WorkflowDag,
]:
    metadata_path = tmp_path / "metadata.db"
    migrate(metadata_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = create_default_table_provider_registry(
        tmp_path / "runtime" / "workflow_runs",
        runtime_provider=provider,
    )
    return (
        RuntimeStore.from_sqlite_path(metadata_path),
        provider,
        registry,
        build_workflow_dag(loop_definition()),
    )


def create_running_workflow(store: RuntimeStore) -> tuple[str, str, int]:
    workflow = store.create_workflow_definition(
        name="Loop recovery workflow",
        definition=loop_definition().model_dump(mode="json"),
        workflow_id="workflow-loop-recovery",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-loop-recovery",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-loop-recovery",
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


def create_loop_with_judge_result(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    iteration_status: LoopIterationRunStatus,
) -> tuple[str, str, str]:
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="judge",
        max_iterations=3,
        status=LoopRunStatus.RUNNING,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-1",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        status=iteration_status,
    )
    assert iteration is not None
    judge = store.create_node_run(
        workflow_run_id=workflow_run_id,
        node_instance_id="judge",
        node_type="core.loop_judge",
        node_run_id="node-judge-1",
        status=NodeRunStatus.RUNNING,
    )
    task = NodeTaskModel(
        task_id="judge-task-1",
        workflow_run_id=workflow_run_id,
        workflow_process_id="process-loop-recovery",
        process_generation=1,
        node_run_id=judge.node_run_id,
        node_instance_id=judge.node_instance_id,
        node_type=judge.node_type,
        node_version="1.0",
        attempt=judge.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    output = create_control_output(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=judge.node_run_id,
    )
    result = NodeTaskResultModel(
        result_id="judge-result-1",
        task_id=task.task_id,
        node_run_id=judge.node_run_id,
        attempt=judge.attempt,
        executor_id="executor-1",
        process_generation=1,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=[output.table_ref_id],
    )
    store.create_node_task(task)
    succeeded = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=judge.state_version,
        allowed_source_statuses=[NodeRunStatus.RUNNING],
    )
    assert succeeded is not None
    link = store.add_loop_iteration_node_run(
        loop_iteration_id=iteration.loop_iteration_id,
        node_run_id=judge.node_run_id,
        role="JUDGE",
    )
    assert link is not None
    return loop.loop_run_id, iteration.loop_iteration_id, judge.node_run_id


def create_control_output(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
) -> TableRefModel:
    staging = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        output_name="control_status",
        schema=control_schema(),
    )
    provider.insert_rows(
        staging,
        [
            {
                "signal_type": "loop_decision",
                "selected_branch": "continue_loop",
                "actual_control": "true",
                "source_node_id": "judge",
                "target_anchor": "orders_loop",
                "details": '{"next_input_selector":{"row_index":1}}',
            }
        ],
    )
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def test_recovery_interprets_successful_judge_once(tmp_path: Path) -> None:
    store, provider, registry, dag = make_context(tmp_path)
    workflow_run_id, process_id, process_generation = create_running_workflow(store)
    loop_run_id, _iteration_id, _judge_node_run_id = create_loop_with_judge_result(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        iteration_status=LoopIterationRunStatus.RUNNING,
    )

    first = recover_serial_loop_runtime_state(
        store,
        registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )
    second = recover_serial_loop_runtime_state(
        store,
        registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )

    iterations = store.list_loop_iteration_runs(loop_run_id)
    next_iteration = iterations[1]
    entry_links = store.list_loop_iteration_node_runs(
        next_iteration.loop_iteration_id,
        node_instance_id="loop-start",
        role="ENTRY",
    )
    assert first.interpreted_decisions == 1
    assert second.interpreted_decisions == 0
    assert [iteration.iteration_index for iteration in iterations] == [0, 1]
    assert iterations[0].status == LoopIterationRunStatus.SUCCEEDED.value
    assert next_iteration.status == LoopIterationRunStatus.RUNNING.value
    assert next_iteration.input_selector == {"row_index": 1}
    assert len(entry_links) == 1


def test_recovery_finishes_succeeded_iteration_without_next_iteration(
    tmp_path: Path,
) -> None:
    store, provider, registry, dag = make_context(tmp_path)
    workflow_run_id, process_id, process_generation = create_running_workflow(store)
    loop_run_id, _iteration_id, _judge_node_run_id = create_loop_with_judge_result(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        iteration_status=LoopIterationRunStatus.SUCCEEDED,
    )

    summary = recover_serial_loop_runtime_state(
        store,
        registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )

    iterations = store.list_loop_iteration_runs(loop_run_id)
    assert summary.interpreted_decisions == 1
    assert [iteration.iteration_index for iteration in iterations] == [0, 1]


def test_recovery_closes_loop_blocked_by_failed_iteration(tmp_path: Path) -> None:
    store, _provider, registry, dag = make_context(tmp_path)
    workflow_run_id, process_id, process_generation = create_running_workflow(store)
    loop = store.create_loop_run(
        loop_run_id="loop-run-failed",
        workflow_run_id=workflow_run_id,
        loop_id="failed_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="judge",
        max_iterations=3,
        status=LoopRunStatus.RUNNING,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-failed",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        status=LoopIterationRunStatus.FAILED,
    )
    assert iteration is not None

    summary = recover_serial_loop_runtime_state(
        store,
        registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )

    recovered_loop = store.get_loop_run(loop.loop_run_id)
    assert summary.closed_failed_loops == 1
    assert recovered_loop is not None
    assert recovered_loop.status == LoopRunStatus.FAILED.value
