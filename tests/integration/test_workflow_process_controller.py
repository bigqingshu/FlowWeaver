from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

import flowweaver.workflow_process.main as workflow_process_main
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import DatabaseEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import (
    LifecycleStatus,
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeResultStatus,
    NodeRunStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import (
    apply_node_success,
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.ready_queue import (
    collect_ready_node_candidates,
    count_in_flight_node_runs,
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


def make_ready_queue_table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    role: TableRole,
) -> TableRefModel:
    is_memory = role == TableRole.AUXILIARY
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=role,
        storage_kind=(
            TableStorageKind.MEMORY if is_memory else TableStorageKind.RUNTIME_SQL
        ),
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=(
            TableMutability.WORKING_MUTABLE
            if is_memory
            else TableMutability.PUBLISHED_IMMUTABLE
        ),
        provider_id="memory" if is_memory else "sqlite_runtime",
        logical_table_id=table_ref_id,
        opaque_handle=(
            {"memory_table_id": f"{table_ref_id}-memory"}
            if is_memory
            else {
                "database_path": "runtime/run.db",
                "table_name": f"{table_ref_id}_v1",
            }
        ),
        schema=[
            FieldSchemaModel(
                field_id="amount",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{table_ref_id}-fingerprint",
        version=1,
        capabilities={"READ"},
        lifecycle_status=(
            LifecycleStatus.ACTIVE if is_memory else LifecycleStatus.PUBLISHED
        ),
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


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


def definition_with_transform_config(config: dict) -> dict:
    data = definition()
    data["nodes"][1]["config"] = config
    return data


def fork_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {"node_instance_id": "a", "node_type": "core.a", "node_version": "1.0"},
            {"node_instance_id": "b", "node_type": "core.b", "node_version": "1.0"},
            {"node_instance_id": "c", "node_type": "core.c", "node_version": "1.0"},
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


def loop_exit_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "loop_start",
                "node_type": "core.loop_start",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "loop_exit",
                "node_type": "core.after_loop",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "source-to-exit",
                "source_node_id": "source",
                "source_port": "out",
                "target_node_id": "loop_exit",
                "target_port": "in",
            }
        ],
        "control_protocol": {
            "mode": "enabled",
            "loop_regions": [
                {
                    "loop_id": "orders_loop",
                    "start_node_id": "loop_start",
                    "judge_node_id": "loop_start",
                    "body_node_ids": ["loop_start"],
                    "end_node_id": "loop_exit",
                    "enabled": True,
                }
            ],
        },
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


def create_run_from_definition(
    store: RuntimeStore,
    *,
    definition_data: dict,
    workflow_id: str,
    workflow_run_id: str,
    process_id: str,
):
    workflow = store.create_workflow_definition(
        name="Controller workflow",
        definition=definition_data,
        workflow_id=workflow_id,
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )
    store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id=process_id,
    )
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition_data))
    return run, process, dag


def record_successful_node_result(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int,
    node_instance_id: str,
    output_refs: list[str],
) -> None:
    node = store.get_node_run_for_instance(
        workflow_run_id=workflow_run_id,
        node_instance_id=node_instance_id,
    )
    assert node is not None
    running = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.RUNNING,
        expected_state_version=node.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    assert running is not None
    task = NodeTaskModel(
        task_id=f"{node_instance_id}-task-1",
        workflow_run_id=workflow_run_id,
        workflow_process_id=process_id,
        process_generation=process_generation,
        node_run_id=node.node_run_id,
        node_instance_id=node.node_instance_id,
        node_type=node.node_type,
        node_version="1.0",
        attempt=node.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        result_id=f"{node_instance_id}-result-1",
        task_id=task.task_id,
        node_run_id=node.node_run_id,
        attempt=node.attempt,
        executor_id="executor-1",
        process_generation=process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=output_refs,
    )
    store.create_node_task(task)
    succeeded = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        finished_at=result.finished_at,
        expected_state_version=running.state_version,
        allowed_source_statuses=[NodeRunStatus.RUNNING],
    )
    assert succeeded is not None


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
    assert [node.node_instance_id for node in result.newly_ready_nodes] == ["transform"]
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


