from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowRun
from flowweaver.protocols.enums import EventType, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.workflow_process.workflow_completion import (
    WorkflowCompletionEvaluator,
)


def complete_workflow_if_all_nodes_succeeded(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    event_sink: RuntimeEventSink,
) -> WorkflowRun | None:
    if not WorkflowCompletionEvaluator(store).can_mark_workflow_succeeded(
        workflow_run_id
    ):
        return None
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.status == WorkflowRunStatus.SUCCEEDED.value:
        return run
    completed = store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    if completed is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FINISHED,
                workflow_run_id=workflow_run_id,
                payload={"process_id": process_id},
            )
        )
    return completed
