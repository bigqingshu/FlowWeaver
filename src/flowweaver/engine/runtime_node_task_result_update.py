from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import NodeRunRecord
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_run_status_update import (
    apply_node_run_status_update_guards as _apply_node_run_status_update_guards,
)
from flowweaver.engine.runtime_node_run_status_update import (
    node_run_status_source_values as _node_run_status_source_values,
)
from flowweaver.engine.runtime_node_run_status_update import (
    node_run_status_update_values as _node_run_status_update_values,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _add_node_task_result_to_session,
    _node_run_from_record,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_NODE_STATUSES as _TERMINAL_NODE_STATUSES,
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
    _add_node_task_result_to_session(session, result)
    session.flush()
    source_statuses = _node_run_status_source_values(
        status,
        allowed_source_statuses,
    )
    statement = (
        update(NodeRunRecord)
        .where(NodeRunRecord.node_run_id == result.node_run_id)
        .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
        .values(
            **_node_run_status_update_values(
                status,
                progress=progress,
                current_stage=current_stage,
                finished_at=finished_at,
                error=error,
                executor_id=executor_id,
            )
        )
    )
    statement = _apply_node_run_status_update_guards(
        statement,
        expected_state_version=expected_state_version,
        source_statuses=source_statuses,
        owner_process_id=owner_process_id,
        process_generation=process_generation,
    )
    update_result = cast(CursorResult[Any], session.execute(statement))
    if update_result.rowcount != 1:
        raise NodeTaskResultUpdateRejected
    record = session.get(NodeRunRecord, result.node_run_id)
    if record is None:
        raise NodeTaskResultUpdateRejected
    return _node_run_from_record(record)
