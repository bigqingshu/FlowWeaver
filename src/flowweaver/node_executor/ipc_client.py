from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from flowweaver.common.time import utc_now
from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.process import NodeExecutorProcess
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskCompletedPayload,
    NodeTaskFailedPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class LocalNodeExecutorIpcClient:
    def __init__(
        self,
        *,
        executor_id: str = "local-node-executor",
        executor_factory: NodeExecutorFactory | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._process = NodeExecutorProcess(
            executor_id=executor_id,
            executor_factory=executor_factory,
        )

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_SUBMIT,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            payload=task.model_dump(mode="json"),
        )
        for response in self._process.handle_envelope(envelope):
            if response.message_type == IPCMessageType.NODE_TASK_COMPLETED:
                return NodeTaskCompletedPayload.model_validate(
                    response.payload
                ).result
            if response.message_type == IPCMessageType.NODE_TASK_FAILED:
                return NodeTaskFailedPayload.model_validate(response.payload).result
        return _missing_result(task, executor_id=self.executor_id)


class SubprocessNodeExecutorIpcClient:
    def __init__(
        self,
        *,
        executor_id: str = "subprocess-node-executor",
        python_executable: str | None = None,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._closed = False
        self._child = subprocess.Popen(
            [
                python_executable or sys.executable,
                "-m",
                "flowweaver.node_executor.process",
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

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_SUBMIT,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            payload=task.model_dump(mode="json"),
        )
        if not self._write_envelope(envelope):
            return _missing_result(task, executor_id=self.executor_id)
        while True:
            response = self._read_response()
            if response is None:
                return _missing_result(task, executor_id=self.executor_id)
            if response.message_type == IPCMessageType.NODE_TASK_COMPLETED:
                return NodeTaskCompletedPayload.model_validate(
                    response.payload
                ).result
            if response.message_type == IPCMessageType.NODE_TASK_FAILED:
                return NodeTaskFailedPayload.model_validate(response.payload).result

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
        if self._closed or self._child.poll() is not None:
            return False
        stdin = self._child.stdin
        if stdin is None or stdin.closed:
            return False
        try:
            stdin.write(envelope.model_dump_json())
            stdin.write("\n")
            stdin.flush()
        except OSError:
            return False
        return True

    def _read_response(self) -> IPCEnvelope | None:
        stdout = self._child.stdout
        if stdout is None or stdout.closed:
            return None
        line = stdout.readline()
        if not line:
            return None
        try:
            return IPCEnvelope.model_validate_json(line)
        except ValueError:
            return None


def _missing_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
) -> NodeTaskResultModel:
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.FAILED,
        error={"message": "Node executor IPC response did not include a result"},
        started_at=now,
        finished_at=now,
    )


def _src_path() -> Path:
    return Path(__file__).resolve().parents[2]


def _child_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env) if base_env is not None else os.environ.copy()
    src_path = _src_path()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(src_path)
        if not existing_pythonpath
        else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )
    return env
