from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowRunRecord
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeRunStatus,
    WorkflowProcessStatus,
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)

TERMINAL_WORKFLOW_STATUS_VALUES = frozenset(
    {
        WorkflowRunStatus.SUCCEEDED.value,
        WorkflowRunStatus.FAILED.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.ABORTED.value,
    }
)
TERMINAL_WORKFLOW_STATUSES = frozenset(TERMINAL_WORKFLOW_STATUS_VALUES)
TERMINAL_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.TIMED_OUT.value,
        NodeRunStatus.SUCCEEDED.value,
        NodeRunStatus.FAILED.value,
        NodeRunStatus.CANCELLED.value,
        NodeRunStatus.SKIPPED.value,
    }
)
TERMINAL_LOOP_RUN_STATUSES = frozenset(
    {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.FAILED.value,
        LoopRunStatus.CANCELLED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }
)
TERMINAL_LOOP_ITERATION_STATUSES = frozenset(
    {
        LoopIterationRunStatus.SUCCEEDED.value,
        LoopIterationRunStatus.FAILED.value,
        LoopIterationRunStatus.CANCELLED.value,
        LoopIterationRunStatus.SKIPPED.value,
    }
)
WORKFLOW_RUN_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    WorkflowRunStatus.RUNNING.value: (WorkflowRunStatus.PENDING.value,),
    WorkflowRunStatus.SUCCEEDED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.FAILED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.CANCELLED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.ABORTED.value: (WorkflowRunStatus.RUNNING.value,),
}
NODE_RUN_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    NodeRunStatus.READY.value: (NodeRunStatus.WAITING_DEPENDENCY.value,),
    NodeRunStatus.QUEUED.value: (NodeRunStatus.READY.value,),
    NodeRunStatus.RUNNING.value: (NodeRunStatus.QUEUED.value,),
    NodeRunStatus.LONG_RUNNING.value: (NodeRunStatus.RUNNING.value,),
    NodeRunStatus.SUCCEEDED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.FAILED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.CANCELLED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    ),
    NodeRunStatus.CANCEL_REQUESTED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.TIMED_OUT.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    ),
    NodeRunStatus.SKIPPED.value: (
        NodeRunStatus.PENDING.value,
        NodeRunStatus.READY.value,
        NodeRunStatus.WAITING_DEPENDENCY.value,
    ),
}
LOOP_RUN_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    LoopRunStatus.RUNNING.value: (LoopRunStatus.PENDING.value,),
    LoopRunStatus.ENDED.value: (LoopRunStatus.RUNNING.value,),
    LoopRunStatus.FAILED.value: (LoopRunStatus.RUNNING.value,),
    LoopRunStatus.CANCELLED.value: (
        LoopRunStatus.PENDING.value,
        LoopRunStatus.RUNNING.value,
    ),
    LoopRunStatus.MAX_ITERATIONS_REACHED.value: (LoopRunStatus.RUNNING.value,),
}
LOOP_ITERATION_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    LoopIterationRunStatus.RUNNING.value: (LoopIterationRunStatus.PENDING.value,),
    LoopIterationRunStatus.SUCCEEDED.value: (LoopIterationRunStatus.RUNNING.value,),
    LoopIterationRunStatus.FAILED.value: (LoopIterationRunStatus.RUNNING.value,),
    LoopIterationRunStatus.CANCELLED.value: (LoopIterationRunStatus.RUNNING.value,),
    LoopIterationRunStatus.SKIPPED.value: (LoopIterationRunStatus.PENDING.value,),
}
ACTIVE_WORKFLOW_PROCESS_STATUSES = frozenset(
    {
        WorkflowProcessStatus.STARTING.value,
        WorkflowProcessStatus.RUNNING.value,
        WorkflowProcessStatus.CANCEL_REQUESTED.value,
    }
)
INTERRUPTED_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.QUEUED.value,
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }
)


def workflow_run_matches_owner(
    session: Session,
    *,
    workflow_run_id: str,
    owner_process_id: str | None,
    process_generation: int | None,
) -> bool:
    statement = select(WorkflowRunRecord.workflow_run_id).where(
        WorkflowRunRecord.workflow_run_id == workflow_run_id
    )
    if owner_process_id is not None:
        statement = statement.where(
            WorkflowRunRecord.owner_process_id == owner_process_id
        )
    if process_generation is not None:
        statement = statement.where(
            WorkflowRunRecord.process_generation == process_generation
        )
    return session.scalar(statement) is not None


def workflow_run_status_values(
    statuses: Iterable[WorkflowRunStatus | str],
) -> list[str]:
    return [
        status.value if isinstance(status, WorkflowRunStatus) else status
        for status in statuses
    ]


def node_run_status_values(statuses: Iterable[NodeRunStatus | str]) -> list[str]:
    return [
        status.value if isinstance(status, NodeRunStatus) else status
        for status in statuses
    ]


def loop_run_status_values(statuses: Iterable[LoopRunStatus | str]) -> list[str]:
    return [
        status.value if isinstance(status, LoopRunStatus) else status
        for status in statuses
    ]


def loop_iteration_status_values(
    statuses: Iterable[LoopIterationRunStatus | str],
) -> list[str]:
    return [
        status.value if isinstance(status, LoopIterationRunStatus) else status
        for status in statuses
    ]


def optional_completion_reason_value(
    value: WorkflowRunCompletionReason | str | None,
) -> str | None:
    if isinstance(value, WorkflowRunCompletionReason):
        return value.value
    return value
