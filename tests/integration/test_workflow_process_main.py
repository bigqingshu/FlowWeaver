from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import IPCEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.node_executor import FakeNodeExecutor, SubprocessNodeExecutorIpcClient
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


def test_workflow_process_executes_ready_nodes_with_fake_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Fake executor workflow",
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
    assert {node.executor_id for node in node_runs} == {"local-node-executor"}
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

    def create_executor(_task: NodeTaskModel) -> SubprocessNodeExecutorIpcClient:
        executor = SubprocessNodeExecutorIpcClient(
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
    finally:
        for executor in executors:
            executor.close()

    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert len(executors) == 1
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
