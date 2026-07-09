from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
)


def result_already_applied_or_terminal(
    store: RuntimeStore,
    result: NodeTaskResultModel,
) -> NodeTaskApplyResult:
    existing_result = store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    )
    if existing_result is not None:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.ALREADY_APPLIED,
            node_run_id=existing_result.node_run_id,
        )
    return NodeTaskApplyResult(
        NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
        node_run_id=result.node_run_id,
    )
