from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import AuditEventRecord, TableLeaseRecord
from flowweaver.protocols.enums import TableLeaseStatus, TableLeaseType


@dataclass(frozen=True)
class TableLease:
    lease_id: str
    table_ref_id: str
    lease_type: str
    owner_id: str
    status: str
    acquired_at: datetime
    last_heartbeat_at: datetime
    expires_at: datetime
    released_at: datetime | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LeaseAcquireResult:
    granted: bool
    lease: TableLease | None
    conflict_lease_ids: list[str]
    reason: str | None = None


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
            self._audit(
                session,
                action="heartbeat",
                result="granted",
                lease=record,
                summary={"ttl_seconds": ttl_seconds},
            )
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
            self._audit(
                session,
                action="release",
                result="granted",
                lease=record,
                summary={},
            )
            return True

    def active_read_count(self, table_ref_id: str) -> int:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            return len(
                [
                    record
                    for record in self._active_leases(session, table_ref_id, now)
                    if record.lease_type == TableLeaseType.READ.value
                ]
            )

    def can_acquire_write(self, table_ref_id: str) -> bool:
        now = utc_now()
        with self._immediate_session() as session:
            self._expire_stale_leases(session, now)
            return not self._active_leases(session, table_ref_id, now)

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
            active_leases = self._active_leases(session, table_ref_id, now)
            conflicts = _conflicts_for(lease_type, active_leases)
            if conflicts:
                self._audit_conflict(
                    session,
                    table_ref_id=table_ref_id,
                    owner_id=owner_id,
                    lease_type=lease_type,
                    conflict_lease_ids=[record.lease_id for record in conflicts],
                )
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
            self._audit(
                session,
                action=f"acquire_{lease_type.value.lower()}",
                result="granted",
                lease=record,
                summary={"ttl_seconds": ttl_seconds},
            )
            return LeaseAcquireResult(
                granted=True,
                lease=_lease_from_record(record),
                conflict_lease_ids=[],
            )

    def _active_leases(
        self,
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

    def _expire_stale_leases(self, session: Session, now: datetime) -> int:
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
            self._audit(
                session,
                action="expire",
                result="granted",
                lease=record,
                summary={},
            )
        return len(stale_records)

    def _audit(
        self,
        session: Session,
        *,
        action: str,
        result: str,
        lease: TableLeaseRecord,
        summary: dict[str, Any],
    ) -> None:
        session.add(
            AuditEventRecord(
                event_id=new_id(),
                event_type="TABLE_LEASE",
                timestamp=_datetime_to_text(utc_now()),
                workflow_run_id=None,
                node_run_id=None,
                subject_type="ENGINE_HOST",
                subject_id=lease.owner_id,
                resource_type="TABLE_REF",
                resource_id=lease.table_ref_id,
                action=action,
                result=result,
                summary_json=_json_dumps(
                    {
                        "lease_id": lease.lease_id,
                        "lease_type": lease.lease_type,
                        **summary,
                    }
                ),
            )
        )

    def _audit_conflict(
        self,
        session: Session,
        *,
        table_ref_id: str,
        owner_id: str,
        lease_type: TableLeaseType,
        conflict_lease_ids: list[str],
    ) -> None:
        session.add(
            AuditEventRecord(
                event_id=new_id(),
                event_type="TABLE_LEASE",
                timestamp=_datetime_to_text(utc_now()),
                workflow_run_id=None,
                node_run_id=None,
                subject_type="ENGINE_HOST",
                subject_id=owner_id,
                resource_type="TABLE_REF",
                resource_id=table_ref_id,
                action=f"acquire_{lease_type.value.lower()}",
                result="conflict",
                summary_json=_json_dumps(
                    {
                        "lease_type": lease_type.value,
                        "conflict_lease_ids": conflict_lease_ids,
                    }
                ),
            )
        )

    @contextmanager
    def _immediate_session(self) -> Iterator[Session]:
        connection: Connection = self._engine.connect()
        session = Session(bind=connection, expire_on_commit=False)
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            yield session
            session.flush()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            session.close()
            connection.close()


def _conflicts_for(
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


def _lease_from_record(record: TableLeaseRecord) -> TableLease:
    return TableLease(
        lease_id=record.lease_id,
        table_ref_id=record.table_ref_id,
        lease_type=record.lease_type,
        owner_id=record.owner_id,
        status=record.status,
        acquired_at=_datetime_from_text(record.acquired_at),
        last_heartbeat_at=_datetime_from_text(record.last_heartbeat_at),
        expires_at=_datetime_from_text(record.expires_at),
        released_at=_optional_datetime_from_text(record.released_at),
        metadata=json.loads(record.metadata_json),
    )


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _datetime_to_text(value: datetime) -> str:
    return value.isoformat()


def _datetime_from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime_from_text(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None
