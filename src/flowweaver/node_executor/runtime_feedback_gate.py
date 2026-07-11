from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any

from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
    RuntimeFeedbackLogLevel,
)
from flowweaver.protocols.runtime_logs import (
    runtime_log_level_is_enabled,
    sanitize_runtime_log_context,
)


class NodeTaskRuntimeFeedbackGate:
    def __init__(
        self,
        policy: ResolvedRuntimeFeedbackPolicyModel | None,
        *,
        version: int = 0,
        monotonic_time: Callable[[], float] | None = None,
    ) -> None:
        if version < 0:
            raise ValueError("runtime feedback gate version must be non-negative")
        self._policy = policy
        self._version = version
        self._monotonic_time = monotonic_time or time.monotonic
        self._last_progress_emitted_at: float | None = None
        self._lock = Lock()

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def apply_policy(
        self,
        policy: ResolvedRuntimeFeedbackPolicyModel,
        *,
        version: int,
    ) -> int:
        if version < 0:
            raise ValueError("runtime feedback gate version must be non-negative")
        with self._lock:
            if version <= self._version:
                return self._version
            self._policy = policy
            self._version = version
            return self._version

    def prepare_progress_metrics(
        self,
        metrics: Mapping[str, int | float | str] | None,
    ) -> dict[str, int | float | str] | None:
        with self._lock:
            policy = self._policy
            if policy is None:
                return dict(metrics or {})
            telemetry = policy.telemetry
            if not telemetry.progress_enabled:
                return None
            if telemetry.event_level not in {"progress", "verbose"}:
                return None
            interval = telemetry.progress_interval_seconds
            if interval > 0:
                now = self._monotonic_time()
                if (
                    self._last_progress_emitted_at is not None
                    and now - self._last_progress_emitted_at < interval
                ):
                    return None
                self._last_progress_emitted_at = now
            if not policy.diagnostics.include_metrics:
                return {}
            return dict(metrics or {})

    def prepare_log_context(
        self,
        level: RuntimeFeedbackLogLevel,
        context: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        with self._lock:
            policy = self._policy
            if policy is not None and not runtime_log_level_is_enabled(
                configured_level=policy.telemetry.log_level,
                message_level=level,
            ):
                return None
            diagnostics = policy.diagnostics if policy is not None else None
            return sanitize_runtime_log_context(
                context,
                include_metrics=(
                    diagnostics.include_metrics if diagnostics is not None else True
                ),
                payload_byte_limit=(
                    diagnostics.payload_byte_limit if diagnostics is not None else 0
                ),
                redact_columns=(
                    diagnostics.redact_columns if diagnostics is not None else []
                ),
                mask_policy=(
                    diagnostics.mask_policy if diagnostics is not None else "none"
                ),
                capture_error_context=(
                    diagnostics.capture_error_context
                    if diagnostics is not None
                    else True
                ),
                is_error=level == "ERROR",
            )
