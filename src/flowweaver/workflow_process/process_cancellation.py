from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.loop_terminal_state import (
    cancel_active_loop_runs_for_workflow,
)
from flowweaver.workflow_process.process_finalization import (
    release_unreleased_read_leases_for_terminal_workflow,
)
from flowweaver.workflow_process.task_supervision import (
    request_cancel_for_in_flight_tasks,
)


def cancel_workflow_process_if_requested(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None,
    execution_pool: NodeTaskExecutionPool,
    event_sink: RuntimeEventSink,
) -> bool:
    if not request_workflow_cancel_if_requested(
        store=store,
        process_id=process_id,
        execution_pool=execution_pool,
    ):
        return False
    return finalize_workflow_cancel_if_idle(
        store=store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        execution_pool=execution_pool,
        event_sink=event_sink,
    )


def request_workflow_cancel_if_requested(
    *,
    store: RuntimeStore,
    process_id: str,
    execution_pool: NodeTaskExecutionPool,
) -> bool:
    process = store.get_workflow_process(process_id)
    if process is None or process.cancel_requested_at is None:
        return False
    request_cancel_for_in_flight_tasks(
        store=store,
        execution_pool=execution_pool,
    )
    return True


def finalize_workflow_cancel_if_idle(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None,
    execution_pool: NodeTaskExecutionPool,
    event_sink: RuntimeEventSink,
) -> bool:
    process = store.get_workflow_process(process_id)
    if (
        process is None
        or process.cancel_requested_at is None
        or execution_pool.in_flight_count() > 0
    ):
        return False
    cancel_active_loop_runs_for_workflow(
        store,
        workflow_run_id=workflow_run_id,
        error={
            "message": "Workflow run cancelled",
            "reason": "WORKFLOW_CANCEL_REQUESTED",
        },
    )
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.CANCELLED,
        finished_at=utc_now(),
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_CANCELLED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id},
        )
    )
    release_unreleased_read_leases_for_terminal_workflow(
        store,
        workflow_run_id,
    )
    return True
