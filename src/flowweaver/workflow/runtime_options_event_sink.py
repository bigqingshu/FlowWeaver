from __future__ import annotations

import time
from collections.abc import Callable, Mapping

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.protocols.events import EventModel
from flowweaver.workflow.definition import RuntimeOptionsWorkflowModel
from flowweaver.workflow.runtime_option_sanitization import (
    CRITICAL_EVENT_TYPES as _CRITICAL_EVENT_TYPES,
)
from flowweaver.workflow.runtime_option_sanitization import (
    event_node_instance_id as _event_node_instance_id,
)
from flowweaver.workflow.runtime_option_sanitization import (
    runtime_options_should_emit_event as _runtime_options_should_emit_event,
)
from flowweaver.workflow.runtime_option_sanitization import (
    sanitize_runtime_event as _sanitize_runtime_event,
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
