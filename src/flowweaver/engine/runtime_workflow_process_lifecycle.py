from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowProcessRecord
from flowweaver.engine.runtime_models import WorkflowProcess
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_status_guards import (
    ACTIVE_WORKFLOW_PROCESS_STATUSES as _ACTIVE_WORKFLOW_PROCESS_STATUSES,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
)
from flowweaver.protocols.enums import WorkflowProcessStatus


def update_workflow_process_pid_in_session(
    session: Session,
    process_id: str,
    os_pid: int,
) -> WorkflowProcess | None:
    record = session.get(WorkflowProcessRecord, process_id)
    if record is None:
        return None
    record.os_pid = os_pid
    return _workflow_process_from_record(record)


def record_workflow_process_heartbeat_in_session(
    session: Session,
    process_id: str,
    *,
    process_generation: int | None,
    now: datetime,
) -> WorkflowProcess | None:
    record = session.get(WorkflowProcessRecord, process_id)
    if record is None:
        return None
    if (
        process_generation is not None
        and record.process_generation != process_generation
    ):
        return None
    if record.status not in _ACTIVE_WORKFLOW_PROCESS_STATUSES:
        return None
    if record.status == WorkflowProcessStatus.STARTING.value:
        record.status = WorkflowProcessStatus.RUNNING.value
    record.last_heartbeat_at = _datetime_to_text(now)
    return _workflow_process_from_record(record)


def request_workflow_process_cancel_in_session(
    session: Session,
    workflow_run_id: str,
    *,
    now: datetime,
) -> WorkflowProcess | None:
    record = session.scalar(
        select(WorkflowProcessRecord)
        .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
        .order_by(WorkflowProcessRecord.started_at.desc())
    )
    if record is None:
        return None
    if record.status in {
        WorkflowProcessStatus.STARTING.value,
        WorkflowProcessStatus.RUNNING.value,
    }:
        record.status = WorkflowProcessStatus.CANCEL_REQUESTED.value
        record.cancel_requested_at = _datetime_to_text(now)
    return _workflow_process_from_record(record)


def mark_workflow_process_exited_in_session(
    session: Session,
    process_id: str,
    *,
    exit_code: int,
    error: dict[str, Any] | None,
    now: datetime,
) -> WorkflowProcess | None:
    record = session.get(WorkflowProcessRecord, process_id)
    if record is None:
        return None
    record.status = (
        WorkflowProcessStatus.EXITED.value
        if exit_code == 0
        else WorkflowProcessStatus.FAILED.value
    )
    record.exited_at = _datetime_to_text(now)
    record.exit_code = exit_code
    record.error_json = _json_dumps(error) if error else None
    return _workflow_process_from_record(record)
