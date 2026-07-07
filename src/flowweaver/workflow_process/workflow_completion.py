from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeRunStatus,
)

_INCOMPLETE_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.PENDING.value,
        NodeRunStatus.READY.value,
        NodeRunStatus.WAITING_DEPENDENCY.value,
        NodeRunStatus.QUEUED.value,
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
        NodeRunStatus.SUSPECTED_HUNG.value,
    }
)
_SUCCESSFUL_LOOP_RUN_STATUSES = frozenset(
    {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }
)
_SUCCESSFUL_LOOP_ITERATION_STATUSES = frozenset(
    {
        LoopIterationRunStatus.SUCCEEDED.value,
        LoopIterationRunStatus.SKIPPED.value,
    }
)


class WorkflowCompletionEvaluator:
    def __init__(self, store: RuntimeStore) -> None:
        self._store = store

    def can_mark_workflow_succeeded(self, workflow_run_id: str) -> bool:
        node_runs = self._store.list_node_runs(workflow_run_id)
        if not node_runs:
            return False
        if any(node.status in _INCOMPLETE_NODE_STATUSES for node in node_runs):
            return False
        if any(node.status != NodeRunStatus.SUCCEEDED.value for node in node_runs):
            return False

        loop_runs = self._store.list_loop_runs(workflow_run_id)
        for loop in loop_runs:
            if loop.status not in _SUCCESSFUL_LOOP_RUN_STATUSES:
                return False
            if not self._loop_iterations_are_successful(loop.loop_run_id):
                return False
        return True

    def _loop_iterations_are_successful(self, loop_run_id: str) -> bool:
        iterations = self._store.list_loop_iteration_runs(loop_run_id)
        return all(
            iteration.status in _SUCCESSFUL_LOOP_ITERATION_STATUSES
            for iteration in iterations
        )
