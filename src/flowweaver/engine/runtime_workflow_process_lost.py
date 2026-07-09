from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowProcessRecord
from flowweaver.engine.runtime_models import WorkflowProcess
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_status_guards import (
    ACTIVE_WORKFLOW_PROCESS_STATUSES as _ACTIVE_WORKFLOW_PROCESS_STATUSES,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
)
from flowweaver.protocols.enums import WorkflowProcessStatus


def mark_lost_workflow_processes_in_session(
    session: Session,
    *,
    stale_before: datetime,
    starting_stale_before: datetime | None,
    now: datetime,
) -> list[WorkflowProcess]:
    lost: list[WorkflowProcess] = []
    records = list(
        session.scalars(
            select(WorkflowProcessRecord).where(
                WorkflowProcessRecord.status.in_(_ACTIVE_WORKFLOW_PROCESS_STATUSES)
            )
        )
    )
    for record in records:
        if record.status == WorkflowProcessStatus.STARTING.value:
            if (
                starting_stale_before is None
                or record.started_at > _datetime_to_text(starting_stale_before)
            ):
                continue
        elif (
            record.last_heartbeat_at is None
            or record.last_heartbeat_at > _datetime_to_text(stale_before)
        ):
            continue
        record.status = WorkflowProcessStatus.LOST.value
        record.exited_at = _datetime_to_text(now)
        lost.append(_workflow_process_from_record(record))
    return lost
