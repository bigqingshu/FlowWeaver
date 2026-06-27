from __future__ import annotations

import argparse
import sys
from typing import TextIO

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.fake import FakeNodeExecutor
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import (
    ExecutorHeartbeatPayload,
    IPCEnvelope,
    NodeTaskCompletedPayload,
    NodeTaskHeartbeatPayload,
    NodeTaskProgressPayload,
    NodeTaskSubmitPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel


class NodeExecutorProcess:
    def __init__(
        self,
        *,
        executor_id: str,
        executor_factory: NodeExecutorFactory | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._executor_factory = executor_factory or (
            lambda _task: FakeNodeExecutor(executor_id=executor_id)
        )
        self._active_task_ids: set[str] = set()
        self._active_task_correlations: dict[str, str] = {}
        self._pending_task_events: list[IPCEnvelope] = []

    def ready_envelope(self) -> IPCEnvelope:
        return IPCEnvelope(
            message_type=IPCMessageType.EXECUTOR_READY,
            payload={"executor_id": self.executor_id},
        )

    def heartbeat_envelope(self) -> IPCEnvelope:
        return IPCEnvelope(
            message_type=IPCMessageType.EXECUTOR_HEARTBEAT,
            payload=ExecutorHeartbeatPayload(
                executor_id=self.executor_id,
                active_task_ids=sorted(self._active_task_ids),
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
        self._pending_task_events.append(
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
        self._pending_task_events.append(
            self.task_progress_envelope(
                task,
                progress=progress,
                current_stage=current_stage,
                metrics=metrics,
                correlation_id=correlation_id,
            )
        )

    def handle_envelope(self, envelope: IPCEnvelope) -> tuple[IPCEnvelope, ...]:
        if envelope.message_type != IPCMessageType.NODE_TASK_SUBMIT:
            return ()
        task = NodeTaskSubmitPayload.model_validate(envelope.payload)
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
        executor = self._executor_factory(task)
        self._active_task_ids.add(task.task_id)
        self._active_task_correlations[task.task_id] = envelope.message_id
        self._pending_task_events = []
        try:
            result = executor.execute(task)
            task_events = tuple(self._pending_task_events)
        finally:
            self._active_task_ids.discard(task.task_id)
            self._active_task_correlations.pop(task.task_id, None)
            self._pending_task_events = []
        completed = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_COMPLETED,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            correlation_id=envelope.message_id,
            payload=NodeTaskCompletedPayload(result=result).model_dump(mode="json"),
        )
        return (accepted, *task_events, completed)


def run_node_executor_process(
    *,
    executor_id: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    executor_factory: NodeExecutorFactory | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    process = NodeExecutorProcess(
        executor_id=executor_id,
        executor_factory=executor_factory,
    )
    _write_envelope(stdout, process.ready_envelope())
    for line in stdin:
        if not line.strip():
            continue
        envelope = IPCEnvelope.model_validate_json(line)
        for response in process.handle_envelope(envelope):
            _write_envelope(stdout, response)
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


def _exit() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
