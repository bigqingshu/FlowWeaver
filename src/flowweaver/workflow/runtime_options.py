from __future__ import annotations

from collections.abc import Mapping

from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedDiagnosticsFeedbackPolicyModel,
    ResolvedRuntimeFeedbackPolicyModel,
    ResolvedTelemetryFeedbackPolicyModel,
)
from flowweaver.workflow.definition import (
    DiagnosticsRuntimeOptionsOverrideModel,
    RuntimeOptionsOverrideModel,
    RuntimeOptionsWorkflowModel,
    TelemetryRuntimeOptionsOverrideModel,
    WorkflowDefinitionModel,
)
from flowweaver.workflow.runtime_feedback_policy import (
    RuntimeFeedbackPolicyLike,
    StaticRuntimeFeedbackPolicyProvider,
)
from flowweaver.workflow.runtime_option_sanitization import (
    sanitize_runtime_diagnostics_payload as _sanitize_runtime_diagnostics_payload,
)
from flowweaver.workflow.runtime_option_sanitization import (
    sanitize_runtime_error_payload as _sanitize_runtime_error_payload,
)
from flowweaver.workflow.runtime_options_event_sink import (
    RuntimeOptionsEventSink as RuntimeOptionsEventSink,
)

SYSTEM_DEFAULT_RUNTIME_OPTIONS = RuntimeOptionsWorkflowModel()
_PROFILE_PRESET_OVERRIDES: dict[str, dict[str, object]] = {
    "normal": SYSTEM_DEFAULT_RUNTIME_OPTIONS.model_dump(mode="json"),
    "background_fast": {
        "profile": "background_fast",
        "strict_validation": True,
        "telemetry": {
            "log_level": "WARN",
            "event_level": "basic",
            "event_rate_limit_per_second": 10,
            "progress_enabled": False,
            "progress_interval_seconds": 5,
        },
        "diagnostics": {
            "capture_error_context": True,
            "include_metrics": False,
            "payload_byte_limit": 65536,
            "ttl_seconds": 604800,
            "redact_columns": [],
            "mask_policy": "partial",
        },
    },
    "diagnostic": {
        "profile": "diagnostic",
        "strict_validation": True,
        "telemetry": {
            "log_level": "DEBUG",
            "event_level": "verbose",
            "event_rate_limit_per_second": 0,
            "progress_enabled": True,
            "progress_interval_seconds": 0,
        },
        "diagnostics": {
            "capture_error_context": True,
            "include_metrics": True,
            "payload_byte_limit": 262144,
            "ttl_seconds": 86400,
            "redact_columns": [],
            "mask_policy": "partial",
        },
    },
}


def resolve_runtime_options_for_node(
    definition: WorkflowDefinitionModel,
    node_instance_id: str,
) -> RuntimeOptionsWorkflowModel:
    runtime_options = definition.runtime_options
    workflow_options = resolve_workflow_runtime_options(definition)
    node_override = (
        runtime_options.node_overrides.get(node_instance_id)
        if runtime_options is not None
        else None
    )
    return merge_runtime_options(
        SYSTEM_DEFAULT_RUNTIME_OPTIONS,
        workflow_options,
        node_override,
    )


def resolve_workflow_runtime_options(
    definition: WorkflowDefinitionModel,
) -> RuntimeOptionsWorkflowModel:
    runtime_options = definition.runtime_options
    return merge_runtime_options(
        SYSTEM_DEFAULT_RUNTIME_OPTIONS,
        runtime_options.workflow if runtime_options is not None else None,
    )


def resolve_runtime_options_by_node(
    definition: WorkflowDefinitionModel,
) -> dict[str, RuntimeOptionsWorkflowModel]:
    return {
        node.node_instance_id: resolve_runtime_options_for_node(
            definition,
            node.node_instance_id,
        )
        for node in definition.nodes
    }


def runtime_feedback_policy_from_options(
    options: RuntimeOptionsWorkflowModel,
) -> ResolvedRuntimeFeedbackPolicyModel:
    return ResolvedRuntimeFeedbackPolicyModel(
        telemetry=ResolvedTelemetryFeedbackPolicyModel(
            log_level=options.telemetry.log_level.value,
            event_level=options.telemetry.event_level.value,
            event_rate_limit_per_second=(
                options.telemetry.event_rate_limit_per_second
            ),
            progress_enabled=options.telemetry.progress_enabled,
            progress_interval_seconds=(
                options.telemetry.progress_interval_seconds
            ),
        ),
        diagnostics=ResolvedDiagnosticsFeedbackPolicyModel(
            capture_error_context=options.diagnostics.capture_error_context,
            include_metrics=options.diagnostics.include_metrics,
            payload_byte_limit=options.diagnostics.payload_byte_limit,
            redact_columns=list(options.diagnostics.redact_columns),
            mask_policy=options.diagnostics.mask_policy.value,
        ),
    )


