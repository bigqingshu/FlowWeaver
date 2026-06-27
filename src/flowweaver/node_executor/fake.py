from __future__ import annotations

import time
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class FakeNodeExecutor:
    def __init__(
        self,
        *,
        executor_id: str = "fake-executor",
        status: NodeResultStatus = NodeResultStatus.SUCCEEDED,
        delay_seconds: float = 0,
        output_refs: list[str] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self.status = status
        self.delay_seconds = delay_seconds
        self.output_refs = output_refs or []
        self.error = error

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        started_at = utc_now()
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=self.status,
            output_refs=self.output_refs,
            error=self.error,
            started_at=started_at,
            finished_at=utc_now(),
        )
