from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import (
    NodeRunRecord,
    WorkflowProcessRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_status_guards import (
    INTERRUPTED_NODE_STATUSES as _INTERRUPTED_NODE_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUSES as _TERMINAL_WORKFLOW_STATUSES,
)
from flowweaver.engine.runtime_workflow_record_mappers import _workflow_run_from_record
from flowweaver.protocols.enums import NodeRunStatus, WorkflowRunStatus


def abort_workflow_run_for_process_in_session(
    session: Session,
    process_id: str,
    *,
    reason: str,
    now: datetime,
) -> WorkflowRun | None:
    process = session.get(WorkflowProcessRecord, process_id)
    if process is None:
        return None
    run = session.get(WorkflowRunRecord, process.workflow_run_id)
    if run is None:
        return None
    statement = (
        update(WorkflowRunRecord)
        .where(WorkflowRunRecord.workflow_run_id == run.workflow_run_id)
        .where(WorkflowRunRecord.status.notin_(_TERMINAL_WORKFLOW_STATUSES))
        .where(WorkflowRunRecord.owner_process_id == process.process_id)
        .where(WorkflowRunRecord.process_generation == process.process_generation)
        .values(
            status=WorkflowRunStatus.ABORTED.value,
            state_version=WorkflowRunRecord.state_version + 1,
            finished_at=_datetime_to_text(now),
            error_json=_json_dumps(
                {
                    "reason": reason,
                    "process_id": process.process_id,
                    "process_generation": process.process_generation,
                }
            ),
        )
    )
    result = cast(CursorResult[Any], session.execute(statement))
    if result.rowcount != 1:
        return _workflow_run_from_record(run)
    session.execute(
        update(NodeRunRecord)
        .where(NodeRunRecord.workflow_run_id == run.workflow_run_id)
        .where(NodeRunRecord.status.in_(_INTERRUPTED_NODE_STATUSES))
        .values(
            status=NodeRunStatus.CANCELLED.value,
            state_version=NodeRunRecord.state_version + 1,
            finished_at=_datetime_to_text(now),
            error_json=_json_dumps(
                {
                    "reason": reason,
                    "process_id": process.process_id,
                    "process_generation": process.process_generation,
                }
            ),
        )
    )
    loaded = session.get(WorkflowRunRecord, run.workflow_run_id)
    if loaded is None:
        return None
    return _workflow_run_from_record(loaded)
