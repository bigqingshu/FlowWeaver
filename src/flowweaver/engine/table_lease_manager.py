from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import TableLeaseRecord
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.table_lease_models import (
    LeaseAcquireResult as LeaseAcquireResult,
)
from flowweaver.engine.table_lease_models import (
    TableLease as TableLease,
)
from flowweaver.engine.table_lease_models import (
    datetime_to_text as _datetime_to_text,
)
from flowweaver.engine.table_lease_models import (
    json_dumps as _json_dumps,
)
from flowweaver.engine.table_lease_models import (
    lease_from_record as _lease_from_record,
)
from flowweaver.engine.table_lease_queries import (
    active_table_leases as _active_table_leases,
)
from flowweaver.engine.table_lease_queries import (
    conflicting_table_leases as _conflicting_table_leases,
)
from flowweaver.engine.table_lease_queries import (
    expire_stale_table_leases as _expire_stale_table_leases,
)
from flowweaver.protocols.enums import TableLeaseStatus, TableLeaseType


class TableLeaseManager:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def acquire_read_lease(
        self,
        *,
        table_ref_id: str,
        owner_id: str,
        ttl_seconds: int,
        metadata: dict[str, Any] | None = None,
    ) -> LeaseAcquireResult:
        return self._acquire_lease(
            table_ref_id=table_ref_id,
            owner_id=owner_id,
            lease_type=TableLeaseType.READ,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

    def acquire_write_lease(
        self,
        *,
        table_ref_id: str,
        owner_id: str,
        ttl_seconds: int,
        metadata: dict[str, Any] | None = None,
    ) -> LeaseAcquireResult:
        return self._acquire_lease(
            table_ref_id=table_ref_id,
            owner_id=owner_id,
            lease_type=TableLeaseType.WRITE,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

    def heartbeat(self, lease_id: str, *, ttl_seconds: int) -> TableLease | None:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            record = session.get(TableLeaseRecord, lease_id)
            if record is None or record.status != TableLeaseStatus.ACTIVE.value:
                return None
            record.last_heartbeat_at = _datetime_to_text(now)
            record.expires_at = _datetime_to_text(now + timedelta(seconds=ttl_seconds))
            return _lease_from_record(record)

    def release(self, lease_id: str) -> bool:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            record = session.get(TableLeaseRecord, lease_id)
            if record is None or record.status != TableLeaseStatus.ACTIVE.value:
                return False
            record.status = TableLeaseStatus.RELEASED.value
            record.released_at = _datetime_to_text(now)
            return True

    def active_read_count(self, table_ref_id: str) -> int:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            return len(
                [
                    record
                    for record in _active_table_leases(session, table_ref_id, now)
                    if record.lease_type == TableLeaseType.READ.value
                ]
            )

    def can_acquire_write(self, table_ref_id: str) -> bool:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            return not _active_table_leases(session, table_ref_id, now)

    def expire_stale_leases(self) -> int:
        with self._immediate_session() as session:
            return self._expire_stale_leases(session, utc_now())

    def _acquire_lease(
        self,
        *,
        table_ref_id: str,
        owner_id: str,
        lease_type: TableLeaseType,
        ttl_seconds: int,
        metadata: dict[str, Any],
    ) -> LeaseAcquireResult:
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            active_leases = _active_table_leases(session, table_ref_id, now)
            conflicts = _conflicting_table_leases(lease_type, active_leases)
            if conflicts:
                return LeaseAcquireResult(
                    granted=False,
                    lease=None,
                    conflict_lease_ids=[record.lease_id for record in conflicts],
                    reason="TABLE_LEASE_CONFLICT",
                )

            record = TableLeaseRecord(
                lease_id=new_id(),
                table_ref_id=table_ref_id,
                lease_type=lease_type.value,
                owner_id=owner_id,
                status=TableLeaseStatus.ACTIVE.value,
                acquired_at=_datetime_to_text(now),
                last_heartbeat_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
                metadata_json=_json_dumps(metadata),
            )
            session.add(record)
            return LeaseAcquireResult(
                granted=True,
                lease=_lease_from_record(record),
                conflict_lease_ids=[],
            )

    def _expire_stale_leases(self, session: Session, now: datetime) -> int:
        return _expire_stale_table_leases(session, now)

    def _immediate_session(self) -> AbstractContextManager[Session]:
        return immediate_session(self._engine)
