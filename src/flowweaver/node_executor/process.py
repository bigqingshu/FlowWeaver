from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import TextIO

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.builtin_fault import (
    BUILTIN_FAULT_NODE_TYPES,
    BuiltinFaultNodeExecutor,
)
from flowweaver.node_executor.cancel_token import NodeExecutionContext
from flowweaver.node_executor.fake import FakeNodeExecutor
from flowweaver.node_executor.process_envelopes import (
    heartbeat_envelope as _heartbeat_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    ready_envelope as _ready_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_accepted_envelope as _task_accepted_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_completed_envelope as _task_completed_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_failed_envelope as _task_failed_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_heartbeat_envelope as _task_heartbeat_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_progress_envelope as _task_progress_envelope,
)
from flowweaver.node_executor.process_helpers import (
    failed_task_result as _failed_task_result,
)
from flowweaver.node_executor.process_helpers import (
    write_envelope as _write_envelope,
)
from flowweaver.node_executor.process_loop import (
    EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE as EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE,
)
from flowweaver.node_executor.process_loop import (
    run_node_executor_ipc_loop,
)
from flowweaver.node_executor.process_state import NodeExecutorProcessState
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskCancelRequestPayload,
    NodeTaskSubmitPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel


class NodeExecutorProcess:
    def __init__(
        self,
        *,
        executor_id: str,
        executor_factory: NodeExecutorFactory | None = None,
        event_writer: Callable[[IPCEnvelope], None] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._executor_factory = executor_factory
        self._event_writer = event_writer
        self._state = NodeExecutorProcessState()
        self._pending_task_events: list[IPCEnvelope] = []

    def ready_envelope(self) -> IPCEnvelope:
        return _ready_envelope(self.executor_id)

    def heartbeat_envelope(self) -> IPCEnvelope:
        return _heartbeat_envelope(
            self.executor_id,
            active_task_ids=self._state.active_task_ids(),
        )

    def task_heartbeat_envelope(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> IPCEnvelope:
        return _task_heartbeat_envelope(
            self.executor_id,
            task,
            correlation_id=correlation_id
            or self._state.task_correlation_id(task.task_id),
        )

    def task_progress_envelope(
        self,
        task: NodeTaskModel,
        *,
        progress: float | None,
        current_stage: str | None = None,
        metrics: dict[str, int | float | str] | None = None,
        correlation_id: str | None = None,
    ) -> IPCEnvelope:
        return _task_progress_envelope(
            task,
            progress=progress,
            current_stage=current_stage,
            metrics=metrics or {},
            correlation_id=correlation_id
            or self._state.task_correlation_id(task.task_id),
        )

    def emit_task_heartbeat(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> None:
        self._emit_or_queue_task_event(
            self.task_heartbeat_envelope(task, correlation_id=correlation_id)
        )

    def emit_task_progress(
        self,
        task: NodeTaskModel,
        *,
        progress: float | None,
        current_stage: str | None = None,
        metrics: dict[str, int | float | str] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._emit_or_queue_task_event(
            self.task_progress_envelope(
                task,
                progress=progress,
                current_stage=current_stage,
                metrics=metrics,
                correlation_id=correlation_id,
            )
        )

    def handle_envelope(self, envelope: IPCEnvelope) -> tuple[IPCEnvelope, ...]:
        if envelope.message_type == IPCMessageType.NODE_TASK_CANCEL_REQUEST:
            return self._handle_cancel_request(envelope)
        if envelope.message_type != IPCMessageType.NODE_TASK_SUBMIT:
            return ()
        task = NodeTaskSubmitPayload.model_validate(envelope.payload)
        executor = self._executor_for_task(task)
        self._state.begin_task(
            task_id=task.task_id,
            correlation_id=envelope.message_id,
        )
        self._pending_task_events = []
        accepted = _task_accepted_envelope(
            self.executor_id,
            task,
            correlation_id=envelope.message_id,
        )
        accepted_events = self._emit_or_return(accepted)
        try:
            result = executor.execute(task)
            task_events = tuple(self._pending_task_events)
        except Exception as exc:
            task_events = tuple(self._pending_task_events)
            failed = _task_failed_envelope(
                task,
                result=_failed_task_result(
                    task,
                    executor_id=self.executor_id,
                    error=exc,
                ),
                error_type=type(exc).__name__,
                correlation_id=envelope.message_id,
            )
            return (*accepted_events, *task_events, failed)
        finally:
            self._state.finish_task(task.task_id)
            self._pending_task_events = []
        completed = _task_completed_envelope(
            task,
            result=result,
            correlation_id=envelope.message_id,
        )
        return (*accepted_events, *task_events, completed)

    def task_is_cancelled(self, task: NodeTaskModel) -> bool:
        context = self.task_context(task)
        return context is not None and context.is_cancelled()

    def task_context(self, task: NodeTaskModel) -> NodeExecutionContext | None:
        return self._state.task_context(task.task_id)

    def _handle_cancel_request(
        self,
        envelope: IPCEnvelope,
    ) -> tuple[IPCEnvelope, ...]:
        payload = NodeTaskCancelRequestPayload.model_validate(envelope.payload)
        self._state.request_cancel(task_id=payload.task_id, reason=payload.reason)
        return ()

    def _emit_or_queue_task_event(self, envelope: IPCEnvelope) -> None:
        if self._event_writer is not None:
            self._event_writer(envelope)
            return
        self._pending_task_events.append(envelope)

    def _emit_or_return(self, envelope: IPCEnvelope) -> tuple[IPCEnvelope, ...]:
        if self._event_writer is not None:
            self._event_writer(envelope)
            return ()
        return (envelope,)

    def _executor_for_task(self, task: NodeTaskModel):
        if self._executor_factory is not None:
            return self._executor_factory(task)
        if task.node_type in BUILTIN_FAULT_NODE_TYPES:
            return BuiltinFaultNodeExecutor(
                executor_id=self.executor_id,
                event_emitter=self,
            )
        return FakeNodeExecutor(executor_id=self.executor_id)


def run_node_executor_process(
    *,
    executor_id: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    executor_factory: NodeExecutorFactory | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    process = NodeExecutorProcess(
        executor_id=executor_id,
        executor_factory=executor_factory,
        event_writer=lambda envelope: _write_envelope(stdout, envelope),
    )
    return run_node_executor_ipc_loop(
        process,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor-id", required=True)
    args = parser.parse_args(argv)
    return run_node_executor_process(executor_id=args.executor_id)


def _exit() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
