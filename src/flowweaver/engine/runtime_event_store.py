from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.engine.db_models import RuntimeEventRecord
from flowweaver.engine.runtime_event_record_mappers import (
    _runtime_event_from_record,
)
from flowweaver.engine.runtime_models import RuntimeEventLog
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.protocols.events import EventModel


class RuntimeEventStoreMixin:
    _session_factory: sessionmaker[Session]

    def append_runtime_event(self, event: EventModel) -> int:
        with self._session_factory.begin() as session:
            record = RuntimeEventRecord(
                event_id=event.event_id,
                event_version=event.event_version,
                event_type=event.event_type.value,
                timestamp=_datetime_to_text(event.timestamp),
                workflow_run_id=event.workflow_run_id,
                node_run_id=event.node_run_id,
                payload_json=_json_dumps(event.payload),
            )
            session.add(record)
            session.flush()
            return record.sequence_number

    def list_runtime_events(
        self,
        *,
        after_sequence_number: int | None = None,
        workflow_run_id: str | None = None,
        node_run_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[RuntimeEventLog]:
        limit = max(1, min(limit, 1000))
        statement = select(RuntimeEventRecord).order_by(
            RuntimeEventRecord.sequence_number
        )
        if after_sequence_number is not None:
            statement = statement.where(
                RuntimeEventRecord.sequence_number > after_sequence_number
            )
        if workflow_run_id is not None:
            statement = statement.where(
                RuntimeEventRecord.workflow_run_id == workflow_run_id
            )
        if node_run_id is not None:
            statement = statement.where(RuntimeEventRecord.node_run_id == node_run_id)
        if event_type is not None:
            statement = statement.where(RuntimeEventRecord.event_type == event_type)
        with self._session_factory() as session:
            return [
                _runtime_event_from_record(record)
                for record in session.scalars(statement.limit(limit))
            ]
