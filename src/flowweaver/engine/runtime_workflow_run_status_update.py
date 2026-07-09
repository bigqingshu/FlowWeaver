from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowRunRecord
from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_record_mappers import (
    _json_dumps,
    _optional_datetime_to_text,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUSES as _TERMINAL_WORKFLOW_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    WORKFLOW_RUN_STATUS_SOURCES as _WORKFLOW_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    optional_completion_reason_value as _optional_completion_reason_value,
)
from flowweaver.engine.runtime_status_guards import (
    workflow_run_status_values as _workflow_run_status_values,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_run_from_record,
)
from flowweaver.protocols.enums import (
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)


def update_workflow_run_status_in_session(
    session: Session,
    workflow_run_id: str,
    status: WorkflowRunStatus,
    *,
    finished_at: datetime | None = None,
    completion_reason: WorkflowRunCompletionReason | str | None = None,
    error: dict[str, Any] | None = None,
    expected_state_version: int | None = None,
    allowed_source_statuses: Iterable[WorkflowRunStatus | str] | None = None,
    owner_process_id: str | None = None,
    process_generation: int | None = None,
) -> WorkflowRun | None:
    source_statuses = (
        _workflow_run_status_values(allowed_source_statuses)
        if allowed_source_statuses is not None
        else list(_WORKFLOW_RUN_STATUS_SOURCES.get(status.value, ()))
    )
    statement = (
        update(WorkflowRunRecord)
        .where(WorkflowRunRecord.workflow_run_id == workflow_run_id)
        .where(WorkflowRunRecord.status.notin_(_TERMINAL_WORKFLOW_STATUSES))
        .values(
            status=status.value,
            state_version=WorkflowRunRecord.state_version + 1,
            finished_at=_optional_datetime_to_text(finished_at),
            completion_reason=_optional_completion_reason_value(completion_reason),
            error_json=_json_dumps(error) if error is not None else None,
        )
    )
    if expected_state_version is not None:
        statement = statement.where(
            WorkflowRunRecord.state_version == expected_state_version
        )
    statement = statement.where(WorkflowRunRecord.status.in_(source_statuses))
    if owner_process_id is not None:
        statement = statement.where(
            WorkflowRunRecord.owner_process_id == owner_process_id
        )
    if process_generation is not None:
        statement = statement.where(
            WorkflowRunRecord.process_generation == process_generation
        )
    result = cast(CursorResult[Any], session.execute(statement))
    if result.rowcount != 1:
        return None
    record = session.get(WorkflowRunRecord, workflow_run_id)
    if record is None:
        return None
    return _workflow_run_from_record(record)
