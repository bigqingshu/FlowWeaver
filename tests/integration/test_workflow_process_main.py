from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread

from alembic import command
from alembic.config import Config

import flowweaver.workflow_process.main as workflow_process_main
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_event_sink import IPCEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import (
    DELAY_TEST_NODE_TYPE,
    FAULT_MODE_PROCESS_EXIT,
    FAULT_MODE_RAISE_EXCEPTION,
    FAULT_TEST_NODE_TYPE,
    BuiltinTableNodeExecutor,
    FakeNodeExecutor,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.nodes.builtin_table import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.main import run_workflow_process


class InjectedFailingExecutor:
    executor_id = "injected-failing-executor"

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.FAILED,
            error={"message": "injected failure"},
            started_at=now,
            finished_at=now,
        )


class InjectedReportingExecutor:
    executor_id = "injected-reporting-executor"

    def __init__(self) -> None:
        self._event_handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None = None

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if self._event_handler is not None:
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "executor_id": self.executor_id,
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                    },
                ),
            )
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_PROGRESS,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "progress": 0.5,
                        "current_stage": "halfway",
                        "metrics": {"rows": 10},
                    },
                ),
            )
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            started_at=now,
            finished_at=now,
        )


class BlockingReportingExecutor:
    executor_id = "blocking-reporting-executor"

    def __init__(self, *, progress_reported: Event, finish_task: Event) -> None:
        self._event_handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None = None
        self._progress_reported = progress_reported
        self._finish_task = finish_task

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if self._event_handler is not None:
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "executor_id": self.executor_id,
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                    },
                ),
            )
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_PROGRESS,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "progress": 0.25,
                        "current_stage": "streaming",
                        "metrics": {"ticks": 1},
                    },
                ),
            )
        self._progress_reported.set()
        completed = self._finish_task.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=(
                NodeResultStatus.SUCCEEDED
                if completed
                else NodeResultStatus.FAILED
            ),
            error=None if completed else {"message": "test did not release task"},
            started_at=now,
            finished_at=now,
        )


class NodeAwareOutputExecutor:
    executor_id = "node-aware-output-executor"

    def __init__(self, output_refs_by_node: dict[str, list[str]]) -> None:
        self._output_refs_by_node = output_refs_by_node
        self.seen_input_refs_by_node: dict[str, list[str]] = {}

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.seen_input_refs_by_node[task.node_instance_id] = list(task.input_refs)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=list(self._output_refs_by_node.get(task.node_instance_id, [])),
            started_at=now,
            finished_at=now,
        )


class TrackingSubprocessNodeExecutor(SubprocessNodeExecutorIpcClient):
    def __init__(
        self,
        *,
        closed_executor_ids: list[str],
        executor_id: str,
        python_executable: str,
    ) -> None:
        self._closed_executor_ids = closed_executor_ids
        super().__init__(
            executor_id=executor_id,
            python_executable=python_executable,
        )

    def close(self) -> None:
        if self.executor_id not in self._closed_executor_ids:
            self._closed_executor_ids.append(self.executor_id)
        super().close()


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


def empty_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def single_node_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            }
        ],
        "connections": [],
    }


def single_test_node_definition(
    *,
    node_type: str,
    config: dict,
) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "test-node",
                "node_type": node_type,
                "node_version": "1.0",
                "config": config,
            }
        ],
        "connections": [],
    }


def table_ref_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 5,
                    "columns": ["row_id", "amount", "label"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "filter",
                "node_type": FILTER_ROWS_NODE_TYPE,
                "node_version": "1.0",
                "config": {"field": "amount", "operator": "GT", "value": 2.0},
            },
        ],
        "connections": [
            {
                "connection_id": "generate-to-filter",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "filter",
                "target_port": "in",
            }
        ],
    }


def multi_upstream_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source_b",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "source_a",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "merge",
                "node_type": "core.merge",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "b-to-merge",
                "source_node_id": "source_b",
                "source_port": "out",
                "target_node_id": "merge",
                "target_port": "right",
            },
            {
                "connection_id": "a-to-merge",
                "source_node_id": "source_a",
                "source_port": "out",
                "target_node_id": "merge",
                "target_port": "left",
            },
        ],
    }


