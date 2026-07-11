from __future__ import annotations

from datetime import datetime, timedelta

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow.runtime_feedback_policy import RuntimeFeedbackPolicyLike


def record_task_heartbeat(
    *,
    store: RuntimeStore,
    task: NodeTaskModel,
    executor_id: str,
    attempt: int,
) -> NodeRun | None:
    if attempt != task.attempt:
        return None
    return store.update_node_task_runtime_state(
        task,
        executor_id=executor_id,
    )


def record_task_progress(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    task: NodeTaskModel,
    executor_id: str,
    progress: float | None,
    current_stage: str | None,
    metrics: dict[str, int | float | str] | None = None,
    runtime_feedback_policy: RuntimeFeedbackPolicyLike | None = None,
    last_progress_emitted_at: dict[str, datetime],
) -> NodeRun | None:
    if (
        runtime_feedback_policy is not None
        and not runtime_feedback_policy.telemetry.progress_enabled
    ):
        return store.update_node_task_runtime_state(
            task,
            executor_id=executor_id,
        )
    now = utc_now()
    if (
        runtime_feedback_policy is not None
        and runtime_feedback_policy.telemetry.progress_interval_seconds > 0
    ):
        previous_progress_at = last_progress_emitted_at.get(task.task_id)
        if (
            previous_progress_at is not None
            and now - previous_progress_at
            < timedelta(
                seconds=(
                    runtime_feedback_policy.telemetry.progress_interval_seconds
                )
            )
        ):
            return store.update_node_task_runtime_state(
                task,
                executor_id=executor_id,
                heartbeat_at=now,
            )
    updated = store.update_node_task_runtime_state(
        task,
        executor_id=executor_id,
        heartbeat_at=now,
        progress=progress,
        current_stage=current_stage,
    )
    if updated is None:
        return None
    last_progress_emitted_at[task.task_id] = now
    event_sink.emit(
        EventModel(
            event_type=EventType.NODE_PROGRESS,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            payload={
                "process_id": task.workflow_process_id,
                "task_id": task.task_id,
                "executor_id": executor_id,
                "node_instance_id": task.node_instance_id,
                "progress": progress,
                "current_stage": current_stage,
                "metrics": metrics or {},
            },
        )
    )
    return updated
