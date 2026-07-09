from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import RuntimeEventLog


def runtime_event_log_to_jsonable(value: RuntimeEventLog) -> dict[str, Any]:
    return {
        "event_id": value.event_id,
        "sequence_number": value.sequence_number,
        "event_version": value.event_version,
        "event_type": value.event_type,
        "timestamp": value.timestamp.isoformat(),
        "workflow_run_id": value.workflow_run_id,
        "node_run_id": value.node_run_id,
        "payload": value.payload,
    }
