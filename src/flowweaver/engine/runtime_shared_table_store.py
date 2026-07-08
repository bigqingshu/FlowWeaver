from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    InputSnapshotRecord,
    ReadLeaseRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    ReadLease,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _input_snapshot_from_record,
    _input_snapshot_json,
    _read_lease_from_record,
    _selected_members_json,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    validate_input_snapshot_publications as _validate_input_snapshot_publications,
)


class RuntimeSharedTableStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_input_snapshot_and_read_lease(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        publication_id: str,
        publication_version: int,
        selected_members: Iterable[str],
        expires_at: datetime,
    ) -> tuple[InputSnapshot, ReadLease]:
        input_snapshot_id = new_id()
        lease_id = new_id()
        inputs_tuple = tuple(inputs)
        selected_members_tuple = tuple(selected_members)
        if len(inputs_tuple) != 1:
            raise ValueError(
                "Atomic input snapshot/read lease requires exactly one input"
            )
        snapshot_input = inputs_tuple[0]
        if snapshot_input.publication_id != publication_id:
            raise ValueError("Input snapshot and read lease publication mismatch")
        if snapshot_input.publication_version != publication_version:
            raise ValueError(
                "Input snapshot and read lease publication version mismatch"
            )
        if snapshot_input.selected_members != selected_members_tuple:
            raise ValueError("Input snapshot and read lease selected members mismatch")
        now = utc_now()
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            snapshot_record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
                created_at=_datetime_to_text(now),
            )
            lease_record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=workflow_run_id,
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add_all([snapshot_record, lease_record])
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return (
                _input_snapshot_from_record(snapshot_record),
                _read_lease_from_record(lease_record),
            )
