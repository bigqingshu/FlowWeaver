from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.workflow.definition import (
    DiagnosticsRuntimeOptionsOverrideModel,
    RuntimeOptionsOverrideModel,
    RuntimeOptionsWorkflowModel,
    TelemetryRuntimeOptionsOverrideModel,
    WorkflowDefinitionModel,
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
_CRITICAL_EVENT_TYPES = frozenset(
    {
        EventType.WORKFLOW_STARTED,
        EventType.WORKFLOW_FINISHED,
        EventType.WORKFLOW_FAILED,
        EventType.WORKFLOW_CANCELLED,
        EventType.NODE_STARTED,
        EventType.NODE_FINISHED,
        EventType.NODE_FAILED,
        EventType.NODE_TIMEOUT,
    }
)
_BASIC_EVENT_TYPES = _CRITICAL_EVENT_TYPES | frozenset(
    {
        EventType.NODE_QUEUED,
        EventType.NODE_LONG_RUNNING,
    }
)
_ESSENTIAL_PAYLOAD_KEYS = frozenset(
    {
        "process_id",
        "task_id",
        "executor_id",
        "node_instance_id",
        "completion_reason",
        "run_mode",
        "target_node_instance_id",
    }
)
_ESSENTIAL_ERROR_KEYS = frozenset(
    {
        "message",
        "error_code",
        "code",
        "reason",
        "origin",
        "status",
    }
)


class RuntimeOptionsEventSink:
    def __init__(
        self,
        inner: RuntimeEventSink,
        *,
        workflow_options: RuntimeOptionsWorkflowModel,
        runtime_options_by_node: Mapping[str, RuntimeOptionsWorkflowModel],
        monotonic_time: Callable[[], float] | None = None,
    ) -> None:
        self._inner = inner
        self._workflow_options = workflow_options
        self._runtime_options_by_node = dict(runtime_options_by_node)
        self._monotonic_time = monotonic_time or time.monotonic
        self._rate_windows: dict[tuple[str, str, str, int], int] = {}

    def emit(self, event: EventModel) -> None:
        options = self._options_for_event(event)
        if not _runtime_options_should_emit_event(event, options):
            return
        if not self._allow_rate_limited_event(event, options):
            return
        self._inner.emit(_sanitize_runtime_event(event, options))

    def _options_for_event(self, event: EventModel) -> RuntimeOptionsWorkflowModel:
        node_instance_id = _event_node_instance_id(event)
        if node_instance_id is None:
            return self._workflow_options
        return self._runtime_options_by_node.get(
            node_instance_id,
            self._workflow_options,
        )

    def _allow_rate_limited_event(
        self,
        event: EventModel,
        options: RuntimeOptionsWorkflowModel,
    ) -> bool:
        limit = options.telemetry.event_rate_limit_per_second
        if limit <= 0 or event.event_type in _CRITICAL_EVENT_TYPES:
            return True
        window = int(self._monotonic_time())
        key = (
            event.workflow_run_id or "",
            event.node_run_id or _event_node_instance_id(event) or "",
            event.event_type.value,
            window,
        )
        count = self._rate_windows.get(key, 0)
        if count >= limit:
            return False
        self._rate_windows[key] = count + 1
        if len(self._rate_windows) > 4096:
            self._rate_windows = {
                item_key: item_count
                for item_key, item_count in self._rate_windows.items()
                if item_key[3] >= window - 1
            }
        return True


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


def sanitize_node_task_result_for_runtime_options(
    result: NodeTaskResultModel,
    options: RuntimeOptionsWorkflowModel | None,
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


def _runtime_options_should_emit_event(
    event: EventModel,
    options: RuntimeOptionsWorkflowModel,
) -> bool:
    if event.event_type == EventType.NODE_PROGRESS:
        return options.telemetry.progress_enabled and (
            options.telemetry.event_level in {"progress", "verbose"}
        )
    if event.event_type in _CRITICAL_EVENT_TYPES:
        return True
    if options.telemetry.event_level == "none":
        return False
    if options.telemetry.event_level == "basic":
        return event.event_type in _BASIC_EVENT_TYPES
    if options.telemetry.event_level == "progress":
        return True
    return True


def _sanitize_runtime_event(
    event: EventModel,
    options: RuntimeOptionsWorkflowModel,
) -> EventModel:
    payload = dict(event.payload)
    payload = _sanitize_runtime_diagnostics_payload(payload, options)
    return event.model_copy(update={"payload": payload})


def _sanitize_runtime_diagnostics_payload(
    payload: dict[str, Any],
    options: RuntimeOptionsWorkflowModel,
    *,
    essential_keys: frozenset[str] = _ESSENTIAL_PAYLOAD_KEYS,
) -> dict[str, Any]:
    payload = dict(payload)
    if not options.diagnostics.include_metrics:
        payload = _remove_payload_key(payload, "metrics")
    if options.diagnostics.redact_columns:
        payload = _redact_payload(
            payload,
            {column.lower() for column in options.diagnostics.redact_columns},
            options.diagnostics.mask_policy,
        )
    payload = _limit_payload_size(
        payload,
        options.diagnostics.payload_byte_limit,
        essential_keys=essential_keys,
    )
    return payload


def _sanitize_runtime_error_payload(
    payload: dict[str, Any],
    options: RuntimeOptionsWorkflowModel,
) -> dict[str, Any]:
    if not options.diagnostics.capture_error_context:
        payload = {
            key: value
            for key, value in payload.items()
            if key in _ESSENTIAL_ERROR_KEYS
        }
    return _sanitize_runtime_diagnostics_payload(
        payload,
        options,
        essential_keys=_ESSENTIAL_PAYLOAD_KEYS | _ESSENTIAL_ERROR_KEYS,
    )


def _event_node_instance_id(event: EventModel) -> str | None:
    value = event.payload.get("node_instance_id")
    return value if isinstance(value, str) and value else None


def _remove_payload_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return {
            item_key: _remove_payload_key(item_value, key)
            for item_key, item_value in value.items()
            if item_key != key
        }
    if isinstance(value, list):
        return [_remove_payload_key(item, key) for item in value]
    return value


def _redact_payload(
    value: Any,
    redact_columns: set[str],
    mask_policy: str,
) -> Any:
    if isinstance(value, dict):
        return {
            item_key: (
                _mask_value(item_value, mask_policy)
                if item_key.lower() in redact_columns
                else _redact_payload(item_value, redact_columns, mask_policy)
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item, redact_columns, mask_policy) for item in value]
    return value


def _mask_value(value: Any, mask_policy: str) -> Any:
    if mask_policy == "none":
        return value
    if mask_policy == "full":
        return "***"
    text = str(value)
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}***{text[-1]}"


def _limit_payload_size(
    payload: dict[str, Any],
    payload_byte_limit: int,
    *,
    essential_keys: frozenset[str] = _ESSENTIAL_PAYLOAD_KEYS,
) -> dict[str, Any]:
    if payload_byte_limit <= 0:
        return payload
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    if len(encoded) <= payload_byte_limit:
        return payload
    limited = {
        key: value
        for key, value in payload.items()
        if key in essential_keys
    }
    limited["_runtime_options_payload_truncated"] = True
    limited["_runtime_options_payload_original_bytes"] = len(encoded)
    return limited
