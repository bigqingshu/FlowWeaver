from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import ReadLeaseRecord
from flowweaver.engine.runtime_models import ReadLease
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _read_lease_from_record,
)


def get_read_lease_from_session(
    session: Session,
    lease_id: str,
) -> ReadLease | None:
    record = session.get(ReadLeaseRecord, lease_id)
    if record is None:
        return None
    return _read_lease_from_record(record)


def list_read_leases_by_workflow_run_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    active_only: bool = False,
) -> list[ReadLease]:
    statement = (
        select(ReadLeaseRecord)
        .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
        .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
    )
    if active_only:
        statement = statement.where(ReadLeaseRecord.released_at.is_(None))
        statement = statement.where(
            ReadLeaseRecord.expires_at > _datetime_to_text(utc_now())
        )
    return [_read_lease_from_record(record) for record in session.scalars(statement)]