def test_workflow_process_executes_ready_nodes_with_default_subprocess_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Default executor workflow",
        definition=definition(),
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

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    loaded_process = store.get_workflow_process(process.process_id)
    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert loaded_process is not None
    assert loaded_process.status == "RUNNING"
    assert loaded_process.exit_code is None
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
        "transform": "SUCCEEDED",
    }
    assert {node.executor_id for node in node_runs} == {"subprocess-node-executor"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_passes_upstream_table_refs_to_downstream_task(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-mainloop",
        registry=registry,
        table_provider=provider,
    )
    workflow = store.create_workflow_definition(
        name="TableRef workflow",
        definition=table_ref_definition(),
        workflow_id="workflow-table-ref",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-table-ref",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-table-ref",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    events = store.list_runtime_events()
    queued_events = {
        event.payload["node_instance_id"]: event
        for event in events
        if event.event_type == "NODE_QUEUED"
    }
    generate_task = store.get_node_task(queued_events["generate"].payload["task_id"])
    filter_task = store.get_node_task(queued_events["filter"].payload["task_id"])
    generate_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
    )
    filter_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="filter",
    )
    assert generate_task is not None
    assert filter_task is not None
    assert generate_run is not None
    assert filter_run is not None
    generate_result = store.get_latest_succeeded_node_task_result_for_node_run(
        generate_run.node_run_id
    )
    filter_result = store.get_latest_succeeded_node_task_result_for_node_run(
        filter_run.node_run_id
    )
    assert generate_result is not None
    assert filter_result is not None
    filtered_ref = registry.get(filter_result.output_refs[0])

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert generate_task.input_refs == []
    assert filter_task.input_refs == generate_result.output_refs
    assert len(generate_result.output_refs) == 1
    assert len(filter_result.output_refs) == 1
    filtered_rows = provider.read_rows(
        filtered_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    )
    assert filtered_rows == [
        {"row_id": 3, "amount": 3.0, "label": "label_0_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_0_4"},
        {"row_id": 5, "amount": 5.0, "label": "label_0_5"},
    ]
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_passes_multiple_upstream_table_refs_in_stable_order(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source_b": ["table-b1"],
            "source_a": ["table-a1", "table-a2"],
            "merge": ["merged-table"],
        }
    )
    workflow = store.create_workflow_definition(
        name="Multi upstream TableRef workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-multi-upstream",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-multi-upstream",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-multi-upstream",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert executor.seen_input_refs_by_node["source_a"] == []
    assert executor.seen_input_refs_by_node["source_b"] == []
    assert executor.seen_input_refs_by_node["merge"] == [
        "table-a1",
        "table-a2",
        "table-b1",
    ]


def test_workflow_process_passes_empty_input_refs_when_upstream_has_no_outputs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source": [],
            "transform": ["transform-output"],
        }
    )
    workflow = store.create_workflow_definition(
        name="Empty upstream output workflow",
        definition=definition(),
        workflow_id="workflow-empty-upstream-output",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-empty-upstream-output",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-empty-upstream-output",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert executor.seen_input_refs_by_node == {
        "source": [],
        "transform": [],
    }


def test_workflow_process_reuses_default_executor_for_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    created_executor_ids: list[str] = []
    executed_task_ids: list[str] = []
    closed_executor_ids: list[str] = []

    class TrackingReusableDefaultExecutor:
        def __init__(self) -> None:
            self.executor_id = f"default-reusable-{len(created_executor_ids) + 1}"
            created_executor_ids.append(self.executor_id)

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            executed_task_ids.append(task.task_id)
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                started_at=now,
                finished_at=now,
            )

        def close(self) -> None:
            closed_executor_ids.append(self.executor_id)

    monkeypatch.setattr(
        workflow_process_main,
        "SubprocessNodeExecutorIpcClient",
        TrackingReusableDefaultExecutor,
    )
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reusable default executor workflow",
        definition=definition(),
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

    exit_code = workflow_process_main.run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert created_executor_ids == ["default-reusable-1"]
    assert len(executed_task_ids) == 2
    assert closed_executor_ids == ["default-reusable-1"]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.executor_id for node in node_runs} == {"default-reusable-1"}


