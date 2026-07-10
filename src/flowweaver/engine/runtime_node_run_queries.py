from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import NodeRunRecord
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import _node_run_from_record
from flowweaver.engine.runtime_status_guards import (
    node_run_status_values as _node_run_status_values,
)
from flowweaver.protocols.enums import NodeRunStatus


def get_node_run_from_session(
    session: Session,
    node_run_id: str,
) -> NodeRun | None:
    record = session.get(NodeRunRecord, node_run_id)
    if record is None:
        return None
    return _node_run_from_record(record)


def get_node_run_for_instance_from_session(
    session: Session,
    *,
    workflow_run_id: str,
    node_instance_id: str,
) -> NodeRun | None:
    record = session.scalar(
        select(NodeRunRecord)
        .where(NodeRunRecord.workflow_run_id == workflow_run_id)
        .where(NodeRunRecord.node_instance_id == node_instance_id)
    )
    if record is None:
        return None
    return _node_run_from_record(record)


def list_node_runs_by_ids_from_session(
    session: Session,
    node_run_ids: list[str],
) -> list[NodeRun]:
    if not node_run_ids:
        return []
    records = session.scalars(
        select(NodeRunRecord)
        .where(NodeRunRecord.node_run_id.in_(node_run_ids))
        .order_by(NodeRunRecord.node_instance_id, NodeRunRecord.node_run_id)
    ).all()
    return [_node_run_from_record(record) for record in records]


def list_node_runs_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    statuses: Iterable[NodeRunStatus | str] | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[NodeRun]:
    statement = (
        select(NodeRunRecord)
        .where(NodeRunRecord.workflow_run_id == workflow_run_id)
        .order_by(NodeRunRecord.node_instance_id, NodeRunRecord.node_run_id)
    )
    if statuses is not None:
        statement = statement.where(
            NodeRunRecord.status.in_(_node_run_status_values(statuses))
        )
    statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    records = session.scalars(statement).all()
    return [_node_run_from_record(record) for record in records]


def count_node_runs_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    statuses: Iterable[NodeRunStatus | str] | None = None,
) -> int:
    statement = select(func.count()).select_from(NodeRunRecord).where(
        NodeRunRecord.workflow_run_id == workflow_run_id
    )
    if statuses is not None:
        statement = statement.where(
            NodeRunRecord.status.in_(_node_run_status_values(statuses))
        )
    return int(session.scalar(statement) or 0)
