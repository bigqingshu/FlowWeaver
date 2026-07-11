from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)
from flowweaver.workflow.definition import RuntimeOptionsWorkflowModel

RuntimeFeedbackPolicyLike = (
    RuntimeOptionsWorkflowModel | ResolvedRuntimeFeedbackPolicyModel
)


class RuntimeFeedbackPolicyProvider(Protocol):
    @property
    def version(self) -> int:
        ...

    def workflow_policy(self) -> ResolvedRuntimeFeedbackPolicyModel:
        ...

    def policy_for_node(
        self,
        node_instance_id: str,
    ) -> ResolvedRuntimeFeedbackPolicyModel:
        ...


class StaticRuntimeFeedbackPolicyProvider:
    def __init__(
        self,
        *,
        workflow_policy: ResolvedRuntimeFeedbackPolicyModel,
        policies_by_node: Mapping[str, ResolvedRuntimeFeedbackPolicyModel],
        version: int = 0,
    ) -> None:
        if version < 0:
            raise ValueError("runtime feedback policy version must be non-negative")
        self._workflow_policy = workflow_policy
        self._policies_by_node = dict(policies_by_node)
        self._version = version

    @property
    def version(self) -> int:
        return self._version

    def workflow_policy(self) -> ResolvedRuntimeFeedbackPolicyModel:
        return self._workflow_policy

    def policy_for_node(
        self,
        node_instance_id: str,
    ) -> ResolvedRuntimeFeedbackPolicyModel:
        return self._policies_by_node.get(
            node_instance_id,
            self._workflow_policy,
        )
