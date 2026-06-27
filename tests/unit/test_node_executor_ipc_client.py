from __future__ import annotations

from flowweaver.node_executor import LocalNodeExecutorIpcClient
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
