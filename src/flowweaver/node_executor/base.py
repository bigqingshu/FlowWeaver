from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class NodeExecutor(Protocol):
    executor_id: str

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        ...


@runtime_checkable
class CancellableNodeExecutor(Protocol):
    executor_id: str

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        ...


NodeExecutorFactory = Callable[[NodeTaskModel], NodeExecutor]
