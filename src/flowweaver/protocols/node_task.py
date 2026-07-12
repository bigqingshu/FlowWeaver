from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import Field, model_validator

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.plugin_runtime import (
    PluginTaskRuntimeModel,
    PluginTaskRuntimeResultModel,
)
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


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
    runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel | None = None
    runtime_options_version: int = Field(default=0, ge=0)
    timeout_seconds: int
    plugin_runtime: PluginTaskRuntimeModel | None = None


class NodeTaskResultModel(StrictModel):
    result_id: str = Field(default_factory=new_id)
    task_id: str
    node_run_id: str
    attempt: int
    executor_id: str
    process_generation: int
    status: NodeResultStatus
    output_refs: list[str] = []
    output_slot_bindings: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, Any] = {}
    error: dict[str, Any] | None = None
    plugin_runtime: PluginTaskRuntimeResultModel | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_output_slot_bindings(self) -> Self:
        output_refs = set(self.output_refs)
        unknown_refs = sorted(
            {
                output_ref
                for output_ref in self.output_slot_bindings.values()
                if output_ref not in output_refs
            }
        )
        if unknown_refs:
            raise ValueError(
                "output_slot_bindings values must be present in output_refs"
            )
        return self
