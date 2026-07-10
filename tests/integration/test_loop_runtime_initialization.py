from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_event_sink import DatabaseEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.node_executor import BuiltinTableNodeExecutor
from flowweaver.nodes.builtin_table import LOOP_JUDGE_NODE_TYPE
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
from flowweaver.workflow_process.controller import initialize_node_runs
from flowweaver.workflow_process.dag import WorkflowDag, build_workflow_dag
from flowweaver.workflow_process.loop_runtime_initialization import (
    initialize_enabled_loop_runtime_state,
)
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyStatus,
    NodeTaskManager,
)
from flowweaver.workflow_process.ready_queue import (
    ReadyNodeCandidate,
    collect_ready_node_candidates,
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
                    "node_type": LOOP_JUDGE_NODE_TYPE,
                    "node_version": "1.0",
                    "config": {
                        "loop_id": "orders_loop",
                        "condition_mode": "always_success",
                        "on_success": "continue_loop",
                        "on_fail": "end_loop",
                    },
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


def make_store_provider_registry(
    tmp_path: Path,
) -> tuple[RuntimeStore, SQLiteRuntimeTableProvider, TableProviderRegistry]:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = create_default_table_provider_registry(
        tmp_path / "runtime" / "workflow_runs",
        runtime_provider=provider,
    )
    return store, provider, registry


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


def create_control_output(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
    selected_branch: str,
    details: str = "",
) -> TableRefModel:
    staging = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        output_name=f"control_status_{selected_branch}",
        schema=control_schema(),
    )
    provider.insert_rows(
        staging,
        [
            {
                "signal_type": "loop_decision",
                "selected_branch": selected_branch,
                "actual_control": "false",
                "source_node_id": "loop_judge",
                "target_anchor": "orders_loop",
                "details": details,
            }
        ],
    )
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def create_data_output(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
    output_name: str,
) -> TableRefModel:
    staging = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        output_name=output_name,
        schema=[
            FieldSchemaModel(
                field_id="amount",
                name="amount",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
    )
    provider.insert_rows(staging, [{"amount": 2}])
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def create_manager(
    store: RuntimeStore,
    registry: TableProviderRegistry,
    *,
    definition: WorkflowDefinitionModel,
    dag: WorkflowDag,
) -> NodeTaskManager:
    return NodeTaskManager(
        store=store,
        event_sink=DatabaseEventSink(store),
        dag=dag,
        failure_policy_mode=definition.failure_policy.mode,
        table_provider_registry=registry,
    )


def ready_candidate(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    dag: WorkflowDag,
    node_instance_id: str,
) -> ReadyNodeCandidate:
    matches = [
        candidate
        for candidate in collect_ready_node_candidates(
            store=store,
            workflow_run_id=workflow_run_id,
            dag=dag,
        )
        if candidate.node_run.node_instance_id == node_instance_id
    ]
    assert len(matches) == 1
    return matches[0]


def submit_and_accept_candidate(
    manager: NodeTaskManager,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int,
    candidate: ReadyNodeCandidate,
    config: dict | None = None,
) -> NodeTaskModel:
    task = manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=process_id,
        process_generation=process_generation,
        node_instance_id=candidate.node_run.node_instance_id,
        node_run_id=candidate.node_run.node_run_id,
        input_refs=list(candidate.input_refs),
        config=config,
    )
    assert task is not None
    accepted = manager.accept_task(task_id=task.task_id, executor_id="executor-1")
    assert accepted == task
    return task


def apply_success(
    manager: NodeTaskManager,
    task: NodeTaskModel,
    *,
    output_refs: list[str] | None = None,
) -> None:
    result = NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id="executor-1",
        process_generation=task.process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=output_refs or [],
    )
    applied = manager.apply_result(result)
    assert applied.status == NodeTaskApplyStatus.APPLIED


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
        ("loop_start", "ENTRY"),
        ("loop_judge", "JUDGE"),
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


