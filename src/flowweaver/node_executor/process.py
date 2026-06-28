from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from threading import Lock, Thread
from typing import TextIO

from flowweaver.common.time import utc_now
from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.builtin_fault import (
    BUILTIN_FAULT_NODE_TYPES,
    BuiltinFaultNodeExecutor,
)
from flowweaver.node_executor.cancel_token import CancelToken
from flowweaver.node_executor.fake import FakeNodeExecutor
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import (
    ExecutorHeartbeatPayload,
    IPCEnvelope,
    NodeTaskCancelRequestPayload,
    NodeTaskCompletedPayload,
    NodeTaskFailedPayload,
    NodeTaskHeartbeatPayload,
    NodeTaskProgressPayload,
    NodeTaskSubmitPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel

EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE = 2


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
        self._active_task_ids: set[str] = set()
        self._active_task_correlations: dict[str, str] = {}
        self._cancel_tokens: dict[str, CancelToken] = {}
        self._pending_task_events: list[IPCEnvelope] = []
        self._state_lock = Lock()

    def ready_envelope(self) -> IPCEnvelope:
        return IPCEnvelope(
            message_type=IPCMessageType.EXECUTOR_READY,
            payload={"executor_id": self.executor_id},
        )

    def heartbeat_envelope(self) -> IPCEnvelope:
        with self._state_lock:
            active_task_ids = sorted(self._active_task_ids)
        return IPCEnvelope(
            message_type=IPCMessageType.EXECUTOR_HEARTBEAT,
            payload=ExecutorHeartbeatPayload(
                executor_id=self.executor_id,
                active_task_ids=active_task_ids,
            ).model_dump(mode="json"),
        )

    def task_heartbeat_envelope(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> IPCEnvelope:
        return IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            correlation_id=correlation_id or self._active_task_correlations.get(
                task.task_id
            ),
            payload=NodeTaskHeartbeatPayload(
                executor_id=self.executor_id,
                task_id=task.task_id,
                attempt=task.attempt,
            ).model_dump(mode="json"),
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
        return IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_PROGRESS,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            correlation_id=correlation_id or self._active_task_correlations.get(
                task.task_id
            ),
            payload=NodeTaskProgressPayload(
                progress=progress,
                current_stage=current_stage,
                metrics=metrics or {},
            ).model_dump(mode="json"),
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
        with self._state_lock:
            self._active_task_ids.add(task.task_id)
            self._active_task_correlations[task.task_id] = envelope.message_id
            self._cancel_tokens[task.task_id] = CancelToken()
        self._pending_task_events = []
        accepted = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_ACCEPTED,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            correlation_id=envelope.message_id,
            payload={
                "executor_id": self.executor_id,
                "task_id": task.task_id,
                "node_run_id": task.node_run_id,
            },
        )
        accepted_events = self._emit_or_return(accepted)
        try:
            result = executor.execute(task)
            task_events = tuple(self._pending_task_events)
        except Exception as exc:
            task_events = tuple(self._pending_task_events)
            failed = IPCEnvelope(
                message_type=IPCMessageType.NODE_TASK_FAILED,
                workflow_run_id=task.workflow_run_id,
                node_run_id=task.node_run_id,
                correlation_id=envelope.message_id,
                payload=NodeTaskFailedPayload(
                    result=_failed_task_result(
                        task,
                        executor_id=self.executor_id,
                        error=exc,
                    ),
                    error_type=type(exc).__name__,
                ).model_dump(mode="json"),
            )
            return (*accepted_events, *task_events, failed)
        finally:
            with self._state_lock:
                self._active_task_ids.discard(task.task_id)
                self._active_task_correlations.pop(task.task_id, None)
                self._cancel_tokens.pop(task.task_id, None)
            self._pending_task_events = []
        completed = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_COMPLETED,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            correlation_id=envelope.message_id,
            payload=NodeTaskCompletedPayload(result=result).model_dump(mode="json"),
        )
        return (*accepted_events, *task_events, completed)

    def task_is_cancelled(self, task: NodeTaskModel) -> bool:
        with self._state_lock:
            token = self._cancel_tokens.get(task.task_id)
        return token is not None and token.is_cancelled()

    def _handle_cancel_request(
        self,
        envelope: IPCEnvelope,
    ) -> tuple[IPCEnvelope, ...]:
        payload = NodeTaskCancelRequestPayload.model_validate(envelope.payload)
        with self._state_lock:
            token = self._cancel_tokens.get(payload.task_id)
        if token is not None:
            token.request_cancel(reason=payload.reason)
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
    _write_envelope(stdout, process.ready_envelope())
    task_workers: list[Thread] = []

    def handle_task(envelope: IPCEnvelope) -> None:
        try:
            responses = process.handle_envelope(envelope)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            os._exit(code)
        for response in responses:
            _write_envelope(stdout, response)

    for line in stdin:
        if not line.strip():
            continue
        try:
            envelope = IPCEnvelope.model_validate_json(line)
        except ValueError as exc:
            _write_process_error(stderr, "IPC_INPUT_ERROR", exc)
            return EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE
        if envelope.message_type == IPCMessageType.NODE_TASK_SUBMIT:
            worker = Thread(
                target=handle_task,
                args=(envelope,),
                name=f"flowweaver-executor-task-{envelope.message_id}",
                daemon=True,
            )
            task_workers.append(worker)
            worker.start()
            continue
        responses = process.handle_envelope(envelope)
        for response in responses:
            _write_envelope(stdout, response)
    for worker in task_workers:
        worker.join()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor-id", required=True)
    args = parser.parse_args(argv)
    return run_node_executor_process(executor_id=args.executor_id)


def _write_envelope(stream: TextIO, envelope: IPCEnvelope) -> None:
    stream.write(envelope.model_dump_json())
    stream.write("\n")
    stream.flush()


def _write_process_error(stream: TextIO, error_code: str, error: Exception) -> None:
    stream.write(f"{error_code}: {type(error).__name__}: {error}\n")
    stream.flush()


def _failed_task_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
    error: Exception,
) -> NodeTaskResultModel:
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.FAILED,
        error={
            "message": str(error),
            "error_type": type(error).__name__,
        },
        started_at=now,
        finished_at=now,
    )


def _exit() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
