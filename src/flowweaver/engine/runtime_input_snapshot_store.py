from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import InputSnapshotRecord, WorkflowRunRecord
from flowweaver.engine.runtime_models import InputSnapshot, InputSnapshotEntry
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _input_snapshot_from_record,
    _input_snapshot_json,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    validate_input_snapshot_publications as _validate_input_snapshot_publications,
)


class RuntimeInputSnapshotStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_input_snapshot(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        input_snapshot_id: str | None = None,
    ) -> InputSnapshot:
        input_snapshot_id = input_snapshot_id or new_id()
        inputs_tuple = tuple(inputs)
        now = utc_now()
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
                created_at=_datetime_to_text(now),
            )
            session.add(record)
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return _input_snapshot_from_record(record)

    def get_input_snapshot(
        self,
        input_snapshot_id: str,
    ) -> InputSnapshot | None:
        with self._session_factory() as session:
            record = session.get(InputSnapshotRecord, input_snapshot_id)
            if record is None:
                return None
            return _input_snapshot_from_record(record)
