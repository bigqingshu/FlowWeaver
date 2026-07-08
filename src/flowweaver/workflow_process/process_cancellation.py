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
    process = store.get_workflow_process(process_id)
    if process is None or process.cancel_requested_at is None:
        return False
    request_cancel_for_in_flight_tasks(
        store=store,
        execution_pool=execution_pool,
    )
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
