from __future__ import annotations

from io import StringIO

from flowweaver.node_executor import FakeNodeExecutor, NodeExecutorProcess
from flowweaver.node_executor.process import run_node_executor_process
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope, NodeTaskSubmitPayload


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
