from __future__ import annotations

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, WorkflowRunStatus
from flowweaver.protocols.events import EventModel


def mark_workflow_process_started(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None,
    run: WorkflowRun,
    event_sink: RuntimeEventSink,
) -> None:
    store.record_workflow_process_heartbeat(
        process_id,
        process_generation=process_generation,
    )
    current_run = store.get_workflow_run(workflow_run_id)
    if (
        current_run is not None
        and current_run.status == WorkflowRunStatus.PENDING.value
    ):
        store.update_workflow_run_status(
            workflow_run_id,
            WorkflowRunStatus.RUNNING,
            expected_state_version=current_run.state_version,
            allowed_source_statuses=[WorkflowRunStatus.PENDING],
            owner_process_id=process_id if process_generation is not None else None,
            process_generation=process_generation,
        )
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_run_id=workflow_run_id,
            payload={
                "process_id": process_id,
                "run_mode": run.run_mode,
                "trigger_source": run.trigger_source,
                "target_node_instance_id": run.target_node_instance_id,
            },
        )
    )
