from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import DataRefRecord
from flowweaver.engine.runtime_record_mappers import _table_ref_from_record
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import TableRefModel

_AVAILABLE_LOGICAL_TABLE_STATUSES = (
    LifecycleStatus.ACTIVE.value,
    LifecycleStatus.PUBLISHED.value,
)


def get_table_ref_from_session(
    session: Session,
    table_ref_id: str,
) -> TableRefModel | None:
    record = session.get(DataRefRecord, table_ref_id)
    if record is None:
        return None
    return _table_ref_from_record(record)


def get_latest_table_ref_by_logical_identity_from_session(
    session: Session,
    *,
    workflow_run_id: str,
    storage_kind: TableStorageKind,
    role: TableRole,
    logical_table_id: str,
) -> TableRefModel | None:
    record = session.scalar(
        select(DataRefRecord)
        .where(DataRefRecord.workflow_run_id == workflow_run_id)
        .where(DataRefRecord.storage_kind == storage_kind.value)
        .where(DataRefRecord.role == role.value)
        .where(DataRefRecord.logical_table_id == logical_table_id)
        .where(
            DataRefRecord.lifecycle_status.in_(
                _AVAILABLE_LOGICAL_TABLE_STATUSES
            )
        )
        .order_by(
            DataRefRecord.version.desc(),
            DataRefRecord.created_at.desc(),
            DataRefRecord.table_ref_id.desc(),
        )
        .limit(1)
    )
    if record is None:
        return None
    return _table_ref_from_record(record)


def list_table_refs_by_workflow_run_from_session(
    session: Session,
    workflow_run_id: str,
) -> list[TableRefModel]:
    records = session.scalars(
        select(DataRefRecord)
        .where(DataRefRecord.workflow_run_id == workflow_run_id)
        .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
    ).all()
    return [_table_ref_from_record(record) for record in records]


def list_table_refs_by_node_run_from_session(
    session: Session,
    *,
    workflow_run_id: str,
    node_run_id: str,
) -> list[TableRefModel]:
    records = session.scalars(
        select(DataRefRecord)
        .where(DataRefRecord.workflow_run_id == workflow_run_id)
        .where(DataRefRecord.node_run_id == node_run_id)
        .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
    ).all()
    return [_table_ref_from_record(record) for record in records]
