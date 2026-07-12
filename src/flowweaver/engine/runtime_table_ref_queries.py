from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from flowweaver.engine.db_models import (
    DataRefRecord,
    NodeRunRecord,
    NodeTaskResultOutputBindingRecord,
    NodeTaskResultRecord,
)
from flowweaver.engine.runtime_models import (
    RunTableCleanupCandidate,
    RunTableDirectoryEntry,
    RunTableResultBinding,
)
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
_CLEANUP_EXCLUDED_STATUSES = (
    LifecycleStatus.RELEASED.value,
    LifecycleStatus.RETIRED.value,
    LifecycleStatus.ORPHANED.value,
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


def list_table_ref_cleanup_candidates_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    after_created_at: str | None = None,
    after_table_ref_id: str | None = None,
    limit: int,
) -> list[RunTableCleanupCandidate]:
    statement = (
        select(DataRefRecord.table_ref_id, DataRefRecord.created_at)
        .where(DataRefRecord.workflow_run_id == workflow_run_id)
        .where(
            DataRefRecord.lifecycle_status.notin_(_CLEANUP_EXCLUDED_STATUSES)
        )
        .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
        .limit(limit)
    )
    if after_created_at is not None and after_table_ref_id is not None:
        statement = statement.where(
            or_(
                DataRefRecord.created_at > after_created_at,
                and_(
                    DataRefRecord.created_at == after_created_at,
                    DataRefRecord.table_ref_id > after_table_ref_id,
                ),
            )
        )
    return [
        RunTableCleanupCandidate(
            table_ref_id=table_ref_id,
            created_at=created_at,
        )
        for table_ref_id, created_at in session.execute(statement).all()
    ]


def list_table_refs_by_ids_from_session(
    session: Session,
    table_ref_ids: list[str],
) -> list[TableRefModel]:
    if not table_ref_ids:
        return []
    records = session.scalars(
        select(DataRefRecord)
        .where(DataRefRecord.table_ref_id.in_(table_ref_ids))
        .order_by(DataRefRecord.table_ref_id)
    ).all()
    return [_table_ref_from_record(record) for record in records]


def list_table_ref_directory_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    node_run_id: str | None = None,
    table_type: str | None = None,
    lifecycle_statuses: Iterable[LifecycleStatus | str] | None = None,
    logical_table_id: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[RunTableDirectoryEntry]:
    statement = (
        select(DataRefRecord, NodeRunRecord.node_instance_id)
        .outerjoin(
            NodeRunRecord,
            DataRefRecord.node_run_id == NodeRunRecord.node_run_id,
        )
        .where(
            *_table_ref_directory_conditions(
                workflow_run_id=workflow_run_id,
                node_run_id=node_run_id,
                table_type=table_type,
                lifecycle_statuses=lifecycle_statuses,
                logical_table_id=logical_table_id,
            )
        )
        .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
        .offset(offset)
    )
    if limit is not None:
        statement = statement.limit(limit)
    rows = session.execute(statement).all()
    bindings_by_ref = _latest_result_bindings_by_output_ref_id(
        session,
        [record.table_ref_id for record, _source_node_instance_id in rows],
    )
    return [
        RunTableDirectoryEntry(
            table_ref=_table_ref_from_record(record),
            source_node_instance_id=source_node_instance_id,
            result_bindings=bindings_by_ref.get(record.table_ref_id, ()),
        )
        for record, source_node_instance_id in rows
    ]


def list_table_ref_directory_by_ids_from_session(
    session: Session,
    table_ref_ids: list[str],
) -> list[RunTableDirectoryEntry]:
    if not table_ref_ids:
        return []
    rows = session.execute(
        select(DataRefRecord, NodeRunRecord.node_instance_id)
        .outerjoin(
            NodeRunRecord,
            DataRefRecord.node_run_id == NodeRunRecord.node_run_id,
        )
        .where(DataRefRecord.table_ref_id.in_(table_ref_ids))
        .order_by(DataRefRecord.table_ref_id)
    ).all()
    bindings_by_ref = _latest_result_bindings_by_output_ref_id(
        session,
        [record.table_ref_id for record, _source_node_instance_id in rows],
    )
    return [
        RunTableDirectoryEntry(
            table_ref=_table_ref_from_record(record),
            source_node_instance_id=source_node_instance_id,
            result_bindings=bindings_by_ref.get(record.table_ref_id, ()),
        )
        for record, source_node_instance_id in rows
    ]


