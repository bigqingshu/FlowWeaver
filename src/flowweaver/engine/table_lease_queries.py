from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import TableLeaseRecord
from flowweaver.engine.table_lease_models import datetime_to_text as _datetime_to_text
from flowweaver.protocols.enums import TableLeaseStatus, TableLeaseType


def active_table_leases(
    session: Session,
    table_ref_id: str,
    now: datetime,
) -> list[TableLeaseRecord]:
    return list(
        session.scalars(
            select(TableLeaseRecord)
            .where(TableLeaseRecord.table_ref_id == table_ref_id)
            .where(TableLeaseRecord.status == TableLeaseStatus.ACTIVE.value)
            .where(TableLeaseRecord.expires_at > _datetime_to_text(now))
        )
    )


def expire_stale_table_leases(session: Session, now: datetime) -> int:
    stale_records = list(
        session.scalars(
            select(TableLeaseRecord)
            .where(TableLeaseRecord.status == TableLeaseStatus.ACTIVE.value)
            .where(TableLeaseRecord.expires_at <= _datetime_to_text(now))
        )
    )
    for record in stale_records:
        record.status = TableLeaseStatus.EXPIRED.value
        record.released_at = _datetime_to_text(now)
    return len(stale_records)


def conflicting_table_leases(
    requested_type: TableLeaseType,
    active_leases: list[TableLeaseRecord],
) -> list[TableLeaseRecord]:
    if requested_type == TableLeaseType.READ:
        return [
            record
            for record in active_leases
            if record.lease_type == TableLeaseType.WRITE.value
        ]
    return active_leases
