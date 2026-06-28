from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Protocol

from flowweaver.common.time import utc_now
from flowweaver.node_executor import NodeExecutor
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


@dataclass(frozen=True)
class DispatchedNodeTask:
    task: NodeTaskModel
    executor: NodeExecutor
    node_run_id: str
    node_instance_id: str
    executor_id: str


@dataclass(frozen=True)
class ExecutorTaskCompletion:
    dispatched_task: DispatchedNodeTask
    result: NodeTaskResultModel | None


NodeTaskExecute = Callable[[DispatchedNodeTask], NodeTaskResultModel | None]


class NodeTaskExecutionPool(Protocol):
    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        ...

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        ...

    def in_flight_count(self) -> int:
        ...

    def in_flight_tasks(self) -> tuple[DispatchedNodeTask, ...]:
        ...


class ImmediateNodeTaskExecutionPool:
    def __init__(self, execute_task: NodeTaskExecute | None = None) -> None:
        self._completed: list[ExecutorTaskCompletion] = []
        self._execute_task = execute_task or _execute_directly

    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        result = self._execute_task(dispatched_task)
        self._completed.append(
            ExecutorTaskCompletion(
                dispatched_task=dispatched_task,
                result=result,
            )
        )
        return True

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        if not self._completed:
            return None
        return self._completed.pop(0)

    def in_flight_count(self) -> int:
        return 0

    def in_flight_tasks(self) -> tuple[DispatchedNodeTask, ...]:
        return ()


class ThreadedNodeTaskExecutionPool:
    def __init__(self, execute_task: NodeTaskExecute | None = None) -> None:
        self._completed: Queue[ExecutorTaskCompletion] = Queue()
        self._execute_task = execute_task or _execute_directly
        self._in_flight: dict[str, DispatchedNodeTask] = {}
        self._workers: dict[str, Thread] = {}
        self._closed = False
        self._lock = Lock()

    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        task_id = dispatched_task.task.task_id
        worker = Thread(
            target=self._execute_in_thread,
            args=(task_id, dispatched_task),
            name=f"flowweaver-node-task-pool-{task_id}",
            daemon=True,
        )
        with self._lock:
            if self._closed:
                return False
            if task_id in self._in_flight:
                return False
            self._in_flight[task_id] = dispatched_task
            self._workers[task_id] = worker
            worker.start()
        return True

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def close(self, *, timeout_seconds: float | None = None) -> None:
        with self._lock:
            self._closed = True
            workers = tuple(self._workers.values())
        for worker in workers:
            worker.join(timeout=timeout_seconds)

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        try:
            return self._completed.get_nowait()
        except Empty:
            return None

    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def in_flight_tasks(self) -> tuple[DispatchedNodeTask, ...]:
        with self._lock:
            return tuple(self._in_flight.values())

    def _execute_in_thread(
        self,
        task_id: str,
        dispatched_task: DispatchedNodeTask,
    ) -> None:
        result: NodeTaskResultModel | None = None
        try:
            result = self._execute_task(dispatched_task)
        except Exception as exc:
            result = _failed_task_result(dispatched_task, exc)
        finally:
            with self._lock:
                self._in_flight.pop(task_id, None)
                self._workers.pop(task_id, None)
            self._completed.put(
                ExecutorTaskCompletion(
                    dispatched_task=dispatched_task,
                    result=result,
                )
            )


class ManualNodeTaskExecutionPool:
    def __init__(self) -> None:
        self._in_flight: dict[str, DispatchedNodeTask] = {}
        self._completed: list[ExecutorTaskCompletion] = []

    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        task_id = dispatched_task.task.task_id
        if task_id in self._in_flight:
            return False
        self._in_flight[task_id] = dispatched_task
        return True

    def complete(
        self,
        task_id: str,
        result: NodeTaskResultModel | None,
    ) -> bool:
        dispatched_task = self._in_flight.pop(task_id, None)
        if dispatched_task is None:
            return False
        self._completed.append(
            ExecutorTaskCompletion(
                dispatched_task=dispatched_task,
                result=result,
            )
        )
        return True

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        if not self._completed:
            return None
        return self._completed.pop(0)

    def in_flight_count(self) -> int:
        return len(self._in_flight)

    def in_flight_tasks(self) -> tuple[DispatchedNodeTask, ...]:
        return tuple(self._in_flight.values())


def _execute_directly(
    dispatched_task: DispatchedNodeTask,
) -> NodeTaskResultModel:
    return dispatched_task.executor.execute(dispatched_task.task)


def _failed_task_result(
    dispatched_task: DispatchedNodeTask,
    error: Exception,
) -> NodeTaskResultModel:
    task = dispatched_task.task
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=dispatched_task.executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.FAILED,
        error={
            "message": str(error),
            "error_type": type(error).__name__,
        },
        started_at=now,
        finished_at=now,
    )
