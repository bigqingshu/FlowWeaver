from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_event_sink import DatabaseEventSink
from flowweaver.engine.runtime_store import (
    NodeRun,
    RuntimeStore,
    WorkflowRun,
    sqlite_url,
)
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    NodeResultStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.control_signal_interpreter import (
    ControlSignalInterpretationStatus,
    interpret_control_outputs_after_node_success,
)
from flowweaver.workflow_process.controller import initialize_node_runs
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.loop_control import (
    SerialLoopAdvanceStatus,
    start_serial_loop,
)
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyStatus,
    NodeTaskManager,
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


def single_judge_definition() -> dict:
    return {
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


def make_store_provider_registry(
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


def create_running_judge_process(
    store: RuntimeStore,
    registry: TableProviderRegistry,
) -> tuple[WorkflowRun, str, NodeRun, NodeTaskManager]:
    workflow = store.create_workflow_definition(
        name="Loop decision workflow",
        definition=single_judge_definition(),
        workflow_id="workflow-loop-decision",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-loop-decision",
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
    definition = WorkflowDefinitionModel.model_validate(single_judge_definition())
    dag = build_workflow_dag(definition)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    judge = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="judge",
    )
    assert judge is not None
    manager = NodeTaskManager(
        store=store,
        event_sink=DatabaseEventSink(store),
        dag=dag,
        failure_policy_mode=definition.failure_policy.mode,
        table_provider_registry=registry,
    )
    return run, process.process_id, judge, manager


def start_loop_for_judge(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    judge: NodeRun,
) -> str:
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="judge",
        max_iterations=3,
    )
    assert loop is not None
    started = start_serial_loop(store, loop_run_id=loop.loop_run_id)
    assert started.iteration is not None
    linked = store.add_loop_iteration_node_run(
        loop_iteration_id=started.iteration.loop_iteration_id,
        node_run_id=judge.node_run_id,
        role="JUDGE",
    )
    assert linked is not None
    return loop.loop_run_id


def create_control_output(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
    selected_branch: str,
    actual_control: str,
    signal_type: str = "loop_decision",
    details: str = '{"next_input_selector":{"row_index":1}}',
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
                "signal_type": signal_type,
                "selected_branch": selected_branch,
                "actual_control": actual_control,
                "source_node_id": "judge",
                "target_anchor": "orders_loop",
                "details": details,
            }
        ],
    )
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def submit_and_accept_judge(
    store: RuntimeStore,
    manager: NodeTaskManager,
    *,
    run: WorkflowRun,
    process_id: str,
) -> NodeTaskModel:
    process = store.get_workflow_process(process_id)
    assert process is not None
    task = manager.submit_ready_node(
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process_id,
        process_generation=process.process_generation,
        node_instance_id="judge",
    )
    assert task is not None
    accepted = manager.accept_task(task_id=task.task_id, executor_id="executor-1")
    assert accepted == task
    return task


def test_node_success_control_output_creates_next_iteration(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
    run, process_id, judge, manager = create_running_judge_process(store, registry)
    loop_run_id = start_loop_for_judge(
        store,
        workflow_run_id=run.workflow_run_id,
        judge=judge,
    )
    task = submit_and_accept_judge(
        store,
        manager,
        run=run,
        process_id=process_id,
    )
    control_output = create_control_output(
        store,
        provider,
        workflow_run_id=run.workflow_run_id,
        node_run_id=task.node_run_id,
        selected_branch="continue_loop",
        actual_control="true",
    )
    result = NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id="executor-1",
        process_generation=task.process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=[control_output.table_ref_id],
    )

    applied = manager.apply_result(result)
    iterations = store.list_loop_iteration_runs(loop_run_id)

    assert applied.status == NodeTaskApplyStatus.APPLIED
    assert [iteration.iteration_index for iteration in iterations] == [0, 1]
    assert iterations[0].status == LoopIterationRunStatus.SUCCEEDED.value
    assert iterations[1].status == LoopIterationRunStatus.RUNNING.value
    assert iterations[1].input_selector == {"row_index": 1}
    entry_links = store.list_loop_iteration_node_runs(
        iterations[1].loop_iteration_id,
        node_instance_id="loop-start",
        role="ENTRY",
    )
    assert len(entry_links) == 1
    entry_node = store.get_node_run(entry_links[0].node_run_id)
    assert entry_node is not None
    assert entry_node.status == "READY"


def test_control_output_preview_signal_has_no_loop_side_effect(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
    run, _process_id, judge, _manager = create_running_judge_process(store, registry)
    loop_run_id = start_loop_for_judge(
        store,
        workflow_run_id=run.workflow_run_id,
        judge=judge,
    )
    control_output = create_control_output(
        store,
        provider,
        workflow_run_id=run.workflow_run_id,
        node_run_id=judge.node_run_id,
        selected_branch="continue_loop",
        actual_control="false",
    )

    interpreted = interpret_control_outputs_after_node_success(
        store,
        registry,
        workflow_run_id=run.workflow_run_id,
        completed_node=judge,
        output_refs=[control_output.table_ref_id],
    )

    assert (
        interpreted.status == ControlSignalInterpretationStatus.IGNORED_PREVIEW_SIGNAL
    )
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1
    assert (
        store.list_loop_iteration_runs(loop_run_id)[0].status
        == LoopIterationRunStatus.RUNNING.value
    )


def test_control_output_duplicate_interpretation_is_idempotent(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
    run, _process_id, judge, _manager = create_running_judge_process(store, registry)
    loop_run_id = start_loop_for_judge(
        store,
        workflow_run_id=run.workflow_run_id,
        judge=judge,
    )
    control_output = create_control_output(
        store,
        provider,
        workflow_run_id=run.workflow_run_id,
        node_run_id=judge.node_run_id,
        selected_branch="continue_loop",
        actual_control="true",
    )

    first = interpret_control_outputs_after_node_success(
        store,
        registry,
        workflow_run_id=run.workflow_run_id,
        completed_node=judge,
        output_refs=[control_output.table_ref_id],
    )
    second = interpret_control_outputs_after_node_success(
        store,
        registry,
        workflow_run_id=run.workflow_run_id,
        completed_node=judge,
        output_refs=[control_output.table_ref_id],
    )

    assert first.status == ControlSignalInterpretationStatus.LOOP_DECISION_APPLIED
    assert first.advance_result is not None
    assert first.advance_result.status == SerialLoopAdvanceStatus.CREATED_NEXT_ITERATION
    assert second.status == ControlSignalInterpretationStatus.LOOP_DECISION_APPLIED
    assert second.advance_result is not None
    assert second.advance_result.status == SerialLoopAdvanceStatus.ALREADY_ADVANCED
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 2


def test_control_output_non_loop_signal_is_rejected_without_side_effect(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
    run, _process_id, judge, _manager = create_running_judge_process(store, registry)
    loop_run_id = start_loop_for_judge(
        store,
        workflow_run_id=run.workflow_run_id,
        judge=judge,
    )
    control_output = create_control_output(
        store,
        provider,
        workflow_run_id=run.workflow_run_id,
        node_run_id=judge.node_run_id,
        selected_branch="continue_loop",
        actual_control="true",
        signal_type="branch_preview",
    )

    interpreted = interpret_control_outputs_after_node_success(
        store,
        registry,
        workflow_run_id=run.workflow_run_id,
        completed_node=judge,
        output_refs=[control_output.table_ref_id],
    )

    assert interpreted.status == ControlSignalInterpretationStatus.REJECTED_SIGNAL_TYPE
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1