def build_static_runtime_feedback_policy_provider(
    definition: WorkflowDefinitionModel,
    *,
    version: int = 0,
) -> StaticRuntimeFeedbackPolicyProvider:
    workflow_options = resolve_workflow_runtime_options(definition)
    options_by_node = resolve_runtime_options_by_node(definition)
    return StaticRuntimeFeedbackPolicyProvider(
        workflow_policy=runtime_feedback_policy_from_options(workflow_options),
        policies_by_node={
            node_instance_id: runtime_feedback_policy_from_options(options)
            for node_instance_id, options in options_by_node.items()
        },
        version=version,
    )


def sanitize_node_task_result_for_runtime_options(
    result: NodeTaskResultModel,
    options: RuntimeFeedbackPolicyLike | None,
) -> NodeTaskResultModel:
    if options is None:
        return result
    return result.model_copy(
        update={
            "summary": _sanitize_runtime_diagnostics_payload(
                result.summary,
                options,
            ),
            "error": (
                None
                if result.error is None
                else _sanitize_runtime_error_payload(result.error, options)
            ),
        }
    )


def merge_runtime_options(
    system_defaults: RuntimeOptionsWorkflowModel,
    workflow_options: RuntimeOptionsWorkflowModel | None = None,
    node_override: RuntimeOptionsOverrideModel | None = None,
) -> RuntimeOptionsWorkflowModel:
    workflow_options = workflow_options or RuntimeOptionsWorkflowModel()
    merged_data = _merge_runtime_options_overlay(
        system_defaults.model_dump(mode="json"),
        workflow_options.model_dump(mode="json", exclude_unset=True),
    )
    if node_override is None:
        return RuntimeOptionsWorkflowModel.model_validate(merged_data)
    override_data = node_override.model_dump(mode="json", exclude_none=True)
    return RuntimeOptionsWorkflowModel.model_validate(
        _merge_runtime_options_overlay(
            merged_data,
            _normalize_node_override_data(override_data),
        )
    )


def _normalize_node_override_data(
    override_data: Mapping[str, object],
) -> dict[str, object]:
    normalized = dict(override_data)
    telemetry = normalized.get("telemetry")
    if isinstance(telemetry, Mapping):
        normalized["telemetry"] = _telemetry_from_override(telemetry).model_dump(
            mode="json",
            exclude_none=True,
        )
    diagnostics = normalized.get("diagnostics")
    if isinstance(diagnostics, Mapping):
        normalized["diagnostics"] = _diagnostics_from_override(
            diagnostics
        ).model_dump(
            mode="json",
            exclude_none=True,
        )
    return normalized


def _telemetry_from_override(
    data: Mapping[str, object],
) -> TelemetryRuntimeOptionsOverrideModel:
    return TelemetryRuntimeOptionsOverrideModel.model_validate(dict(data))


def _diagnostics_from_override(
    data: Mapping[str, object],
) -> DiagnosticsRuntimeOptionsOverrideModel:
    return DiagnosticsRuntimeOptionsOverrideModel.model_validate(dict(data))


def _merge_dicts(
    base: Mapping[str, object],
    override: Mapping[str, object],
) -> dict[str, object]:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if (
            isinstance(value, Mapping)
            and isinstance(current, Mapping)
        ):
            result[key] = _merge_dicts(
                current,
                value,
            )
            continue
        result[key] = value
    return result


def _merge_runtime_options_overlay(
    base: Mapping[str, object],
    overlay: Mapping[str, object],
) -> dict[str, object]:
    profile = overlay.get("profile")
    result = dict(base)
    if isinstance(profile, str):
        result = _merge_dicts(result, _profile_preset_data(profile))
    return _merge_dicts(result, overlay)


def _profile_preset_data(profile: str) -> dict[str, object]:
    preset = _PROFILE_PRESET_OVERRIDES.get(profile)
    return dict(preset or {})
