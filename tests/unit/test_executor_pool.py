from __future__ import annotations

from threading import Event
from time import monotonic, sleep

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.executor_pool import (
    DispatchedNodeTask,
    ExecutorTaskCompletion,
    ImmediateNodeTaskExecutionPool,
    ManualNodeTaskExecutionPool,
    ThreadedNodeTaskExecutionPool,
)


class FakePoolExecutor:
    executor_id = "fake-pool-executor"

    def __init__(self) -> None:
        self.executed_task_ids: list[str] = []

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.executed_task_ids.append(task.task_id)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[f"{task.node_instance_id}-output"],
            started_at=now,
            finished_at=now,
        )


class BlockingPoolExecutor:
    executor_id = "blocking-pool-executor"

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.started.set()
        self.release.wait(timeout=2)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[f"{task.node_instance_id}-threaded-output"],
            started_at=now,
            finished_at=now,
        )


class RaisingPoolExecutor:
    executor_id = "raising-pool-executor"

    def execute(self, _task: NodeTaskModel) -> NodeTaskResultModel:
        raise RuntimeError("threaded executor exploded")


def make_task(task_id: str = "task-1") -> NodeTaskModel:
    return NodeTaskModel(
        task_id=task_id,
        workflow_run_id="run-1",
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=f"{task_id}-node-run",
        node_instance_id="source",
        node_type="core.source",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )


def make_dispatched_task(task_id: str = "task-1") -> DispatchedNodeTask:
    task = make_task(task_id)
    executor = FakePoolExecutor()
    return DispatchedNodeTask(
        task=task,
        executor=executor,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        executor_id=executor.executor_id,
    )


def make_blocking_dispatched_task(
    task_id: str = "task-1",
) -> tuple[DispatchedNodeTask, BlockingPoolExecutor]:
    task = make_task(task_id)
    executor = BlockingPoolExecutor()
    return (
        DispatchedNodeTask(
            task=task,
            executor=executor,
            node_run_id=task.node_run_id,
            node_instance_id=task.node_instance_id,
            executor_id=executor.executor_id,
        ),
        executor,
    )


def make_raising_dispatched_task(
    task_id: str = "task-1",
) -> DispatchedNodeTask:
    task = make_task(task_id)
    executor = RaisingPoolExecutor()
    return DispatchedNodeTask(
        task=task,
        executor=executor,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        executor_id=executor.executor_id,
    )


def pop_completion_until_available(
    pool: ThreadedNodeTaskExecutionPool,
) -> ExecutorTaskCompletion | None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        completion = pool.pop_completed()
        if completion is not None:
            return completion
        sleep(0.01)
    return None


def test_immediate_node_task_execution_pool_records_completion() -> None:
    task = make_task()
    executor = FakePoolExecutor()
    dispatched = DispatchedNodeTask(
        task=task,
        executor=executor,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        executor_id=executor.executor_id,
    )
    pool = ImmediateNodeTaskExecutionPool()

    submitted = pool.submit(dispatched)
    completion = pool.pop_completed()

    assert submitted is True
    assert executor.executed_task_ids == ["task-1"]
    assert pool.in_flight_count() == 0
    assert completion is not None
    assert completion.dispatched_task == dispatched
    assert completion.result is not None
    assert completion.result.status == NodeResultStatus.SUCCEEDED
    assert completion.result.output_refs == ["source-output"]
    assert pool.pop_completed() is None


def test_threaded_node_task_execution_pool_runs_task_until_completion() -> None:
    dispatched, executor = make_blocking_dispatched_task()
    pool = ThreadedNodeTaskExecutionPool()

    assert pool.submit(dispatched) is True
    assert pool.submit(dispatched) is False
    assert pool.in_flight_count() == 1
    assert executor.started.wait(timeout=1)
    assert pool.pop_completed() is None

    executor.release.set()
    completion = pop_completion_until_available(pool)

    assert pool.in_flight_count() == 0
    assert completion is not None
    assert completion.dispatched_task == dispatched
    assert completion.result is not None
    assert completion.result.status == NodeResultStatus.SUCCEEDED
    assert completion.result.output_refs == ["source-threaded-output"]
    assert pool.pop_completed() is None


def test_threaded_node_task_execution_pool_converts_executor_error_to_failure() -> None:
    dispatched = make_raising_dispatched_task()
    pool = ThreadedNodeTaskExecutionPool()

    assert pool.submit(dispatched) is True
    completion = pop_completion_until_available(pool)

    assert pool.in_flight_count() == 0
    assert completion is not None
    assert completion.dispatched_task == dispatched
    assert completion.result is not None
    assert completion.result.status == NodeResultStatus.FAILED
    assert completion.result.task_id == dispatched.task.task_id
    assert completion.result.node_run_id == dispatched.task.node_run_id
    assert completion.result.executor_id == dispatched.executor_id
    assert completion.result.process_generation == dispatched.task.process_generation
    assert completion.result.error == {
        "message": "threaded executor exploded",
        "error_type": "RuntimeError",
    }
    assert pool.pop_completed() is None


def test_threaded_node_task_execution_pool_rejects_submit_after_close() -> None:
    pool = ThreadedNodeTaskExecutionPool()

    pool.close(timeout_seconds=0)

    assert pool.closed is True
    assert pool.submit(make_dispatched_task()) is False
    assert pool.in_flight_count() == 0
    assert pool.pop_completed() is None


def test_threaded_node_task_execution_pool_close_waits_for_running_task() -> None:
    dispatched, executor = make_blocking_dispatched_task()
    pool = ThreadedNodeTaskExecutionPool()

    assert pool.submit(dispatched) is True
    assert executor.started.wait(timeout=1)
    executor.release.set()
    pool.close(timeout_seconds=1)
    completion = pool.pop_completed()

    assert pool.closed is True
    assert pool.in_flight_count() == 0
    assert completion is not None
    assert completion.dispatched_task == dispatched
    assert completion.result is not None
    assert completion.result.status == NodeResultStatus.SUCCEEDED
    assert pool.submit(make_dispatched_task("task-2")) is False
    assert pool.pop_completed() is None


def test_manual_node_task_execution_pool_tracks_in_flight_completion() -> None:
    dispatched = make_dispatched_task()
    result = NodeTaskResultModel(
        task_id=dispatched.task.task_id,
        node_run_id=dispatched.node_run_id,
        attempt=dispatched.task.attempt,
        executor_id=dispatched.executor_id,
        process_generation=dispatched.task.process_generation,
        status=NodeResultStatus.SUCCEEDED,
    )
    pool = ManualNodeTaskExecutionPool()

    assert pool.submit(dispatched) is True
    assert pool.submit(dispatched) is False
    assert pool.in_flight_count() == 1
    assert pool.complete("missing-task", result) is False
    assert pool.in_flight_count() == 1
    assert pool.complete(dispatched.task.task_id, result) is True
    assert pool.in_flight_count() == 0

    completion = pool.pop_completed()

    assert completion is not None
    assert completion.dispatched_task == dispatched
    assert completion.result == result
    assert pool.pop_completed() is None
