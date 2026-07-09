from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import select

from flowweaver.engine.db_models import NodeRunRecord, WorkflowRunRecord
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_status_guards import (
    NODE_RUN_STATUS_SOURCES as _NODE_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    node_run_status_values as _node_run_status_values,
)
from flowweaver.protocols.enums import NodeRunStatus


def node_run_status_source_values(
    status: NodeRunStatus,
    allowed_source_statuses: Iterable[NodeRunStatus | str] | None,
) -> list[str]:
    if allowed_source_statuses is not None:
        return _node_run_status_values(allowed_source_statuses)
    return list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))


def node_run_status_update_values(
    status: NodeRunStatus,
    *,
    progress: float | None = None,
    current_stage: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error: dict[str, Any] | None = None,
    executor_id: str | None = None,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "status": status.value,
        "state_version": NodeRunRecord.state_version + 1,
        "error_json": _json_dumps(error) if error is not None else None,
    }
    if progress is not None:
        values["progress"] = progress
    if current_stage is not None:
        values["current_stage"] = current_stage
    if started_at is not None:
        values["started_at"] = _datetime_to_text(started_at)
    if finished_at is not None:
        values["finished_at"] = _datetime_to_text(finished_at)
    if executor_id is not None:
        values["executor_id"] = executor_id
    return values


def apply_node_run_status_update_guards(
    statement: Any,
    *,
    expected_state_version: int | None,
    source_statuses: Iterable[str],
    owner_process_id: str | None,
    process_generation: int | None,
) -> Any:
    if expected_state_version is not None:
        statement = statement.where(
            NodeRunRecord.state_version == expected_state_version
        )
    statement = statement.where(NodeRunRecord.status.in_(source_statuses))
    if owner_process_id is not None or process_generation is not None:
        owner_check = select(WorkflowRunRecord.workflow_run_id).where(
            WorkflowRunRecord.workflow_run_id == NodeRunRecord.workflow_run_id
        )
        if owner_process_id is not None:
            owner_check = owner_check.where(
                WorkflowRunRecord.owner_process_id == owner_process_id
            )
        if process_generation is not None:
            owner_check = owner_check.where(
                WorkflowRunRecord.process_generation == process_generation
            )
        statement = statement.where(owner_check.exists())
    return statement
