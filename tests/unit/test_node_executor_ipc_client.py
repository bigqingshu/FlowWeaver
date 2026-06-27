from __future__ import annotations

import sys
from textwrap import dedent

from flowweaver.node_executor import (
    LocalNodeExecutorIpcClient,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


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