def test_recover_ready_nodes_releases_loop_exit_after_loop_terminal(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run_from_definition(
        store,
        definition_data=loop_exit_definition(),
        workflow_id="workflow-loop-exit",
        workflow_run_id="run-loop-exit",
        process_id="process-loop-exit",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop_start",
        judge_node_instance_id="loop_start",
        max_iterations=3,
        status=LoopRunStatus.RUNNING,
    )
    assert loop is not None
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    loop_exit = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="loop_exit",
    )
    assert source is not None
    assert loop_exit is not None
    assert loop_exit.status == NodeRunStatus.WAITING_DEPENDENCY.value
    source_done = store.update_node_run_status(
        source.node_run_id,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=source.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    assert source_done is not None

    before_terminal = recover_ready_nodes(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    ended = store.update_loop_run_status(
        loop.loop_run_id,
        LoopRunStatus.ENDED,
        expected_state_version=loop.state_version,
        allowed_source_statuses=[LoopRunStatus.RUNNING],
    )
    after_terminal = recover_ready_nodes(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    assert before_terminal == ()
    assert ended is not None
    assert [node.node_instance_id for node in after_terminal] == ["loop_exit"]
    assert after_terminal[0].status == NodeRunStatus.READY.value


def test_recover_ready_nodes_releases_loop_exit_at_max_iterations(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run_from_definition(
        store,
        definition_data=loop_exit_definition(),
        workflow_id="workflow-loop-max-exit",
        workflow_run_id="run-loop-max-exit",
        process_id="process-loop-max-exit",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-max-1",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop_start",
        judge_node_instance_id="loop_start",
        max_iterations=1,
        status=LoopRunStatus.RUNNING,
    )
    assert loop is not None
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    assert source is not None
    source_done = store.update_node_run_status(
        source.node_run_id,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=source.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    assert source_done is not None
    capped = store.update_loop_run_status(
        loop.loop_run_id,
        LoopRunStatus.MAX_ITERATIONS_REACHED,
        expected_state_version=loop.state_version,
        allowed_source_statuses=[LoopRunStatus.RUNNING],
    )

    recovered = recover_ready_nodes(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    assert capped is not None
    assert [node.node_instance_id for node in recovered] == ["loop_exit"]


def test_ready_queue_uses_dag_order_for_ready_nodes(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Ready queue workflow",
        definition=fork_definition(),
        workflow_id="workflow-ready-queue",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-ready-queue",
    )
    store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-ready-queue",
    )
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(fork_definition()))
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert [item.node_run.node_instance_id for item in candidates] == ["a"]
    assert candidates[0].input_refs == ()
    assert candidates[0].dependency_count == 0


def test_ready_queue_waits_for_upstream_result_refs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    assert source is not None
    assert transform is not None
    store.update_node_run_status(
        source.node_run_id,
        NodeRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=source.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    store.update_node_run_status(
        transform.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=transform.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert candidates == ()


def test_ready_queue_passes_upstream_result_refs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    assert source is not None
    assert transform is not None
    running_source = store.update_node_run_status(
        source.node_run_id,
        NodeRunStatus.RUNNING,
        expected_state_version=source.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    assert running_source is not None
    task = NodeTaskModel(
        task_id="source-task-1",
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_run_id=source.node_run_id,
        node_instance_id=source.node_instance_id,
        node_type=source.node_type,
        node_version="1.0",
        attempt=source.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        result_id="source-result-1",
        task_id=task.task_id,
        node_run_id=source.node_run_id,
        attempt=source.attempt,
        executor_id="executor-1",
        process_generation=process.process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=["table-source-1", "table-source-2"],
    )
    store.create_node_task(task)
    succeeded_source = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        finished_at=result.finished_at,
        expected_state_version=running_source.state_version,
        allowed_source_statuses=[NodeRunStatus.RUNNING],
    )
    assert succeeded_source is not None
    ready_transform = store.update_node_run_status(
        transform.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=transform.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert ready_transform is not None

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert [item.node_run.node_instance_id for item in candidates] == ["transform"]
    assert candidates[0].input_refs == ("table-source-1", "table-source-2")
    assert candidates[0].dependency_count == 1


def test_ready_queue_passes_only_current_table_refs_to_downstream_inputs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    assert source is not None
    assert transform is not None
    current_ref = make_ready_queue_table_ref(
        table_ref_id="table-current",
        workflow_run_id=run.workflow_run_id,
        node_run_id=source.node_run_id,
        role=TableRole.CURRENT,
    )
    auxiliary_ref = make_ready_queue_table_ref(
        table_ref_id="table-auxiliary",
        workflow_run_id=run.workflow_run_id,
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
    )
    store.register_table_ref(current_ref)
    store.register_table_ref(auxiliary_ref)
    record_successful_node_result(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
        output_refs=[current_ref.table_ref_id, auxiliary_ref.table_ref_id],
    )
    source_result = store.get_latest_succeeded_node_task_result_for_node_run(
        source.node_run_id
    )
    ready_transform = store.update_node_run_status(
        transform.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=transform.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert source_result is not None
    assert ready_transform is not None

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert source_result.output_refs == [
        current_ref.table_ref_id,
        auxiliary_ref.table_ref_id,
    ]
    assert [item.node_run.node_instance_id for item in candidates] == ["transform"]
    assert candidates[0].input_refs == (current_ref.table_ref_id,)


def test_ready_queue_resolves_configured_auxiliary_input_source(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    definition_data = definition_with_transform_config(
        {
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
                "output_role": "AUXILIARY",
                "storage_kind": "MEMORY",
                "logical_table_id": "table-auxiliary",
            }
        }
    )
    run, process, dag = create_run_from_definition(
        store,
        definition_data=definition_data,
        workflow_id="workflow-configured-input-source",
        workflow_run_id="run-configured-input-source",
        process_id="process-configured-input-source",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    assert source is not None
    assert transform is not None
    current_ref = make_ready_queue_table_ref(
        table_ref_id="table-current",
        workflow_run_id=run.workflow_run_id,
        node_run_id=source.node_run_id,
        role=TableRole.CURRENT,
    )
    auxiliary_ref = make_ready_queue_table_ref(
        table_ref_id="table-auxiliary",
        workflow_run_id=run.workflow_run_id,
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
    )
    store.register_table_ref(current_ref)
    store.register_table_ref(auxiliary_ref)
    record_successful_node_result(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
        output_refs=[current_ref.table_ref_id, auxiliary_ref.table_ref_id],
    )
    ready_transform = store.update_node_run_status(
        transform.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=transform.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert ready_transform is not None

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert [item.node_run.node_instance_id for item in candidates] == ["transform"]
    assert candidates[0].input_refs == (auxiliary_ref.table_ref_id,)
    assert candidates[0].input_slot_bindings == {
        "in": auxiliary_ref.table_ref_id,
    }
    assert candidates[0].input_resolution_issue is None


def test_configured_input_resolution_error_fails_node_before_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    definition_data = definition_with_transform_config(
        {
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
                "output_role": "AUXILIARY",
                "storage_kind": "MEMORY",
                "logical_table_id": "missing-table",
            }
        }
    )
    workflow = store.create_workflow_definition(
        name="Configured input error workflow",
        definition=definition_data,
        workflow_id="workflow-configured-input-error",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-configured-input-error",
    )
    running_run = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    assert running_run is not None
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-configured-input-error",
    )
    assert process is not None
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition_data))
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    source = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
    )
    transform = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="transform",
    )
    assert source is not None
    assert transform is not None
    current_ref = make_ready_queue_table_ref(
        table_ref_id="table-current",
        workflow_run_id=run.workflow_run_id,
        node_run_id=source.node_run_id,
        role=TableRole.CURRENT,
    )
    store.register_table_ref(current_ref)
    record_successful_node_result(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="source",
        output_refs=[current_ref.table_ref_id],
    )
    ready_transform = store.update_node_run_status(
        transform.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=transform.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert ready_transform is not None
    event_sink = DatabaseEventSink(store)
    task_manager = NodeTaskManager(store=store, event_sink=event_sink, dag=dag)
    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    dispatched = workflow_process_main.dispatch_ready_node_candidate(
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        candidate=candidates[0],
        task_manager=task_manager,
        executor_factory=lambda _task: (_ for _ in ()).throw(
            AssertionError("executor should not be created")
        ),
    )

    transform_after = store.get_node_run(transform.node_run_id)
    workflow_after = store.get_workflow_run(run.workflow_run_id)
    result = store.get_latest_succeeded_node_task_result_for_node_run(
        transform.node_run_id
    )
    assert dispatched is None
    assert candidates[0].input_resolution_issue is not None
    assert transform_after is not None
    assert transform_after.status == NodeRunStatus.FAILED.value
    assert workflow_after is not None
    assert workflow_after.status == WorkflowRunStatus.FAILED.value
    assert result is None
    assert transform_after.error == {
        "code": "INPUT_TABLE_RESOLUTION_FAILED",
        "message": "Input table selector did not match any upstream table",
        "details": {
            "slot": "in",
            "source_node_instance_id": "source",
            "output_role": "AUXILIARY",
            "storage_kind": "MEMORY",
            "logical_table_id": "missing-table",
            "output_slot": None,
        },
    }


def test_ready_queue_counts_in_flight_node_runs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run_from_definition(
        store,
        definition_data=diamond_definition(),
        workflow_id="workflow-in-flight-count",
        workflow_run_id="run-in-flight-count",
        process_id="process-in-flight-count",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    for node_instance_id, status in (
        ("a", NodeRunStatus.RUNNING),
        ("b", NodeRunStatus.LONG_RUNNING),
        ("c", NodeRunStatus.CANCEL_REQUESTED),
    ):
        node = store.get_node_run_for_instance(
            workflow_run_id=run.workflow_run_id,
            node_instance_id=node_instance_id,
        )
        assert node is not None
        if node.status == NodeRunStatus.WAITING_DEPENDENCY.value:
            ready = store.update_node_run_status(
                node.node_run_id,
                NodeRunStatus.READY,
                expected_state_version=node.state_version,
                allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
            )
            assert ready is not None
            node = ready
        updated = store.update_node_run_status(
            node.node_run_id,
            status,
            expected_state_version=node.state_version,
            allowed_source_statuses=[NodeRunStatus.READY],
        )
        assert updated is not None

    assert (
        count_in_flight_node_runs(
            store=store,
            workflow_run_id=run.workflow_run_id,
        )
        == 3
    )


def test_ready_queue_exposes_fork_candidates_after_source_success(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run_from_definition(
        store,
        definition_data=diamond_definition(),
        workflow_id="workflow-ready-fork",
        workflow_run_id="run-ready-fork",
        process_id="process-ready-fork",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    record_successful_node_result(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="a",
        output_refs=["table-a"],
    )
    recovered = recover_ready_nodes(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert [node.node_instance_id for node in recovered] == ["b", "c"]
    assert [item.node_run.node_instance_id for item in candidates] == ["b", "c"]
    assert [item.input_refs for item in candidates] == [("table-a",), ("table-a",)]
    assert [item.dependency_count for item in candidates] == [1, 1]


def test_ready_queue_waits_for_all_join_upstream_result_refs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run_from_definition(
        store,
        definition_data=diamond_definition(),
        workflow_id="workflow-ready-join",
        workflow_run_id="run-ready-join",
        process_id="process-ready-join",
    )
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    for node_instance_id, output_refs in (
        ("a", ["table-a"]),
        ("b", ["table-b"]),
    ):
        node = store.get_node_run_for_instance(
            workflow_run_id=run.workflow_run_id,
            node_instance_id=node_instance_id,
        )
        assert node is not None
        if node.status == NodeRunStatus.WAITING_DEPENDENCY.value:
            ready = store.update_node_run_status(
                node.node_run_id,
                NodeRunStatus.READY,
                expected_state_version=node.state_version,
                allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
            )
            assert ready is not None
        record_successful_node_result(
            store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            node_instance_id=node_instance_id,
            output_refs=output_refs,
        )
    d_node = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="d",
    )
    assert d_node is not None
    ready_d = store.update_node_run_status(
        d_node.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=d_node.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert ready_d is not None

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert candidates == ()

    c_node = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="c",
    )
    assert c_node is not None
    ready_c = store.update_node_run_status(
        c_node.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=c_node.state_version,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    assert ready_c is not None
    record_successful_node_result(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        node_instance_id="c",
        output_refs=["table-c"],
    )

    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )

    assert [item.node_run.node_instance_id for item in candidates] == ["d"]
    assert candidates[0].input_refs == ("table-b", "table-c")
    assert candidates[0].dependency_count == 2


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


def test_workflow_completion_waits_for_loop_terminal_state(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-completion-running",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="source",
        judge_node_instance_id="transform",
        max_iterations=3,
        status=LoopRunStatus.RUNNING,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-running",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        status=LoopIterationRunStatus.RUNNING,
    )
    assert iteration is not None
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

    assert result.workflow_completed is None
    assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"


def test_workflow_completion_waits_for_loop_iterations(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-completion-terminal",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="source",
        judge_node_instance_id="transform",
        max_iterations=3,
        status=LoopRunStatus.ENDED,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-still-running",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        status=LoopIterationRunStatus.RUNNING,
    )
    assert iteration is not None
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

    assert result.workflow_completed is None
    assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"


def test_workflow_completion_allows_successful_terminal_loop(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run, process, dag = create_run(store)
    initialize_node_runs(
        store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        dag=dag,
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-completion-ended",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="source",
        judge_node_instance_id="transform",
        max_iterations=3,
        status=LoopRunStatus.ENDED,
    )
    assert loop is not None
    iteration = store.create_loop_iteration_run(
        loop_iteration_id="loop-iteration-succeeded",
        loop_run_id=loop.loop_run_id,
        iteration_index=0,
        status=LoopIterationRunStatus.SUCCEEDED,
    )
    assert iteration is not None
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
