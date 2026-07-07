from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

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


class RuntimeOptionsProfile(str, Enum):
    BACKGROUND_FAST = "background_fast"
    NORMAL = "normal"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"


class RuntimeOptionsLogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class RuntimeOptionsEventLevel(str, Enum):
    NONE = "none"
    BASIC = "basic"
    PROGRESS = "progress"
    VERBOSE = "verbose"


class RuntimeOptionsMaskPolicy(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class TelemetryRuntimeOptionsModel(StrictModel):
    log_level: RuntimeOptionsLogLevel = RuntimeOptionsLogLevel.INFO
    event_level: RuntimeOptionsEventLevel = RuntimeOptionsEventLevel.PROGRESS
    event_rate_limit_per_second: int = Field(default=0, ge=0)
    progress_enabled: bool = True
    progress_interval_seconds: float = Field(default=0, ge=0)


class DiagnosticsRuntimeOptionsModel(StrictModel):
    capture_error_context: bool = True
    include_metrics: bool = True
    payload_byte_limit: int = Field(default=0, ge=0)
    ttl_seconds: int = Field(default=0, ge=0)
    redact_columns: list[str] = Field(default_factory=list)
    mask_policy: RuntimeOptionsMaskPolicy = RuntimeOptionsMaskPolicy.NONE


class RuntimeOptionsWorkflowModel(StrictModel):
    profile: RuntimeOptionsProfile = RuntimeOptionsProfile.NORMAL
    strict_validation: bool = True
    telemetry: TelemetryRuntimeOptionsModel = Field(
        default_factory=TelemetryRuntimeOptionsModel
    )
    diagnostics: DiagnosticsRuntimeOptionsModel = Field(
        default_factory=DiagnosticsRuntimeOptionsModel
    )


class TelemetryRuntimeOptionsOverrideModel(StrictModel):
    log_level: RuntimeOptionsLogLevel | None = None
    event_level: RuntimeOptionsEventLevel | None = None
    event_rate_limit_per_second: int | None = Field(default=None, ge=0)
    progress_enabled: bool | None = None
    progress_interval_seconds: float | None = Field(default=None, ge=0)


class DiagnosticsRuntimeOptionsOverrideModel(StrictModel):
    capture_error_context: bool | None = None
    include_metrics: bool | None = None
    payload_byte_limit: int | None = Field(default=None, ge=0)
    ttl_seconds: int | None = Field(default=None, ge=0)
    redact_columns: list[str] | None = None
    mask_policy: RuntimeOptionsMaskPolicy | None = None


class RuntimeOptionsOverrideModel(StrictModel):
    profile: RuntimeOptionsProfile | None = None
    strict_validation: bool | None = None
    telemetry: TelemetryRuntimeOptionsOverrideModel | None = None
    diagnostics: DiagnosticsRuntimeOptionsOverrideModel | None = None


class RuntimeOptionsModel(StrictModel):
    version: Literal["1.0"] = "1.0"
    workflow: RuntimeOptionsWorkflowModel = Field(
        default_factory=RuntimeOptionsWorkflowModel
    )
    node_overrides: dict[str, RuntimeOptionsOverrideModel] = Field(
        default_factory=dict
    )

    @field_validator("node_overrides")
    @classmethod
    def validate_node_override_keys(
        cls,
        value: dict[str, RuntimeOptionsOverrideModel],
    ) -> dict[str, RuntimeOptionsOverrideModel]:
        if any(not key.strip() for key in value):
            raise ValueError("node_overrides keys must be non-empty node instance IDs")
        return value


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
    runtime_options: RuntimeOptionsModel | None = None
