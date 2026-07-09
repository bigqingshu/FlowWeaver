from __future__ import annotations

from typing import TextIO

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


def write_envelope(stream: TextIO, envelope: IPCEnvelope) -> None:
    stream.write(envelope.model_dump_json())
    stream.write("\n")
    stream.flush()


def write_process_error(stream: TextIO, error_code: str, error: Exception) -> None:
    stream.write(f"{error_code}: {type(error).__name__}: {error}\n")
    stream.flush()


def failed_task_result(
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
