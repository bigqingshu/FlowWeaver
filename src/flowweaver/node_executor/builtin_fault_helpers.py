from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class TaskEventEmitter(Protocol):
    def emit_task_heartbeat(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> None:
        ...

    def emit_task_progress(
        self,
        task: NodeTaskModel,
        *,
        progress: float | None,
        current_stage: str | None = None,
        metrics: dict[str, int | float | str] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        ...

    def task_is_cancelled(self, task: NodeTaskModel) -> bool:
        ...


def float_config(
    config: dict[str, Any],
    key: str,
    *,
    default: float,
) -> float:
    value = config.get(key, default)
    if not isinstance(value, int | float):
        raise ValueError(f"config.{key} must be a number")
    if value < 0:
        raise ValueError(f"config.{key} must be non-negative")
    return float(value)


def int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"config.{key} must be an integer")
    return value


def emit_delay_progress(
    event_emitter: TaskEventEmitter,
    task: NodeTaskModel,
    *,
    elapsed_seconds: float,
    duration_seconds: float,
) -> None:
    progress = 1.0 if duration_seconds == 0 else elapsed_seconds / duration_seconds
    event_emitter.emit_task_progress(
        task,
        progress=max(0.0, min(1.0, progress)),
        current_stage="running",
        metrics={"elapsed_seconds": round(elapsed_seconds, 6)},
    )


def cancelled_task_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
    started_at: datetime,
) -> NodeTaskResultModel:
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.CANCELLED,
        error={
            "message": "Node task cancelled",
            "reason": "NODE_TASK_CANCEL_REQUEST",
        },
        started_at=started_at,
        finished_at=utc_now(),
    )
