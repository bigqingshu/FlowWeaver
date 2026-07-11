from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)
from flowweaver.protocols.runtime_logs import RuntimeLogPayloadModel


class IPCEnvelope(StrictModel):
    protocol_version: str = "1.0"
    message_id: str = Field(default_factory=new_id)
    message_type: IPCMessageType
    timestamp: datetime = Field(default_factory=utc_now)
    workflow_run_id: str | None = None
    node_run_id: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any]


class ExecutorHeartbeatPayload(StrictModel):
    executor_id: str
    active_task_ids: list[str] = Field(default_factory=list)


class NodeTaskHeartbeatPayload(StrictModel):
    executor_id: str
    task_id: str
    attempt: int


class NodeTaskSubmitPayload(NodeTaskModel):
    pass


class NodeTaskProgressPayload(StrictModel):
    progress: float | None
    current_stage: str | None = None
    metrics: dict[str, int | float | str] = Field(default_factory=dict)


class NodeTaskLogPayload(RuntimeLogPayloadModel):
    node_instance_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)


class NodeTaskRuntimeOptionsUpdatePayload(StrictModel):
    task_id: str = Field(min_length=1)
    runtime_options_version: int = Field(ge=0)
    runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel


class NodeTaskRuntimeOptionsAppliedPayload(StrictModel):
    task_id: str = Field(min_length=1)
    runtime_options_version: int = Field(ge=0)


class NodeTaskCancelRequestPayload(StrictModel):
    task_id: str
    reason: str = "WORKFLOW_CANCEL_REQUESTED"


class NodeTaskCompletedPayload(StrictModel):
    result: NodeTaskResultModel


class NodeTaskFailedPayload(StrictModel):
    result: NodeTaskResultModel
    error_type: str
