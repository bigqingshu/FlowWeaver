from __future__ import annotations

import time

from flowweaver.common.time import utc_now
from flowweaver.node_executor.builtin_fault_helpers import (
    TaskEventEmitter as TaskEventEmitter,
)
from flowweaver.node_executor.builtin_fault_helpers import (
    cancelled_task_result as _cancelled_task_result,
)
from flowweaver.node_executor.builtin_fault_helpers import (
    emit_delay_progress as _emit_delay_progress,
)
from flowweaver.node_executor.builtin_fault_helpers import (
    float_config as _float_config,
)
from flowweaver.node_executor.builtin_fault_helpers import int_config as _int_config
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
                _emit_delay_progress(
                    self._event_emitter,
                    task,
                    elapsed_seconds=elapsed,
                    duration_seconds=duration_seconds,
                )
                next_progress_at = now_monotonic + progress_interval
            if self._event_emitter.task_is_cancelled(task):
                return _cancelled_task_result(
                    task,
                    executor_id=self.executor_id,
                    started_at=started_at,
                )
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
                return _cancelled_task_result(
                    task,
                    executor_id=self.executor_id,
                    started_at=started_at,
                )
            time.sleep(0.01)
