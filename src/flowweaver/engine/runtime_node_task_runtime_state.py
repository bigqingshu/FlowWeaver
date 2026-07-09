from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    NodeRunRecord,
    NodeTaskRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import _node_run_from_record
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel


def update_node_task_runtime_state_in_session(
    session: Session,
    task: NodeTaskModel,
    *,
    executor_id: str,
    heartbeat_at: datetime | None,
    progress: float | None,
    current_stage: str | None,
) -> NodeRun | None:
    values: dict[str, Any] = {
        "last_heartbeat": _datetime_to_text(heartbeat_at or utc_now()),
    }
    if progress is not None:
        values["progress"] = progress
    if current_stage is not None:
        values["current_stage"] = current_stage
    task_check = (
        select(NodeTaskRecord.task_id)
        .where(NodeTaskRecord.task_id == task.task_id)
        .where(NodeTaskRecord.node_run_id == task.node_run_id)
        .where(NodeTaskRecord.attempt == task.attempt)
        .where(NodeTaskRecord.workflow_process_id == task.workflow_process_id)
        .where(NodeTaskRecord.process_generation == task.process_generation)
    )
    owner_check = (
        select(WorkflowRunRecord.workflow_run_id)
        .where(WorkflowRunRecord.workflow_run_id == NodeRunRecord.workflow_run_id)
        .where(WorkflowRunRecord.owner_process_id == task.workflow_process_id)
        .where(WorkflowRunRecord.process_generation == task.process_generation)
    )
    statement = (
        update(NodeRunRecord)
        .where(NodeRunRecord.node_run_id == task.node_run_id)
        .where(
            NodeRunRecord.status.in_(
                [
                    NodeRunStatus.RUNNING.value,
                    NodeRunStatus.LONG_RUNNING.value,
                    NodeRunStatus.CANCEL_REQUESTED.value,
                ]
            )
        )
        .where(NodeRunRecord.executor_id == executor_id)
        .where(NodeRunRecord.attempt == task.attempt)
        .where(task_check.exists())
        .where(owner_check.exists())
        .values(**values)
    )
    result = cast(CursorResult[Any], session.execute(statement))
    if result.rowcount != 1:
        return None
    record = session.get(NodeRunRecord, task.node_run_id)
    if record is None:
        return None
    return _node_run_from_record(record)
