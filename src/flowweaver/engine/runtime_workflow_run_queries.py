from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowRunRecord
from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_workflow_record_mappers import _workflow_run_from_record
from flowweaver.protocols.enums import WorkflowRunStatus


def get_workflow_run_from_session(
    session: Session,
    workflow_run_id: str,
) -> WorkflowRun | None:
    record = session.get(WorkflowRunRecord, workflow_run_id)
    if record is None:
        return None
    return _workflow_run_from_record(record)


def list_workflow_runs_from_session(
    session: Session,
    *,
    workflow_id: str | None = None,
    statuses: Iterable[WorkflowRunStatus | str] | None = None,
    run_mode: str | None = None,
    trigger_source: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[WorkflowRun]:
    statement = select(WorkflowRunRecord).order_by(
        WorkflowRunRecord.started_at.desc(),
        WorkflowRunRecord.workflow_run_id,
    )
    if workflow_id is not None:
        statement = statement.where(WorkflowRunRecord.workflow_id == workflow_id)
    if statuses is not None:
        status_values = [
            status.value if isinstance(status, WorkflowRunStatus) else status
            for status in statuses
        ]
        statement = statement.where(WorkflowRunRecord.status.in_(status_values))
    if run_mode is not None:
        statement = statement.where(WorkflowRunRecord.run_mode == run_mode)
    if trigger_source is not None:
        statement = statement.where(WorkflowRunRecord.trigger_source == trigger_source)
    if offset > 0:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return [_workflow_run_from_record(record) for record in session.scalars(statement)]
