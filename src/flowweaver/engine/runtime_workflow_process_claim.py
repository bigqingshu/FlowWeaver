from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowProcessRecord, WorkflowRunRecord
from flowweaver.engine.runtime_models import WorkflowProcess
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_status_guards import (
    ACTIVE_WORKFLOW_PROCESS_STATUSES as _ACTIVE_WORKFLOW_PROCESS_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUSES as _TERMINAL_WORKFLOW_STATUSES,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
)
from flowweaver.protocols.enums import WorkflowProcessStatus


def claim_workflow_process_in_session(
    session: Session,
    workflow_run_id: str,
    *,
    process_id: str,
    fencing_token: str,
    now: datetime,
) -> WorkflowProcess | None:
    run = session.get(WorkflowRunRecord, workflow_run_id)
    if run is None or run.status in _TERMINAL_WORKFLOW_STATUSES:
        return None
    active_process = session.scalar(
        select(WorkflowProcessRecord)
        .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
        .where(WorkflowProcessRecord.status.in_(_ACTIVE_WORKFLOW_PROCESS_STATUSES))
        .order_by(WorkflowProcessRecord.started_at.desc())
    )
    if active_process is not None:
        return None
    generation = run.process_generation + 1
    run.owner_process_id = process_id
    run.process_generation = generation
    run.fencing_token = fencing_token
    run.state_version += 1
    record = WorkflowProcessRecord(
        process_id=process_id,
        workflow_run_id=workflow_run_id,
        os_pid=None,
        process_generation=generation,
        fencing_token=fencing_token,
        status=WorkflowProcessStatus.STARTING.value,
        started_at=_datetime_to_text(now),
        last_heartbeat_at=None,
        cancel_requested_at=None,
        exited_at=None,
        exit_code=None,
        error_json=None,
    )
    session.add(record)
    return _workflow_process_from_record(record)
