from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import LoopIterationNodeRunRecord
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_node_run_from_record,
)
from flowweaver.engine.runtime_models import LoopIterationNodeRun


def get_loop_iteration_node_run_from_session(
    session: Session,
    *,
    loop_iteration_id: str,
    node_run_id: str,
) -> LoopIterationNodeRun | None:
    record = session.get(
        LoopIterationNodeRunRecord,
        {
            "loop_iteration_id": loop_iteration_id,
            "node_run_id": node_run_id,
        },
    )
    if record is None:
        return None
    return _loop_iteration_node_run_from_record(record)


def list_loop_iteration_node_runs_from_session(
    session: Session,
    loop_iteration_id: str,
    *,
    node_instance_id: str | None = None,
    role: str | None = None,
) -> list[LoopIterationNodeRun]:
    statement = (
        select(LoopIterationNodeRunRecord)
        .where(LoopIterationNodeRunRecord.loop_iteration_id == loop_iteration_id)
        .order_by(
            LoopIterationNodeRunRecord.role,
            LoopIterationNodeRunRecord.node_instance_id,
            LoopIterationNodeRunRecord.node_run_id,
        )
    )
    if node_instance_id is not None:
        statement = statement.where(
            LoopIterationNodeRunRecord.node_instance_id == node_instance_id
        )
    if role is not None:
        statement = statement.where(LoopIterationNodeRunRecord.role == role)
    return [
        _loop_iteration_node_run_from_record(record)
        for record in session.scalars(statement)
    ]


def list_loop_iteration_node_runs_by_node_run_from_session(
    session: Session,
    node_run_id: str,
) -> list[LoopIterationNodeRun]:
    statement = (
        select(LoopIterationNodeRunRecord)
        .where(LoopIterationNodeRunRecord.node_run_id == node_run_id)
        .order_by(
            LoopIterationNodeRunRecord.loop_iteration_id,
            LoopIterationNodeRunRecord.role,
        )
    )
    return [
        _loop_iteration_node_run_from_record(record)
        for record in session.scalars(statement)
    ]
