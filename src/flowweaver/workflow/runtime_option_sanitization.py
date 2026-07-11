from __future__ import annotations

import json
from typing import Any

from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.runtime_logs import (
    MAX_RUNTIME_LOG_MESSAGE_LENGTH,
    MAX_RUNTIME_LOGGER_NAME_LENGTH,
    runtime_log_level_is_enabled,
    sanitize_runtime_log_context,
)
from flowweaver.workflow.runtime_feedback_policy import RuntimeFeedbackPolicyLike

RUNTIME_LOG_EVENT_TYPES = frozenset(
    {
        EventType.WORKFLOW_LOG,
        EventType.NODE_LOG,
    }
)

CRITICAL_EVENT_TYPES = frozenset(
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
BASIC_EVENT_TYPES = CRITICAL_EVENT_TYPES | frozenset(
    {
        EventType.NODE_QUEUED,
        EventType.NODE_LONG_RUNNING,
    }
)
ESSENTIAL_PAYLOAD_KEYS = frozenset(
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
ESSENTIAL_ERROR_KEYS = frozenset(
    {
        "message",
        "error_code",
        "code",
        "reason",
        "origin",
        "status",
    }
)


def runtime_options_should_emit_event(
    event: EventModel,
    options: RuntimeFeedbackPolicyLike,
) -> bool:
    if event.event_type in RUNTIME_LOG_EVENT_TYPES:
        level = event.payload.get("level")
        configured_level = options.telemetry.log_level
        return isinstance(level, str) and runtime_log_level_is_enabled(
            configured_level=getattr(
                configured_level,
                "value",
                configured_level,
            ),
            message_level=level,
        )
    if event.event_type == EventType.NODE_PROGRESS:
        return options.telemetry.progress_enabled and (
            options.telemetry.event_level in {"progress", "verbose"}
        )
    if event.event_type in CRITICAL_EVENT_TYPES:
        return True
    if options.telemetry.event_level == "none":
        return False
    if options.telemetry.event_level == "basic":
        return event.event_type in BASIC_EVENT_TYPES
    if options.telemetry.event_level == "progress":
        return True
    return True


def sanitize_runtime_event(
    event: EventModel,
    options: RuntimeFeedbackPolicyLike,
) -> EventModel:
    if event.event_type in RUNTIME_LOG_EVENT_TYPES:
        return _sanitize_runtime_log_event(event, options)
    payload = dict(event.payload)
    payload = sanitize_runtime_diagnostics_payload(payload, options)
    return event.model_copy(update={"payload": payload})


def sanitize_runtime_diagnostics_payload(
    payload: dict[str, Any],
    options: RuntimeFeedbackPolicyLike,
    *,
    essential_keys: frozenset[str] = ESSENTIAL_PAYLOAD_KEYS,
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


def sanitize_runtime_error_payload(
    payload: dict[str, Any],
    options: RuntimeFeedbackPolicyLike,
) -> dict[str, Any]:
    if not options.diagnostics.capture_error_context:
        payload = {
            key: value
            for key, value in payload.items()
            if key in ESSENTIAL_ERROR_KEYS
        }
    return sanitize_runtime_diagnostics_payload(
        payload,
        options,
        essential_keys=ESSENTIAL_PAYLOAD_KEYS | ESSENTIAL_ERROR_KEYS,
    )


def event_node_instance_id(event: EventModel) -> str | None:
    value = event.payload.get("node_instance_id")
    return value if isinstance(value, str) and value else None


def runtime_log_event_is_error(event: EventModel) -> bool:
    return (
        event.event_type in RUNTIME_LOG_EVENT_TYPES
        and event.payload.get("level") == "ERROR"
    )


def _sanitize_runtime_log_event(
    event: EventModel,
    options: RuntimeFeedbackPolicyLike,
) -> EventModel:
    source = event.payload
    context = source.get("context")
    cleaned_context = sanitize_runtime_log_context(
        context if isinstance(context, dict) else {},
        include_metrics=options.diagnostics.include_metrics,
        payload_byte_limit=options.diagnostics.payload_byte_limit,
        redact_columns=options.diagnostics.redact_columns,
        mask_policy=options.diagnostics.mask_policy,
        capture_error_context=options.diagnostics.capture_error_context,
        is_error=source.get("level") == "ERROR",
    )
    payload: dict[str, Any] = {
        "level": source.get("level"),
        "message": _truncate_runtime_log_text(
            source.get("message"),
            MAX_RUNTIME_LOG_MESSAGE_LENGTH,
        ),
        "logger_name": _truncate_runtime_log_text(
            source.get("logger_name"),
            MAX_RUNTIME_LOGGER_NAME_LENGTH,
        ),
        "context": cleaned_context,
    }
    for key in ("process_id", "node_instance_id", "task_id"):
        value = source.get(key)
        if isinstance(value, str) and value:
            payload[key] = value
    return event.model_copy(update={"payload": payload})


def _truncate_runtime_log_text(value: Any, limit: int) -> str:
    return str(value or "")[:limit]


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
    essential_keys: frozenset[str] = ESSENTIAL_PAYLOAD_KEYS,
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
