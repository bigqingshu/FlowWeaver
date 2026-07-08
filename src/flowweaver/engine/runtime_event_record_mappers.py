from __future__ import annotations

import json

from flowweaver.engine.db_models import RuntimeEventRecord
from flowweaver.engine.runtime_models import RuntimeEventLog
from flowweaver.engine.runtime_record_codecs import _datetime_from_text


def _runtime_event_from_record(record: RuntimeEventRecord) -> RuntimeEventLog:
    return RuntimeEventLog(
        event_id=record.event_id,
        sequence_number=record.sequence_number,
        event_version=record.event_version,
        event_type=record.event_type,
        timestamp=_datetime_from_text(record.timestamp),
        workflow_run_id=record.workflow_run_id,
        node_run_id=record.node_run_id,
        payload=json.loads(record.payload_json),
    )
