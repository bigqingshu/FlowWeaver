from __future__ import annotations

from typing import Literal

from pydantic import Field

from flowweaver.protocols.base import StrictModel

RuntimeFeedbackLogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]
RuntimeFeedbackEventLevel = Literal["none", "basic", "progress", "verbose"]
RuntimeFeedbackMaskPolicy = Literal["none", "partial", "full"]


class ResolvedTelemetryFeedbackPolicyModel(StrictModel):
    log_level: RuntimeFeedbackLogLevel
    event_level: RuntimeFeedbackEventLevel
    event_rate_limit_per_second: int = Field(ge=0)
    progress_enabled: bool
    progress_interval_seconds: float = Field(ge=0)


class ResolvedDiagnosticsFeedbackPolicyModel(StrictModel):
    capture_error_context: bool
    include_metrics: bool
    payload_byte_limit: int = Field(ge=0)
    redact_columns: list[str] = Field(default_factory=list)
    mask_policy: RuntimeFeedbackMaskPolicy


class ResolvedRuntimeFeedbackPolicyModel(StrictModel):
    telemetry: ResolvedTelemetryFeedbackPolicyModel
    diagnostics: ResolvedDiagnosticsFeedbackPolicyModel


class TelemetryFeedbackPolicyOverrideModel(StrictModel):
    log_level: RuntimeFeedbackLogLevel | None = None
    event_level: RuntimeFeedbackEventLevel | None = None
    event_rate_limit_per_second: int | None = Field(default=None, ge=0)
    progress_enabled: bool | None = None
    progress_interval_seconds: float | None = Field(default=None, ge=0)


class DiagnosticsFeedbackPolicyOverrideModel(StrictModel):
    capture_error_context: bool | None = None
    include_metrics: bool | None = None
    payload_byte_limit: int | None = Field(default=None, ge=0)
    redact_columns: list[str] | None = None
    mask_policy: RuntimeFeedbackMaskPolicy | None = None


class RuntimeFeedbackPolicyOverrideModel(StrictModel):
    telemetry: TelemetryFeedbackPolicyOverrideModel | None = None
    diagnostics: DiagnosticsFeedbackPolicyOverrideModel | None = None