def _latest_result_bindings_by_output_ref_id(
    session: Session,
    output_ref_ids: list[str],
) -> dict[str, tuple[RunTableResultBinding, ...]]:
    if not output_ref_ids:
        return {}
    ranked_bindings = (
        select(
            NodeTaskResultOutputBindingRecord.output_ref_id.label(
                "output_ref_id"
            ),
            NodeTaskResultOutputBindingRecord.node_run_id.label("node_run_id"),
            NodeRunRecord.node_instance_id.label("node_instance_id"),
            NodeTaskResultOutputBindingRecord.output_slot.label("output_slot"),
            func.row_number()
            .over(
                partition_by=(
                    NodeTaskResultOutputBindingRecord.node_run_id,
                    NodeTaskResultOutputBindingRecord.output_slot,
                ),
                order_by=(
                    NodeTaskResultRecord.finished_at.desc(),
                    NodeTaskResultOutputBindingRecord.result_id.desc(),
                ),
            )
            .label("binding_rank"),
        )
        .join(
            NodeTaskResultRecord,
            NodeTaskResultOutputBindingRecord.result_id
            == NodeTaskResultRecord.result_id,
        )
        .join(
            NodeRunRecord,
            NodeTaskResultOutputBindingRecord.node_run_id
            == NodeRunRecord.node_run_id,
        )
        .subquery()
    )
    rows = session.execute(
        select(
            ranked_bindings.c.output_ref_id,
            ranked_bindings.c.node_run_id,
            ranked_bindings.c.node_instance_id,
            ranked_bindings.c.output_slot,
        )
        .where(ranked_bindings.c.binding_rank == 1)
        .where(ranked_bindings.c.output_ref_id.in_(output_ref_ids))
        .order_by(
            ranked_bindings.c.output_ref_id,
            ranked_bindings.c.node_instance_id,
            ranked_bindings.c.node_run_id,
            ranked_bindings.c.output_slot,
        )
    ).all()
    slots_by_binding: dict[tuple[str, str, str], list[str]] = {}
    for output_ref_id, node_run_id, node_instance_id, output_slot in rows:
        key = (output_ref_id, node_run_id, node_instance_id)
        slots_by_binding.setdefault(key, []).append(output_slot)
    result: dict[str, list[RunTableResultBinding]] = {}
    for (output_ref_id, node_run_id, node_instance_id), output_slots in (
        slots_by_binding.items()
    ):
        result.setdefault(output_ref_id, []).append(
            RunTableResultBinding(
                node_run_id=node_run_id,
                node_instance_id=node_instance_id,
                output_slots=tuple(output_slots),
            )
        )
    return {
        output_ref_id: tuple(bindings)
        for output_ref_id, bindings in result.items()
    }


def count_table_ref_directory_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    node_run_id: str | None = None,
    table_type: str | None = None,
    lifecycle_statuses: Iterable[LifecycleStatus | str] | None = None,
    logical_table_id: str | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(DataRefRecord)
        .where(
            *_table_ref_directory_conditions(
                workflow_run_id=workflow_run_id,
                node_run_id=node_run_id,
                table_type=table_type,
                lifecycle_statuses=lifecycle_statuses,
                logical_table_id=logical_table_id,
            )
        )
    )
    return int(session.scalar(statement) or 0)


def _table_ref_directory_conditions(
    *,
    workflow_run_id: str,
    node_run_id: str | None,
    table_type: str | None,
    lifecycle_statuses: Iterable[LifecycleStatus | str] | None,
    logical_table_id: str | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [
        DataRefRecord.workflow_run_id == workflow_run_id
    ]
    if node_run_id is not None:
        conditions.append(DataRefRecord.node_run_id == node_run_id)
    if logical_table_id is not None:
        conditions.append(DataRefRecord.logical_table_id == logical_table_id)
    if lifecycle_statuses is not None:
        lifecycle_values = [
            status.value if isinstance(status, LifecycleStatus) else status
            for status in lifecycle_statuses
        ]
        conditions.append(DataRefRecord.lifecycle_status.in_(lifecycle_values))
    if table_type == "current_table":
        conditions.append(DataRefRecord.role == TableRole.CURRENT.value)
    elif table_type == "memory_table":
        conditions.append(
            and_(
                DataRefRecord.storage_kind == TableStorageKind.MEMORY.value,
                DataRefRecord.role != TableRole.CURRENT.value,
            )
        )
    elif table_type == "runtime_sql_table":
        conditions.append(
            and_(
                DataRefRecord.storage_kind == TableStorageKind.RUNTIME_SQL.value,
                DataRefRecord.role != TableRole.CURRENT.value,
            )
        )
    elif table_type == "external_sql_table":
        conditions.append(
            and_(
                DataRefRecord.storage_kind == TableStorageKind.EXTERNAL_SQL.value,
                DataRefRecord.role != TableRole.CURRENT.value,
            )
        )
    elif table_type is not None:
        raise ValueError(f"Unsupported table type: {table_type}")
    return conditions


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
