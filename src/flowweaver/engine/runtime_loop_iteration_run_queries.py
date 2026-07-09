from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import LoopIterationRunRecord
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_run_from_record,
)
from flowweaver.engine.runtime_models import LoopIterationRun
from flowweaver.engine.runtime_status_guards import (
    loop_iteration_status_values as _loop_iteration_status_values,
)
from flowweaver.protocols.enums import LoopIterationRunStatus


def get_loop_iteration_run_from_session(
    session: Session,
    loop_iteration_id: str,
) -> LoopIterationRun | None:
    record = session.get(LoopIterationRunRecord, loop_iteration_id)
    if record is None:
        return None
    return _loop_iteration_run_from_record(record)


def get_loop_iteration_run_for_index_from_session(
    session: Session,
    *,
    loop_run_id: str,
    iteration_index: int,
) -> LoopIterationRun | None:
    record = session.scalar(
        select(LoopIterationRunRecord)
        .where(LoopIterationRunRecord.loop_run_id == loop_run_id)
        .where(LoopIterationRunRecord.iteration_index == iteration_index)
    )
    if record is None:
        return None
    return _loop_iteration_run_from_record(record)


def list_loop_iteration_runs_from_session(
    session: Session,
    loop_run_id: str,
    *,
    statuses: Iterable[LoopIterationRunStatus | str] | None = None,
) -> list[LoopIterationRun]:
    statement = (
        select(LoopIterationRunRecord)
        .where(LoopIterationRunRecord.loop_run_id == loop_run_id)
        .order_by(LoopIterationRunRecord.iteration_index)
    )
    if statuses is not None:
        statement = statement.where(
            LoopIterationRunRecord.status.in_(
                _loop_iteration_status_values(statuses)
            )
        )
    return [
        _loop_iteration_run_from_record(record)
        for record in session.scalars(statement)
    ]
