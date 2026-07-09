from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import NodeTaskRecord, NodeTaskResultRecord
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_from_record,
    _node_task_result_from_record,
)
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


def get_node_task_from_session(
    session: Session,
    task_id: str,
) -> NodeTaskModel | None:
    record = session.get(NodeTaskRecord, task_id)
    if record is None:
        return None
    return _node_task_from_record(record)


def get_node_task_result_from_session(
    session: Session,
    *,
    task_id: str,
    result_id: str,
) -> NodeTaskResultModel | None:
    record = session.scalar(
        select(NodeTaskResultRecord)
        .where(NodeTaskResultRecord.task_id == task_id)
        .where(NodeTaskResultRecord.result_id == result_id)
    )
    if record is None:
        return None
    return _node_task_result_from_record(record)


def get_latest_succeeded_node_task_result_for_node_run_from_session(
    session: Session,
    node_run_id: str,
) -> NodeTaskResultModel | None:
    record = session.scalar(
        select(NodeTaskResultRecord)
        .where(NodeTaskResultRecord.node_run_id == node_run_id)
        .where(NodeTaskResultRecord.status == NodeResultStatus.SUCCEEDED.value)
        .order_by(
            NodeTaskResultRecord.finished_at.desc(),
            NodeTaskResultRecord.result_id.desc(),
        )
    )
    if record is None:
        return None
    return _node_task_result_from_record(record)
