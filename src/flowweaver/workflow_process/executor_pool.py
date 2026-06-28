from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from flowweaver.node_executor import NodeExecutor
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


def _execute_directly(
    dispatched_task: DispatchedNodeTask,
) -> NodeTaskResultModel:
    return dispatched_task.executor.execute(dispatched_task.task)
