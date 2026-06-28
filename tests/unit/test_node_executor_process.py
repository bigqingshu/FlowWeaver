from __future__ import annotations

from io import StringIO

from flowweaver.common.time import utc_now
from flowweaver.node_executor import FakeNodeExecutor, NodeExecutorProcess
from flowweaver.node_executor.process import (
    EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE,
    run_node_executor_process,
)
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope, NodeTaskSubmitPayload
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


def make_task() -> NodeTaskSubmitPayload:
    return NodeTaskSubmitPayload(
        task_id="task-1",
        workflow_run_id="run-1",
        workflow_process_id="workflow-process-1",
        process_generation=1,
        node_run_id="node-run-1",
        node_instance_id="source",
        node_type="core.source",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={"rows": 3},
        timeout_seconds=60,
    )


def test_node_executor_process_accepts_and_completes_task_envelope() -> None:
    process = NodeExecutorProcess(executor_id="executor-1")
    task = make_task()
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )

    accepted, completed = process.handle_envelope(envelope)

    assert accepted.message_type == IPCMessageType.NODE_TASK_ACCEPTED
    assert accepted.correlation_id == envelope.message_id
    assert accepted.payload == {
        "executor_id": "executor-1",
        "task_id": task.task_id,
        "node_run_id": task.node_run_id,
    }
    assert completed.message_type == IPCMessageType.NODE_TASK_COMPLETED
    assert completed.correlation_id == envelope.message_id
    assert completed.payload["result"]["task_id"] == task.task_id
    assert completed.payload["result"]["node_run_id"] == task.node_run_id
    assert completed.payload["result"]["executor_id"] == "executor-1"
    assert completed.payload["result"]["status"] == "SUCCEEDED"


def test_node_executor_process_ipc_passes_table_refs_without_inline_rows() -> None:
    task = NodeTaskSubmitPayload(
        task_id="task-table-ref",
        workflow_run_id="run-1",
        workflow_process_id="workflow-process-1",
        process_generation=1,
        node_run_id="node-run-table-ref",
        node_instance_id="filter",
        node_type="FilterRowsNode",
        node_version="1.0",
        attempt=1,
        input_refs=["table-input-1"],
        config={"field": "amount", "operator": "GT", "value": 2.0},
        timeout_seconds=60,
    )

    class RefProducingExecutor:
        executor_id = "executor-1"

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                output_refs=["table-output-1"],
                started_at=now,
                finished_at=now,
            )

    process = NodeExecutorProcess(
        executor_id="executor-1",
        executor_factory=lambda _task: RefProducingExecutor(),
    )
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )

    accepted, completed = process.handle_envelope(envelope)

    assert accepted.message_type == IPCMessageType.NODE_TASK_ACCEPTED
    assert completed.message_type == IPCMessageType.NODE_TASK_COMPLETED
    assert envelope.payload["input_refs"] == ["table-input-1"]
    assert completed.payload["result"]["output_refs"] == ["table-output-1"]
    assert _inline_table_payload_keys(envelope.payload) == set()
    assert _inline_table_payload_keys(completed.payload) == set()


def test_node_executor_process_heartbeat_reports_active_tasks() -> None:
    task = make_task()
    observed_heartbeats: list[IPCEnvelope] = []

    def capture_heartbeat() -> None:
        observed_heartbeats.append(process.heartbeat_envelope())

    class RecordingExecutor:
        executor_id = "executor-1"

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            capture_heartbeat()
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

    process = NodeExecutorProcess(
        executor_id="executor-1",
        executor_factory=lambda _task: RecordingExecutor(),
    )
    idle = process.heartbeat_envelope()
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )

    process.handle_envelope(envelope)
    after_task = process.heartbeat_envelope()

    assert idle.message_type == IPCMessageType.EXECUTOR_HEARTBEAT
    assert idle.payload == {"executor_id": "executor-1", "active_task_ids": []}
    assert observed_heartbeats[0].message_type == IPCMessageType.EXECUTOR_HEARTBEAT
    assert observed_heartbeats[0].payload == {
        "executor_id": "executor-1",
        "active_task_ids": [task.task_id],
    }
    assert after_task.payload == {"executor_id": "executor-1", "active_task_ids": []}


