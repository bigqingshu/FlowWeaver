from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import NodeRunRecord
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import _node_run_from_record


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
) -> list[NodeRun]:
    records = session.scalars(
        select(NodeRunRecord)
        .where(NodeRunRecord.workflow_run_id == workflow_run_id)
        .order_by(NodeRunRecord.node_instance_id)
    ).all()
    return [_node_run_from_record(record) for record in records]
