from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from flowweaver.common.subprocess_command import python_module_command
from flowweaver.node_executor.ipc_client_messages import (
    INTERMEDIATE_NODE_TASK_MESSAGES,
    cancel_request_envelope,
    ipc_failure_result,
    node_task_result_from_response,
    submit_task_envelope,
)
from flowweaver.node_executor.ipc_client_subprocess_helpers import (
    child_environment as _child_environment,
)
from flowweaver.node_executor.ipc_client_subprocess_helpers import (
    read_response_from_child as _read_response_from_child,
)
from flowweaver.node_executor.ipc_client_subprocess_helpers import (
    src_path as _src_path,
)
from flowweaver.node_executor.ipc_client_subprocess_helpers import (
    subprocess_failure_error as _subprocess_failure_error,
)
from flowweaver.node_executor.ipc_client_subprocess_helpers import (
    write_envelope_to_child as _write_envelope_to_child,
)
from flowweaver.node_executor.ipc_client_types import NodeTaskIpcEventHandler
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class SubprocessNodeExecutorIpcClient:
    def __init__(
        self,
        *,
        executor_id: str = "subprocess-node-executor",
        python_executable: str | None = None,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        command: list[str] | None = None,
        event_handler: NodeTaskIpcEventHandler | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._event_handler = event_handler
        self._closed = False
        self._child = subprocess.Popen(
            command
            or [
                *python_module_command(
                    python_executable=python_executable or sys.executable,
                    module_name="flowweaver.node_executor.process",
                    src_path=_src_path(),
                ),
                "--executor-id",
                executor_id,
            ],
            cwd=str(cwd or _src_path()),
            env=_child_environment(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._expect_ready()

    def set_event_handler(self, handler: NodeTaskIpcEventHandler | None) -> None:
        self._event_handler = handler

    @property
    def closed(self) -> bool:
        return self._closed

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = submit_task_envelope(task)
        if not self._write_envelope(envelope):
            return self._missing_result(task)
        while True:
            response = self._read_response()
            if response is None:
                return self._missing_result(task)
            if response.message_type in INTERMEDIATE_NODE_TASK_MESSAGES:
                self._emit_event(task, response)
                continue
            result = node_task_result_from_response(response)
            if result is not None:
                return result

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        return self._write_envelope(cancel_request_envelope(task, reason=reason))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        stdin = self._child.stdin
        if stdin is not None and not stdin.closed:
            try:
                stdin.close()
            except OSError:
                pass
        try:
            self._child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._child.terminate()
            try:
                self._child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._child.kill()
                self._child.wait(timeout=2)
        for stream in (self._child.stdout, self._child.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    def _expect_ready(self) -> None:
        response = self._read_response()
        if (
            response is not None
            and response.message_type == IPCMessageType.EXECUTOR_READY
            and response.payload.get("executor_id") == self.executor_id
        ):
            return
        self.close()
        raise RuntimeError("Node executor subprocess did not become ready")

    def _write_envelope(self, envelope: IPCEnvelope) -> bool:
        return _write_envelope_to_child(
            self._child,
            closed=self._closed,
            envelope=envelope,
        )

    def _read_response(self) -> IPCEnvelope | None:
        return _read_response_from_child(self._child)

    def _emit_event(self, task: NodeTaskModel, envelope: IPCEnvelope) -> None:
        if self._event_handler is not None:
            self._event_handler(task, envelope)

    def _missing_result(self, task: NodeTaskModel) -> NodeTaskResultModel:
        return ipc_failure_result(
            task,
            executor_id=self.executor_id,
            error=self._failure_error(),
        )

    def _failure_error(self) -> dict[str, Any]:
        return _subprocess_failure_error(self._child)