def test_node_executor_process_emits_task_heartbeat_and_progress() -> None:
    task = make_task()
    process_ref: list[NodeExecutorProcess] = []

    class ReportingExecutor:
        executor_id = "executor-1"

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            process_ref[0].emit_task_heartbeat(task)
            process_ref[0].emit_task_progress(
                task,
                progress=0.5,
                current_stage="halfway",
                metrics={"rows": 10},
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

    process = NodeExecutorProcess(
        executor_id="executor-1",
        executor_factory=lambda _task: ReportingExecutor(),
    )
    process_ref.append(process)
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )

    accepted, heartbeat, progress, completed = process.handle_envelope(envelope)

    message_types = [
        item.message_type for item in (accepted, heartbeat, progress, completed)
    ]
    assert message_types == [
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_HEARTBEAT,
        IPCMessageType.NODE_TASK_PROGRESS,
        IPCMessageType.NODE_TASK_COMPLETED,
    ]
    assert heartbeat.correlation_id == envelope.message_id
    assert heartbeat.payload == {
        "executor_id": "executor-1",
        "task_id": task.task_id,
        "attempt": task.attempt,
    }
    assert progress.correlation_id == envelope.message_id
    assert progress.payload == {
        "progress": 0.5,
        "current_stage": "halfway",
        "metrics": {"rows": 10},
    }


def test_node_executor_process_emits_failed_envelope_when_executor_raises() -> None:
    task = make_task()
    process_ref: list[NodeExecutorProcess] = []

    class RaisingExecutor:
        executor_id = "executor-1"

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            process_ref[0].emit_task_heartbeat(task)
            raise RuntimeError("boom")

    process = NodeExecutorProcess(
        executor_id="executor-1",
        executor_factory=lambda _task: RaisingExecutor(),
    )
    process_ref.append(process)
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )

    accepted, heartbeat, failed = process.handle_envelope(envelope)
    after_failure = process.heartbeat_envelope()

    assert [item.message_type for item in (accepted, heartbeat, failed)] == [
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_HEARTBEAT,
        IPCMessageType.NODE_TASK_FAILED,
    ]
    assert failed.correlation_id == envelope.message_id
    assert failed.payload["error_type"] == "RuntimeError"
    assert failed.payload["result"]["task_id"] == task.task_id
    assert failed.payload["result"]["status"] == "FAILED"
    assert failed.payload["result"]["error"] == {
        "message": "boom",
        "error_type": "RuntimeError",
    }
    assert after_failure.payload == {
        "executor_id": "executor-1",
        "active_task_ids": [],
    }


def test_node_executor_process_jsonl_loop_emits_ready_and_failed_result() -> None:
    task = make_task()
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=task.model_dump(mode="json"),
    )
    stdin = StringIO(envelope.model_dump_json() + "\n")
    stdout = StringIO()

    exit_code = run_node_executor_process(
        executor_id="executor-1",
        stdin=stdin,
        stdout=stdout,
        executor_factory=lambda _task: FakeNodeExecutor(
            executor_id="executor-1",
            status=NodeResultStatus.FAILED,
            error={"message": "injected failure"},
        ),
    )

    messages = [
        IPCEnvelope.model_validate_json(line)
        for line in stdout.getvalue().splitlines()
    ]
    assert exit_code == 0
    assert [message.message_type for message in messages] == [
        IPCMessageType.EXECUTOR_READY,
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_COMPLETED,
    ]
    assert messages[0].payload == {"executor_id": "executor-1"}
    assert messages[2].payload["result"]["status"] == "FAILED"
    assert messages[2].payload["result"]["error"] == {
        "message": "injected failure"
    }


def test_node_executor_process_jsonl_loop_returns_nonzero_for_invalid_input() -> None:
    stdin = StringIO("{not-json}\n")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run_node_executor_process(
        executor_id="executor-1",
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )

    messages = [
        IPCEnvelope.model_validate_json(line)
        for line in stdout.getvalue().splitlines()
    ]
    assert exit_code == EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE
    assert [message.message_type for message in messages] == [
        IPCMessageType.EXECUTOR_READY,
    ]
    assert "IPC_INPUT_ERROR" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def _inline_table_payload_keys(value) -> set[str]:
    forbidden_keys = {"table_data", "records", "record_batches", "row_values"}
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden_keys.intersection(value))
        for item in value.values():
            found.update(_inline_table_payload_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_inline_table_payload_keys(item))
    return found
