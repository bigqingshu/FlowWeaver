from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Final

from pydantic import Field

from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel

MAX_RUNTIME_LOG_MESSAGE_LENGTH: Final = 1024
MAX_RUNTIME_LOGGER_NAME_LENGTH: Final = 255
_RUNTIME_LOG_LEVEL_VALUES: Final = {
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "ERROR": 40,
}
_RUNTIME_LOG_BULK_KEYS: Final = frozenset(
    {
        "rows",
        "table_rows",
        "records",
        "record_batches",
        "table_data",
        "binary",
    }
)
_RUNTIME_LOG_ERROR_CONTEXT_KEYS: Final = frozenset(
    {
        "message",
        "error_code",
        "code",
        "reason",
        "origin",
        "status",
    }
)


class RuntimeLogPayloadModel(StrictModel):
    level: RuntimeFeedbackLogLevel
    message: str = Field(min_length=1, max_length=MAX_RUNTIME_LOG_MESSAGE_LENGTH)
    logger_name: str = Field(
        min_length=1,
        max_length=MAX_RUNTIME_LOGGER_NAME_LENGTH,
    )
    context: dict[str, Any] = Field(default_factory=dict)


class WorkflowRuntimeLogPayloadModel(RuntimeLogPayloadModel):
    process_id: str = Field(min_length=1)


def runtime_log_level_is_enabled(
    *,
    configured_level: str,
    message_level: str,
) -> bool:
    configured_value = _RUNTIME_LOG_LEVEL_VALUES.get(configured_level)
    message_value = _RUNTIME_LOG_LEVEL_VALUES.get(message_level)
    if configured_value is None or message_value is None:
        return False
    return message_value >= configured_value


def sanitize_runtime_log_context(
    context: Mapping[str, Any] | None,
    *,
    include_metrics: bool,
    payload_byte_limit: int,
    redact_columns: list[str],
    mask_policy: str,
    capture_error_context: bool,
    is_error: bool,
) -> dict[str, Any]:
    cleaned = _strip_runtime_log_bulk_values(dict(context or {}))
    if not include_metrics:
        cleaned = _remove_runtime_log_key(cleaned, "metrics")
    if is_error and not capture_error_context:
        cleaned = {
            key: value
            for key, value in cleaned.items()
            if key in _RUNTIME_LOG_ERROR_CONTEXT_KEYS
        }
    if redact_columns:
        cleaned = _redact_runtime_log_values(
            cleaned,
            {column.lower() for column in redact_columns},
            mask_policy,
        )
    return _limit_runtime_log_context(
        cleaned,
        payload_byte_limit,
        essential_keys=(
            _RUNTIME_LOG_ERROR_CONTEXT_KEYS if is_error else frozenset()
        ),
    )


def _strip_runtime_log_bulk_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_runtime_log_bulk_values(item)
            for key, item in value.items()
            if key.lower() not in _RUNTIME_LOG_BULK_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_runtime_log_bulk_values(item) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"_runtime_log_binary_omitted_bytes": len(value)}
    return value


def _remove_runtime_log_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return {
            item_key: _remove_runtime_log_key(item_value, key)
            for item_key, item_value in value.items()
            if item_key != key
        }
    if isinstance(value, list):
        return [_remove_runtime_log_key(item, key) for item in value]
    return value


def _redact_runtime_log_values(
    value: Any,
    redact_columns: set[str],
    mask_policy: str,
) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                _mask_runtime_log_value(item, mask_policy)
                if key.lower() in redact_columns
                else _redact_runtime_log_values(item, redact_columns, mask_policy)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _redact_runtime_log_values(item, redact_columns, mask_policy)
            for item in value
        ]
    return value


def _mask_runtime_log_value(value: Any, mask_policy: str) -> Any:
    if mask_policy == "none":
        return value
    if mask_policy == "full":
        return "***"
    text = str(value)
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}***{text[-1]}"


def _limit_runtime_log_context(
    context: dict[str, Any],
    payload_byte_limit: int,
    *,
    essential_keys: frozenset[str],
) -> dict[str, Any]:
    if payload_byte_limit <= 0:
        return context
    encoded = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    if len(encoded) <= payload_byte_limit:
        return context
    limited = {
        key: value for key, value in context.items() if key in essential_keys
    }
    limited["_runtime_options_payload_truncated"] = True
    limited["_runtime_options_payload_original_bytes"] = len(encoded)
    return limited
