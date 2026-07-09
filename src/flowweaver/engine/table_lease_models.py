from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flowweaver.engine.db_models import TableLeaseRecord


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


def lease_from_record(record: TableLeaseRecord) -> TableLease:
    return TableLease(
        lease_id=record.lease_id,
        table_ref_id=record.table_ref_id,
        lease_type=record.lease_type,
        owner_id=record.owner_id,
        status=record.status,
        acquired_at=datetime_from_text(record.acquired_at),
        last_heartbeat_at=datetime_from_text(record.last_heartbeat_at),
        expires_at=datetime_from_text(record.expires_at),
        released_at=optional_datetime_from_text(record.released_at),
        metadata=json.loads(record.metadata_json),
    )


def json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def datetime_to_text(value: datetime) -> str:
    return value.isoformat()


def datetime_from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


def optional_datetime_from_text(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None
