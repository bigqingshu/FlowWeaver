from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class NodeExecutor(Protocol):
    executor_id: str

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        ...


NodeExecutorFactory = Callable[[NodeTaskModel], NodeExecutor]
