from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import LoopRunRecord
from flowweaver.engine.runtime_loop_record_mappers import _loop_run_from_record
from flowweaver.engine.runtime_models import LoopRun
from flowweaver.engine.runtime_status_guards import (
    loop_run_status_values as _loop_run_status_values,
)
from flowweaver.protocols.enums import LoopRunStatus


def get_loop_run_from_session(
    session: Session,
    loop_run_id: str,
) -> LoopRun | None:
    record = session.get(LoopRunRecord, loop_run_id)
    if record is None:
        return None
    return _loop_run_from_record(record)


def get_loop_run_for_workflow_loop_from_session(
    session: Session,
    *,
    workflow_run_id: str,
    loop_id: str,
) -> LoopRun | None:
    record = session.scalar(
        select(LoopRunRecord)
        .where(LoopRunRecord.workflow_run_id == workflow_run_id)
        .where(LoopRunRecord.loop_id == loop_id)
    )
    if record is None:
        return None
    return _loop_run_from_record(record)


def list_loop_runs_from_session(
    session: Session,
    workflow_run_id: str,
    *,
    statuses: Iterable[LoopRunStatus | str] | None = None,
) -> list[LoopRun]:
    statement = (
        select(LoopRunRecord)
        .where(LoopRunRecord.workflow_run_id == workflow_run_id)
        .order_by(LoopRunRecord.created_at, LoopRunRecord.loop_run_id)
    )
    if statuses is not None:
        statement = statement.where(
            LoopRunRecord.status.in_(_loop_run_status_values(statuses))
        )
    return [_loop_run_from_record(record) for record in session.scalars(statement)]
