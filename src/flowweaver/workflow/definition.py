from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from flowweaver.protocols.base import StrictModel


class FailurePolicyMode(str, Enum):
    FAIL_FAST = "FAIL_FAST"
    CONTINUE_INDEPENDENT = "CONTINUE_INDEPENDENT"
    SKIP_DEPENDENTS = "SKIP_DEPENDENTS"


UNAVAILABLE_FAILURE_POLICY_MODES = frozenset({FailurePolicyMode.SKIP_DEPENDENTS})


def failure_policy_unavailable_message(mode: FailurePolicyMode | str) -> str:
    value = mode.value if isinstance(mode, FailurePolicyMode) else mode
    return f"{value} failure policy is reserved and not available yet"


class FailurePolicyModel(StrictModel):
    mode: FailurePolicyMode = FailurePolicyMode.FAIL_FAST


class NodePositionModel(StrictModel):
    x: float = 0
    y: float = 0


class NodeInstanceModel(StrictModel):
    node_instance_id: str
    node_type: str
    node_version: str
    display_name: str | None = None
    config: dict[str, Any] = {}
    position: NodePositionModel | None = None
    enabled: bool = True


class ConnectionModel(StrictModel):
    connection_id: str
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str


class WorkflowInputModel(StrictModel):
    name: str
    data_type: str
    required: bool = True


class WorkflowOutputModel(StrictModel):
    name: str
    source_node_id: str
    source_port: str


class WorkflowDefinitionModel(StrictModel):
    schema_version: str = "1.0"
    nodes: list[NodeInstanceModel] = Field(default_factory=list)
    connections: list[ConnectionModel] = Field(default_factory=list)
    inputs: list[WorkflowInputModel] = Field(default_factory=list)
    outputs: list[WorkflowOutputModel] = Field(default_factory=list)
    failure_policy: FailurePolicyModel = Field(default_factory=FailurePolicyModel)
