from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Protocol

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel

DELAY_TEST_NODE_TYPE = "DelayTestNode"
FAULT_TEST_NODE_TYPE = "FaultTestNode"
FAULT_MODE_INFINITE_LOOP = "INFINITE_LOOP"
FAULT_MODE_RAISE_EXCEPTION = "RAISE_EXCEPTION"
FAULT_MODE_PROCESS_EXIT = "PROCESS_EXIT"
BUILTIN_FAULT_NODE_TYPES = frozenset(
    {
        DELAY_TEST_NODE_TYPE,
        FAULT_TEST_NODE_TYPE,
    }
)


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


class BuiltinFaultNodeExecutor:
    def __init__(
        self,
        *,
        executor_id: str,
        event_emitter: TaskEventEmitter,
    ) -> None:
        self.executor_id = executor_id
        self._event_emitter = event_emitter

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if task.node_type == DELAY_TEST_NODE_TYPE:
            return self._execute_delay(task)
        if task.node_type == FAULT_TEST_NODE_TYPE:
            return self._execute_fault(task)
        raise ValueError(f"Unsupported builtin fault node type: {task.node_type}")

    def _execute_delay(self, task: NodeTaskModel) -> NodeTaskResultModel:
        started_at = utc_now()
        duration_seconds = _float_config(
            task.config,
            "duration_seconds",
            default=0.0,
        )
        heartbeat_interval = max(
            _float_config(task.config, "heartbeat_interval_seconds", default=0.2),
            0.001,
        )
        progress_interval = max(
            _float_config(task.config, "progress_interval_seconds", default=0.2),
            0.001,
        )
        started_monotonic = time.monotonic()
        deadline = started_monotonic + duration_seconds
        next_heartbeat_at = started_monotonic
        next_progress_at = started_monotonic

        while True:
            now_monotonic = time.monotonic()
            elapsed = max(0.0, now_monotonic - started_monotonic)
            if now_monotonic >= next_heartbeat_at:
                self._event_emitter.emit_task_heartbeat(task)
                next_heartbeat_at = now_monotonic + heartbeat_interval
            if now_monotonic >= next_progress_at:
                self._emit_delay_progress(task, elapsed, duration_seconds)
                next_progress_at = now_monotonic + progress_interval
            if self._event_emitter.task_is_cancelled(task):
                return self._cancelled_result(task, started_at=started_at)
            if now_monotonic >= deadline:
                break
            sleep_seconds = min(
                0.01,
                max(0.0, deadline - now_monotonic),
                max(0.001, next_heartbeat_at - now_monotonic),
                max(0.001, next_progress_at - now_monotonic),
            )
            time.sleep(sleep_seconds)

        self._event_emitter.emit_task_heartbeat(task)
        self._event_emitter.emit_task_progress(
            task,
            progress=1.0,
            current_stage="completed",
            metrics={"elapsed_seconds": duration_seconds},
        )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_fault(self, task: NodeTaskModel) -> NodeTaskResultModel:
        mode = str(task.config.get("mode", FAULT_MODE_RAISE_EXCEPTION)).upper()
        if mode == FAULT_MODE_RAISE_EXCEPTION:
            message = str(task.config.get("message", "FaultTestNode injected failure"))
            raise RuntimeError(message)
        if mode == FAULT_MODE_INFINITE_LOOP:
            return self._execute_infinite_loop(task)
        if mode == FAULT_MODE_PROCESS_EXIT:
            exit_code = _int_config(task.config, "exit_code", default=7)
            raise SystemExit(exit_code)
        raise ValueError(f"Unsupported FaultTestNode mode: {mode}")

    def _execute_infinite_loop(self, task: NodeTaskModel) -> NodeTaskResultModel:
        started_at = utc_now()
        heartbeat_interval = max(
            _float_config(task.config, "heartbeat_interval_seconds", default=0.2),
            0.001,
        )
        progress_interval = max(
            _float_config(task.config, "progress_interval_seconds", default=0.2),
            0.001,
        )
        started_monotonic = time.monotonic()
        next_heartbeat_at = started_monotonic
        next_progress_at = started_monotonic
        while True:
            now_monotonic = time.monotonic()
            elapsed = max(0.0, now_monotonic - started_monotonic)
            if now_monotonic >= next_heartbeat_at:
                self._event_emitter.emit_task_heartbeat(task)
                next_heartbeat_at = now_monotonic + heartbeat_interval
            if now_monotonic >= next_progress_at:
                self._event_emitter.emit_task_progress(
                    task,
                    progress=None,
                    current_stage="infinite_loop",
                    metrics={"elapsed_seconds": round(elapsed, 6)},
                )
                next_progress_at = now_monotonic + progress_interval
            if self._event_emitter.task_is_cancelled(task):
                return self._cancelled_result(task, started_at=started_at)
            time.sleep(0.01)

    def _emit_delay_progress(
        self,
        task: NodeTaskModel,
        elapsed_seconds: float,
        duration_seconds: float,
    ) -> None:
        progress = 1.0 if duration_seconds == 0 else elapsed_seconds / duration_seconds
        self._event_emitter.emit_task_progress(
            task,
            progress=max(0.0, min(1.0, progress)),
            current_stage="running",
            metrics={"elapsed_seconds": round(elapsed_seconds, 6)},
        )

    def _cancelled_result(
        self,
        task: NodeTaskModel,
        *,
        started_at: datetime,
    ) -> NodeTaskResultModel:
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.CANCELLED,
            error={
                "message": "Node task cancelled",
                "reason": "NODE_TASK_CANCEL_REQUEST",
            },
            started_at=started_at,
            finished_at=utc_now(),
        )


def _float_config(
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


def _int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"config.{key} must be an integer")
    return value
