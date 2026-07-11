from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


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


@runtime_checkable
class RuntimeOptionsUpdatableNodeExecutor(Protocol):
    executor_id: str

    def request_runtime_options_update(
        self,
        task: NodeTaskModel,
        *,
        runtime_options_version: int,
        runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel,
    ) -> bool:
        ...


NodeExecutorFactory = Callable[[NodeTaskModel], NodeExecutor]
