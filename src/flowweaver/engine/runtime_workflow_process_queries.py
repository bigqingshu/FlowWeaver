from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowProcessRecord
from flowweaver.engine.runtime_models import WorkflowProcess
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
)


def get_workflow_process_from_session(
    session: Session,
    process_id: str,
) -> WorkflowProcess | None:
    record = session.get(WorkflowProcessRecord, process_id)
    if record is None:
        return None
    return _workflow_process_from_record(record)


def get_workflow_process_for_run_from_session(
    session: Session,
    workflow_run_id: str,
) -> WorkflowProcess | None:
    record = session.scalar(
        select(WorkflowProcessRecord)
        .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
        .order_by(WorkflowProcessRecord.started_at.desc())
    )
    if record is None:
        return None
    return _workflow_process_from_record(record)
