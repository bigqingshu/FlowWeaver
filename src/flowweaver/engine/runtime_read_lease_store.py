from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    ReadLeaseRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import ReadLease
from flowweaver.engine.runtime_read_lease_queries import (
    get_read_lease_from_session as _get_read_lease,
)
from flowweaver.engine.runtime_read_lease_queries import (
    list_read_leases_by_workflow_run_from_session as _list_read_leases_by_run,
)
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _read_lease_from_record,
    _selected_members_json,
)


class RuntimeReadLeaseStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_read_lease(
        self,
        *,
        publication_id: str,
        publication_version: int,
        consumer_workflow_run_id: str,
        selected_members: Iterable[str],
        expires_at: datetime,
        lease_id: str | None = None,
    ) -> ReadLease:
        lease_id = lease_id or new_id()
        selected_members_tuple = tuple(selected_members)
        now = utc_now()
        with self._session_factory.begin() as session:
            consumer_run = session.get(WorkflowRunRecord, consumer_workflow_run_id)
            if consumer_run is None:
                raise ValueError(
                    f"Consumer workflow run not found: {consumer_workflow_run_id}"
                )
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=consumer_workflow_run_id,
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add(record)
            session.flush()
            return _read_lease_from_record(record)

    def get_read_lease(self, lease_id: str) -> ReadLease | None:
        with self._session_factory() as session:
            return _get_read_lease(session, lease_id)

    def list_read_leases_by_workflow_run(
        self,
        workflow_run_id: str,
        *,
        active_only: bool = False,
    ) -> list[ReadLease]:
        with self._session_factory() as session:
            return _list_read_leases_by_run(
                session,
                workflow_run_id,
                active_only=active_only,
            )

    def release_read_lease(self, lease_id: str) -> ReadLease | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(ReadLeaseRecord, lease_id)
            if record is None:
                return None
            if record.released_at is None:
                record.released_at = _datetime_to_text(now)
            return _read_lease_from_record(record)

    def release_unreleased_read_leases_for_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[ReadLease]:
        now = utc_now()
        with self._session_factory.begin() as session:
            records = session.scalars(
                select(ReadLeaseRecord)
                .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
                .where(ReadLeaseRecord.released_at.is_(None))
                .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
            ).all()
            for record in records:
                record.released_at = _datetime_to_text(now)
            session.flush()
            return [_read_lease_from_record(record) for record in records]
