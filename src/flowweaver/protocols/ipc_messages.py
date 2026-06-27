from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


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


class NodeTaskCompletedPayload(StrictModel):
    result: NodeTaskResultModel