def test_workflow_process_runs_single_node_with_subprocess_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Subprocess executor workflow",
        definition=single_node_definition(),
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
    executors: list[SubprocessNodeExecutorIpcClient] = []
    closed_executor_ids: list[str] = []

    def create_executor(_task: NodeTaskModel) -> SubprocessNodeExecutorIpcClient:
        executor = TrackingSubprocessNodeExecutor(
            closed_executor_ids=closed_executor_ids,
            executor_id=f"subprocess-mainloop-{len(executors) + 1}",
            python_executable=sys.executable,
        )
        executors.append(executor)
        return executor

    try:
        exit_code = run_workflow_process(
            store=store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            heartbeat_interval_seconds=0,
            executor_factory=create_executor,
        )
        node_runs = store.list_node_runs(run.workflow_run_id)
        closed_executor_ids_after_run = list(closed_executor_ids)
    finally:
        for executor in executors:
            executor.close()

    assert exit_code == 0
    assert len(executors) == 1
    assert closed_executor_ids_after_run == ["subprocess-mainloop-1"]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
    }
    assert {node.executor_id for node in node_runs} == {"subprocess-mainloop-1"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_runs_delay_test_node_with_default_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Delay test node workflow",
        definition=single_test_node_definition(
            node_type=DELAY_TEST_NODE_TYPE,
            config={
                "duration_seconds": 0.02,
                "heartbeat_interval_seconds": 0.005,
                "progress_interval_seconds": 0.005,
            },
        ),
        workflow_id="workflow-delay-test",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-delay-test",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-delay-test",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    events = store.list_runtime_events()
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert node_run.status == "SUCCEEDED"
    assert node_run.executor_id == "subprocess-node-executor"
    assert node_run.last_heartbeat is not None
    assert node_run.progress == 1.0
    assert node_run.current_stage == "completed"
    assert "NODE_PROGRESS" in [event.event_type for event in events]


def test_workflow_process_marks_raise_exception_fault_node_failed(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Raise exception fault workflow",
        definition=single_test_node_definition(
            node_type=FAULT_TEST_NODE_TYPE,
            config={
                "mode": FAULT_MODE_RAISE_EXCEPTION,
                "message": "expected workflow fault",
            },
        ),
        workflow_id="workflow-raise-fault",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-raise-fault",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-raise-fault",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "FAILED"
    assert node_run.error == {
        "message": "expected workflow fault",
        "error_type": "RuntimeError",
    }
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_marks_process_exit_fault_node_failed(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Process exit fault workflow",
        definition=single_test_node_definition(
            node_type=FAULT_TEST_NODE_TYPE,
            config={"mode": FAULT_MODE_PROCESS_EXIT, "exit_code": 7},
        ),
        workflow_id="workflow-process-exit-fault",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-process-exit-fault",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-exit-fault",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "FAILED"
    assert node_run.error is not None
    assert node_run.error["message"] == (
        "Node executor subprocess exited before completing task"
    )
    assert node_run.error["exit_code"] == 7


def test_workflow_process_records_executor_heartbeat_and_progress(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reporting executor workflow",
        definition=single_node_definition(),
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

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedReportingExecutor(),
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    events = store.list_runtime_events()
    assert exit_code == 0
    assert node_run.status == "SUCCEEDED"
    assert node_run.executor_id == "injected-reporting-executor"
    assert node_run.last_heartbeat is not None
    assert node_run.progress == 0.5
    assert node_run.current_stage == "halfway"
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_PROGRESS",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]
    assert events[3].payload == {
        "process_id": process.process_id,
        "task_id": events[1].payload["task_id"],
        "executor_id": "injected-reporting-executor",
        "node_instance_id": "source",
        "progress": 0.5,
        "current_stage": "halfway",
        "metrics": {"rows": 10},
    }


def test_workflow_process_records_task_events_while_executor_is_still_running(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Streaming executor workflow",
        definition=single_node_definition(),
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
    progress_reported = Event()
    finish_task = Event()
    exit_codes: list[int] = []

    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0,
                executor_factory=lambda _task: BlockingReportingExecutor(
                    progress_reported=progress_reported,
                    finish_task=finish_task,
                ),
            )
        )
    )
    worker.start()
    try:
        assert progress_reported.wait(timeout=5)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        live_process = store.get_workflow_process(process.process_id)

        assert node_run.status == "RUNNING"
        assert node_run.executor_id == "blocking-reporting-executor"
        assert node_run.last_heartbeat is not None
        assert node_run.progress == 0.25
        assert node_run.current_stage == "streaming"
        assert live_process is not None
        assert live_process.last_heartbeat_at is not None
        assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"
        assert exit_codes == []
    finally:
        finish_task.set()
        worker.join(timeout=5)

    assert exit_codes == [0]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"


def test_workflow_process_applies_injected_executor_failure_result(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Injected executor workflow",
        definition=definition(),
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

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedFailingExecutor(),
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    } == {"source": "FAILED", "transform": "WAITING_DEPENDENCY"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_ignores_stale_executor_result_without_failing(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Rejected executor result workflow",
        definition=definition(),
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
    sleep_calls = 0

    def stop_after_ignored_result(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        store.request_workflow_process_cancel(run.workflow_run_id)

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: FakeNodeExecutor(
            result_id="stale-generation-result",
            process_generation=0,
        ),
        sleep_func=stop_after_ignored_result,
    )

    events = store.list_runtime_events()
    queued_event = next(event for event in events if event.event_type == "NODE_QUEUED")
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    node_runs = {
        node.node_instance_id: node
        for node in store.list_node_runs(run.workflow_run_id)
    }

    assert exit_code == 0
    assert sleep_calls == 1
    assert loaded_run is not None
    assert loaded_run.status == "CANCELLED"
    assert loaded_run.error is None
    assert node_runs["source"].status == "RUNNING"
    assert node_runs["source"].error is None
    assert node_runs["transform"].status == "WAITING_DEPENDENCY"
    assert store.get_node_task_result(
        task_id=queued_event.payload["task_id"],
        result_id="stale-generation-result",
    ) is None
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "WORKFLOW_CANCELLED",
    ]


def test_workflow_process_ipc_event_sink_does_not_write_runtime_events(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="IPC event workflow",
        definition=empty_definition(),
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
    event_path = tmp_path / "runtime-events.jsonl"

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        event_sink=IPCEventSink(event_path),
    )

    envelopes = [
        IPCEnvelope.model_validate_json(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
    ]
    assert exit_code == 0
    assert store.list_runtime_events() == []
    assert [envelope.message_type for envelope in envelopes] == [
        IPCMessageType.RUNTIME_EVENT,
        IPCMessageType.RUNTIME_EVENT,
    ]
    assert [envelope.payload["event_type"] for envelope in envelopes] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_FINISHED",
    ]