def test_enabled_loop_runtime_runs_two_iterations_and_releases_exit(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
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
    initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    manager = create_manager(store, registry, definition=definition, dag=dag)
    executor = BuiltinTableNodeExecutor(
        executor_id="executor-1",
        store=store,
        registry=RuntimeDataRegistry(store=store, table_provider=provider),
        table_provider=provider,
    )

    first_entry = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_start",
    )
    first_entry_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=first_entry,
    )
    apply_success(manager, first_entry_task)

    first_body = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="body",
    )
    first_body_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=first_body,
    )
    first_body_output = create_data_output(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=first_body_task.node_run_id,
        output_name="first_body_output",
    )
    apply_success(
        manager,
        first_body_task,
        output_refs=[first_body_output.table_ref_id],
    )

    first_judge = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_judge",
    )
    assert first_judge.input_refs == (first_body_output.table_ref_id,)
    first_judge_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=first_judge,
    )
    continue_result = executor.execute(first_judge_task)
    assert continue_result.status == NodeResultStatus.SUCCEEDED
    continue_ref = store.get_table_ref(continue_result.output_refs[0])
    assert continue_ref is not None
    assert (
        provider.read_rows(continue_ref, offset=0, limit=1)[0]["actual_control"]
        == "false"
    )
    continued = manager.apply_result(continue_result)
    assert continued.status == NodeTaskApplyStatus.APPLIED

    loop = store.get_loop_run_for_workflow_loop(
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
    )
    assert loop is not None
    iterations = store.list_loop_iteration_runs(loop.loop_run_id)
    assert [iteration.iteration_index for iteration in iterations] == [0, 1]
    assert iterations[0].status == LoopIterationRunStatus.SUCCEEDED.value
    assert iterations[1].status == LoopIterationRunStatus.RUNNING.value

    second_entry = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_start",
    )
    assert second_entry.node_run.node_run_id != first_entry.node_run.node_run_id
    second_entry_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=second_entry,
    )
    apply_success(manager, second_entry_task)

    second_body = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="body",
    )
    assert second_body.node_run.node_run_id != first_body.node_run.node_run_id
    second_body_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=second_body,
    )
    second_body_output = create_data_output(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=second_body_task.node_run_id,
        output_name="second_body_output",
    )
    apply_success(
        manager,
        second_body_task,
        output_refs=[second_body_output.table_ref_id],
    )

    second_judge = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_judge",
    )
    assert second_judge.node_run.node_run_id != first_judge.node_run.node_run_id
    assert second_judge.input_refs == (second_body_output.table_ref_id,)
    second_judge_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=second_judge,
        config={
            "loop_id": "orders_loop",
            "condition_mode": "always_success",
            "on_success": "end_loop",
            "on_fail": "end_loop",
        },
    )
    end_result = executor.execute(second_judge_task)
    assert end_result.status == NodeResultStatus.SUCCEEDED
    end_ref = store.get_table_ref(end_result.output_refs[0])
    assert end_ref is not None
    assert (
        provider.read_rows(end_ref, offset=0, limit=1)[0]["actual_control"]
        == "false"
    )
    ended = manager.apply_result(end_result)
    assert ended.status == NodeTaskApplyStatus.APPLIED

    loop = store.get_loop_run(loop.loop_run_id)
    assert loop is not None
    assert loop.status == LoopRunStatus.ENDED.value
    final_iteration_statuses = [
        iteration.status
        for iteration in store.list_loop_iteration_runs(loop.loop_run_id)
    ]
    assert final_iteration_statuses == [
        LoopIterationRunStatus.SUCCEEDED.value,
        LoopIterationRunStatus.SUCCEEDED.value,
    ]
    exit_candidate = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="after_loop",
    )
    exit_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=exit_candidate,
    )
    apply_success(manager, exit_task)

    completed = store.get_workflow_run(workflow_run_id)
    assert completed is not None
    assert completed.status == WorkflowRunStatus.SUCCEEDED.value


def test_enabled_loop_runtime_releases_exit_at_max_iterations(
    tmp_path: Path,
) -> None:
    store, provider, registry = make_store_provider_registry(tmp_path)
    definition_data = enabled_loop_definition().model_dump(mode="json")
    definition_data["control_protocol"]["loop_regions"][0]["max_iterations"] = 1
    definition = WorkflowDefinitionModel.model_validate(definition_data)
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
    initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    manager = create_manager(store, registry, definition=definition, dag=dag)

    entry = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_start",
    )
    entry_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=entry,
    )
    apply_success(manager, entry_task)

    body = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="body",
    )
    body_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=body,
    )
    apply_success(manager, body_task, output_refs=["body-output"])

    judge = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="loop_judge",
    )
    judge_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=judge,
    )
    continue_output = create_control_output(
        store,
        provider,
        workflow_run_id=workflow_run_id,
        node_run_id=judge_task.node_run_id,
        selected_branch="continue_loop",
    )
    apply_success(manager, judge_task, output_refs=[continue_output.table_ref_id])

    loop = store.get_loop_run_for_workflow_loop(
        workflow_run_id=workflow_run_id,
        loop_id="orders_loop",
    )
    assert loop is not None
    assert loop.status == LoopRunStatus.MAX_ITERATIONS_REACHED.value
    assert loop.exit_reason == "max_iterations_reached"
    iterations = store.list_loop_iteration_runs(loop.loop_run_id)
    assert [(item.iteration_index, item.status) for item in iterations] == [
        (0, LoopIterationRunStatus.SUCCEEDED.value)
    ]
    exit_candidate = ready_candidate(
        store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id="after_loop",
    )
    exit_task = submit_and_accept_candidate(
        manager,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        candidate=exit_candidate,
    )
    apply_success(manager, exit_task)

    completed = store.get_workflow_run(workflow_run_id)
    assert completed is not None
    assert completed.status == WorkflowRunStatus.SUCCEEDED.value
