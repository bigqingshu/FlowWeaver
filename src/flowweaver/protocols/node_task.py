from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import NodeResultStatus


class NodeTaskModel(StrictModel):
    task_id: str = Field(default_factory=new_id)
    workflow_run_id: str
    workflow_process_id: str
    process_generation: int
    node_run_id: str
    node_instance_id: str
    node_type: str
    node_version: str
    attempt: int
    input_refs: list[str]
    input_slot_bindings: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any]
    timeout_seconds: int


class NodeTaskResultModel(StrictModel):
    result_id: str = Field(default_factory=new_id)
    task_id: str
    node_run_id: str
    attempt: int
    executor_id: str
    process_generation: int
    status: NodeResultStatus
    output_refs: list[str] = []
    summary: dict[str, Any] = {}
    error: dict[str, Any] | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime = Field(default_factory=utc_now)
