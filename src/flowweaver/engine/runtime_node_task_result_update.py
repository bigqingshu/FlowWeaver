from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import NodeRunRecord, WorkflowRunRecord
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_run_from_record,
    _node_task_result_to_record,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_status_guards import (
    NODE_RUN_STATUS_SOURCES as _NODE_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_NODE_STATUSES as _TERMINAL_NODE_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    node_run_status_values as _node_run_status_values,
)
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskResultModel


class NodeTaskResultUpdateRejected(Exception):
    pass


def record_node_task_result_and_update_node_run_status_in_session(
    session: Session,
    result: NodeTaskResultModel,
    status: NodeRunStatus,
    *,
    progress: float | None,
    current_stage: str | None,
    finished_at: datetime | None,
    error: dict[str, Any] | None,
    executor_id: str | None,
    expected_state_version: int | None,
    allowed_source_statuses: Iterable[NodeRunStatus | str] | None,
    owner_process_id: str | None,
    process_generation: int | None,
) -> NodeRun:
    session.add(_node_task_result_to_record(result))
    session.flush()
    source_statuses = (
        _node_run_status_values(allowed_source_statuses)
        if allowed_source_statuses is not None
        else list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))
    )
    values: dict[str, Any] = {
        "status": status.value,
        "state_version": NodeRunRecord.state_version + 1,
        "error_json": _json_dumps(error) if error is not None else None,
    }
    if progress is not None:
        values["progress"] = progress
    if current_stage is not None:
        values["current_stage"] = current_stage
    if finished_at is not None:
        values["finished_at"] = _datetime_to_text(finished_at)
    if executor_id is not None:
        values["executor_id"] = executor_id

    statement = (
        update(NodeRunRecord)
        .where(NodeRunRecord.node_run_id == result.node_run_id)
        .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
        .values(**values)
    )
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
    update_result = cast(CursorResult[Any], session.execute(statement))
    if update_result.rowcount != 1:
        raise NodeTaskResultUpdateRejected
    record = session.get(NodeRunRecord, result.node_run_id)
    if record is None:
        raise NodeTaskResultUpdateRejected
    return _node_run_from_record(record)
