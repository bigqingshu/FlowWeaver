from __future__ import annotations

import sys
from textwrap import dedent
from threading import Event, Thread

from flowweaver.node_executor import (
    DELAY_TEST_NODE_TYPE,
    FAULT_MODE_PROCESS_EXIT,
    FAULT_TEST_NODE_TYPE,
    FakeNodeExecutor,
    LocalNodeExecutorIpcClient,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.node_executor.runtime_logger import NodeTaskLogger
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


def background_fast_feedback_policy() -> ResolvedRuntimeFeedbackPolicyModel:
    return ResolvedRuntimeFeedbackPolicyModel.model_validate(
        {
            "telemetry": {
                "log_level": "WARN",
                "event_level": "basic",
                "event_rate_limit_per_second": 10,
                "progress_enabled": False,
                "progress_interval_seconds": 5,
            },
            "diagnostics": {
                "capture_error_context": True,
                "include_metrics": False,
                "payload_byte_limit": 65536,
                "redact_columns": [],
                "mask_policy": "partial",
            },
        }
    )


def make_task() -> NodeTaskModel:
    return NodeTaskModel(
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


def test_local_node_executor_ipc_client_returns_completed_result() -> None:
    task = make_task()
    executor = LocalNodeExecutorIpcClient(executor_id="executor-1")

    result = executor.execute(task)

    assert result.task_id == task.task_id
    assert result.node_run_id == task.node_run_id
    assert result.executor_id == "executor-1"
    assert result.status == NodeResultStatus.SUCCEEDED


def test_local_node_executor_ipc_client_returns_failed_result() -> None:
    class RaisingExecutor:
        executor_id = "executor-1"

        def execute(self, _task: NodeTaskModel) -> NodeTaskResultModel:
            raise RuntimeError("boom")

    task = make_task()
    executor = LocalNodeExecutorIpcClient(
        executor_id="executor-1",
        executor_factory=lambda _task: RaisingExecutor(),
    )

    result = executor.execute(task)

    assert result.task_id == task.task_id
    assert result.node_run_id == task.node_run_id
    assert result.executor_id == "executor-1"
    assert result.status == NodeResultStatus.FAILED
    assert result.error == {"message": "boom", "error_type": "RuntimeError"}


def test_local_node_executor_ipc_client_forwards_filtered_task_log() -> None:
    class LoggingExecutor:
        executor_id = "logging-executor"

        def __init__(self) -> None:
            self.runtime_logger: NodeTaskLogger | None = None
            self.emit_results: list[bool] = []

        def set_runtime_logger(self, logger: NodeTaskLogger | None) -> None:
            self.runtime_logger = logger

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            assert self.runtime_logger is not None
            self.emit_results = [
                self.runtime_logger.info("hidden info"),
                self.runtime_logger.warn(
                    "visible warning",
                    context={"row_count": 3},
                ),
            ]
            return FakeNodeExecutor(executor_id=self.executor_id).execute(task)

    task = make_task().model_copy(
        update={"runtime_feedback_policy": background_fast_feedback_policy()}
    )
    emitted: list[IPCEnvelope] = []
    logging_executor = LoggingExecutor()
    executor = LocalNodeExecutorIpcClient(
        executor_id="executor-1",
        executor_factory=lambda _task: logging_executor,
        event_handler=lambda _task, envelope: emitted.append(envelope),
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.SUCCEEDED
    assert logging_executor.emit_results == [False, True]
    assert [event.message_type for event in emitted] == [
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_LOG,
    ]
    assert emitted[1].payload == {
        "level": "WARN",
        "message": "visible warning",
        "logger_name": "flowweaver.nodes.core.source",
        "context": {"row_count": 3},
        "node_instance_id": task.node_instance_id,
        "task_id": task.task_id,
    }


def test_subprocess_node_executor_ipc_client_returns_completed_result() -> None:
    task = make_task()
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="subprocess-executor-1",
        python_executable=sys.executable,
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.task_id == task.task_id
    assert result.node_run_id == task.node_run_id
    assert result.executor_id == "subprocess-executor-1"
    assert result.status == NodeResultStatus.SUCCEEDED


def test_subprocess_node_executor_ipc_client_emits_intermediate_events() -> None:
    task = make_task()
    events: list[IPCEnvelope] = []
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="reporting-executor-1",
        command=_reporting_executor_command(executor_id="reporting-executor-1"),
        event_handler=lambda _task, envelope: events.append(envelope),
        env={},
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.status == NodeResultStatus.SUCCEEDED
    assert [event.message_type for event in events] == [
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_HEARTBEAT,
        IPCMessageType.NODE_TASK_PROGRESS,
    ]
    assert events[1].payload == {
        "executor_id": "reporting-executor-1",
        "task_id": task.task_id,
        "attempt": task.attempt,
    }
    assert events[2].payload == {
        "progress": 0.5,
        "current_stage": "halfway",
        "metrics": {"rows": 10},
    }


def test_subprocess_node_executor_ipc_client_streams_delay_test_node_events() -> None:
    task = make_task().model_copy(
        update={
            "node_type": DELAY_TEST_NODE_TYPE,
            "config": {
                "duration_seconds": 0.02,
                "heartbeat_interval_seconds": 0.005,
                "progress_interval_seconds": 0.005,
            },
        }
    )
    events: list[IPCEnvelope] = []
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="delay-executor-1",
        python_executable=sys.executable,
        event_handler=lambda _task, envelope: events.append(envelope),
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.executor_id == "delay-executor-1"
    assert events[0].message_type == IPCMessageType.NODE_TASK_ACCEPTED
    assert IPCMessageType.NODE_TASK_HEARTBEAT in {
        event.message_type for event in events
    }
    assert IPCMessageType.NODE_TASK_PROGRESS in {
        event.message_type for event in events
    }
    assert events[-1].message_type == IPCMessageType.NODE_TASK_PROGRESS
    assert events[-1].payload["progress"] == 1.0


def test_subprocess_node_executor_filters_background_fast_progress() -> None:
    task = make_task().model_copy(
        update={
            "node_type": DELAY_TEST_NODE_TYPE,
            "config": {
                "duration_seconds": 0.02,
                "heartbeat_interval_seconds": 0.005,
                "progress_interval_seconds": 0.005,
            },
            "runtime_feedback_policy": background_fast_feedback_policy(),
        }
    )
    events: list[IPCEnvelope] = []
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="background-fast-executor-1",
        python_executable=sys.executable,
        event_handler=lambda _task, envelope: events.append(envelope),
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.status == NodeResultStatus.SUCCEEDED
    assert IPCMessageType.NODE_TASK_HEARTBEAT in {
        event.message_type for event in events
    }
    assert IPCMessageType.NODE_TASK_PROGRESS not in {
        event.message_type for event in events
    }


def test_subprocess_node_executor_ipc_client_cancels_delay_test_node() -> None:
    task = make_task().model_copy(
        update={
            "node_type": DELAY_TEST_NODE_TYPE,
            "config": {
                "duration_seconds": 5,
                "heartbeat_interval_seconds": 0.005,
                "progress_interval_seconds": 0.005,
            },
        }
    )
    events: list[IPCEnvelope] = []
    accepted_seen = Event()
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="delay-cancel-executor-1",
        python_executable=sys.executable,
        event_handler=lambda _task, envelope: (
            events.append(envelope),
            accepted_seen.set()
            if envelope.message_type == IPCMessageType.NODE_TASK_ACCEPTED
            else None,
        ),
    )
    results = []
    worker = Thread(target=lambda: results.append(executor.execute(task)))
    worker.start()
    try:
        assert accepted_seen.wait(timeout=5)
        assert executor.request_cancel(task)
        worker.join(timeout=5)
    finally:
        executor.close()

    assert len(results) == 1
    assert results[0].status == NodeResultStatus.CANCELLED
    assert results[0].error == {
        "message": "Node task cancelled",
        "reason": "NODE_TASK_CANCEL_REQUEST",
    }
    assert events[0].message_type == IPCMessageType.NODE_TASK_ACCEPTED


def test_subprocess_node_executor_ipc_client_reports_process_exit_fault() -> None:
    task = make_task().model_copy(
        update={
            "node_type": FAULT_TEST_NODE_TYPE,
            "config": {"mode": FAULT_MODE_PROCESS_EXIT, "exit_code": 7},
        }
    )
    events: list[IPCEnvelope] = []
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="process-exit-fault-executor-1",
        python_executable=sys.executable,
        event_handler=lambda _task, envelope: events.append(envelope),
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["message"] == (
        "Node executor subprocess exited before completing task"
    )
    assert result.error["exit_code"] == 7
    assert [event.message_type for event in events] == [
        IPCMessageType.NODE_TASK_ACCEPTED
    ]


def test_subprocess_node_executor_ipc_client_sends_cancel_request() -> None:
    task = make_task()
    events: list[IPCEnvelope] = []
    accepted_seen = Event()
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="cancel-aware-executor-1",
        command=_cancel_observing_executor_command(
            executor_id="cancel-aware-executor-1"
        ),
        event_handler=lambda _task, envelope: (
            events.append(envelope),
            accepted_seen.set()
            if envelope.message_type == IPCMessageType.NODE_TASK_ACCEPTED
            else None,
        ),
        env={},
    )
    results = []
    worker = Thread(target=lambda: results.append(executor.execute(task)))
    worker.start()
    try:
        assert accepted_seen.wait(timeout=5)
        assert executor.request_cancel(task, reason="test-cancel")
        worker.join(timeout=5)
    finally:
        executor.close()

    assert len(results) == 1
    assert results[0].status == NodeResultStatus.CANCELLED
    assert results[0].error == {
        "message": "cancel request observed",
        "reason": "test-cancel",
    }
    assert [event.message_type for event in events] == [
        IPCMessageType.NODE_TASK_ACCEPTED
    ]


def test_subprocess_node_executor_ipc_client_returns_failed_result_on_eof() -> None:
    task = make_task()
    executor = SubprocessNodeExecutorIpcClient(
        executor_id="exiting-executor-1",
        command=_exiting_executor_command(executor_id="exiting-executor-1"),
        env={},
    )
    try:
        result = executor.execute(task)
    finally:
        executor.close()

    assert result.task_id == task.task_id
    assert result.node_run_id == task.node_run_id
    assert result.executor_id == "exiting-executor-1"
    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["message"] == (
        "Node executor subprocess exited before completing task"
    )
    assert result.error["exit_code"] == 7
    assert "forced executor exit" in result.error["stderr"]


def _reporting_executor_command(*, executor_id: str) -> list[str]:
    script = dedent(
        f"""
        from __future__ import annotations

        import json
        import sys

        timestamp = "2026-01-01T00:00:00+00:00"
        ready = {{
            "protocol_version": "1.0",
            "message_id": "ready-1",
            "message_type": "EXECUTOR_READY",
            "timestamp": timestamp,
            "payload": {{"executor_id": {executor_id!r}}},
        }}
        sys.stdout.write(json.dumps(ready) + "\\n")
        sys.stdout.flush()
        submitted = json.loads(sys.stdin.readline())
        task = submitted["payload"]

        def write(message_type, payload):
            envelope = {{
                "protocol_version": "1.0",
                "message_id": message_type.lower(),
                "message_type": message_type,
                "timestamp": timestamp,
                "workflow_run_id": task["workflow_run_id"],
                "node_run_id": task["node_run_id"],
                "correlation_id": submitted["message_id"],
                "payload": payload,
            }}
            sys.stdout.write(json.dumps(envelope) + "\\n")
            sys.stdout.flush()

        write(
            "NODE_TASK_ACCEPTED",
            {{
                "executor_id": {executor_id!r},
                "task_id": task["task_id"],
                "node_run_id": task["node_run_id"],
            }},
        )
        write(
            "NODE_TASK_HEARTBEAT",
            {{
                "executor_id": {executor_id!r},
                "task_id": task["task_id"],
                "attempt": task["attempt"],
            }},
        )
        write(
            "NODE_TASK_PROGRESS",
            {{
                "progress": 0.5,
                "current_stage": "halfway",
                "metrics": {{"rows": 10}},
            }},
        )
        write(
            "NODE_TASK_COMPLETED",
            {{
                "result": {{
                    "result_id": "result-1",
                    "task_id": task["task_id"],
                    "node_run_id": task["node_run_id"],
                    "attempt": task["attempt"],
                    "executor_id": {executor_id!r},
                    "process_generation": task["process_generation"],
                    "status": "SUCCEEDED",
                    "output_refs": [],
                    "error": None,
                    "started_at": timestamp,
                    "finished_at": timestamp,
                }}
            }},
        )
        """
    )
    return [sys.executable, "-c", script]


def _exiting_executor_command(*, executor_id: str) -> list[str]:
    script = dedent(
        f"""
        from __future__ import annotations

        import json
        import sys

        ready = {{
            "protocol_version": "1.0",
            "message_id": "ready-1",
            "message_type": "EXECUTOR_READY",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "payload": {{"executor_id": {executor_id!r}}},
        }}
        sys.stdout.write(json.dumps(ready) + "\\n")
        sys.stdout.flush()
        sys.stdin.readline()
        sys.stderr.write("forced executor exit\\n")
        sys.stderr.flush()
        raise SystemExit(7)
        """
    )
    return [sys.executable, "-c", script]


def _cancel_observing_executor_command(*, executor_id: str) -> list[str]:
    script = dedent(
        f"""
        from __future__ import annotations

        import json
        import sys

        timestamp = "2026-01-01T00:00:00+00:00"
        ready = {{
            "protocol_version": "1.0",
            "message_id": "ready-1",
            "message_type": "EXECUTOR_READY",
            "timestamp": timestamp,
            "payload": {{"executor_id": {executor_id!r}}},
        }}
        sys.stdout.write(json.dumps(ready) + "\\n")
        sys.stdout.flush()
        submitted = json.loads(sys.stdin.readline())
        task = submitted["payload"]

        def write(message_type, payload):
            envelope = {{
                "protocol_version": "1.0",
                "message_id": message_type.lower(),
                "message_type": message_type,
                "timestamp": timestamp,
                "workflow_run_id": task["workflow_run_id"],
                "node_run_id": task["node_run_id"],
                "correlation_id": submitted["message_id"],
                "payload": payload,
            }}
            sys.stdout.write(json.dumps(envelope) + "\\n")
            sys.stdout.flush()

        write(
            "NODE_TASK_ACCEPTED",
            {{
                "executor_id": {executor_id!r},
                "task_id": task["task_id"],
                "node_run_id": task["node_run_id"],
            }},
        )
        cancel = json.loads(sys.stdin.readline())
        if cancel["message_type"] != "NODE_TASK_CANCEL_REQUEST":
            raise SystemExit(8)
        result = {{
            "result_id": "cancelled-result-1",
            "task_id": task["task_id"],
            "node_run_id": task["node_run_id"],
            "attempt": task["attempt"],
            "executor_id": {executor_id!r},
            "process_generation": task["process_generation"],
            "status": "CANCELLED",
            "output_refs": [],
            "error": {{
                "message": "cancel request observed",
                "reason": cancel["payload"]["reason"],
            }},
            "started_at": timestamp,
            "finished_at": timestamp,
        }}
        write("NODE_TASK_COMPLETED", {{"result": result}})
        """
    )
    return [sys.executable, "-c", script]
