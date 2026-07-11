from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from threading import Lock

from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


class NodeTaskRuntimeFeedbackGate:
    def __init__(
        self,
        policy: ResolvedRuntimeFeedbackPolicyModel | None,
        *,
        monotonic_time: Callable[[], float] | None = None,
    ) -> None:
        self._policy = policy
        self._monotonic_time = monotonic_time or time.monotonic
        self._last_progress_emitted_at: float | None = None
        self._lock = Lock()

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
