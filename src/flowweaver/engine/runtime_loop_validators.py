from __future__ import annotations

from sqlalchemy.orm import Session

from flowweaver.engine.db_models import DataRefRecord, LoopRunRecord, NodeRunRecord


def validate_loop_table_ref(
    session: Session,
    *,
    loop: LoopRunRecord,
    table_ref_id: str,
) -> DataRefRecord:
    table_ref = session.get(DataRefRecord, table_ref_id)
    if table_ref is None:
        raise ValueError(f"Loop table ref not found: {table_ref_id}")
    if table_ref.workflow_run_id != loop.workflow_run_id:
        raise ValueError(
            f"Loop table ref does not belong to workflow run: {table_ref_id}"
        )
    return table_ref


def validate_loop_node_run(
    session: Session,
    *,
    loop: LoopRunRecord,
    node_run_id: str,
) -> NodeRunRecord:
    node_run = session.get(NodeRunRecord, node_run_id)
    if node_run is None:
        raise ValueError(f"Loop node run not found: {node_run_id}")
    if node_run.workflow_run_id != loop.workflow_run_id:
        raise ValueError(
            f"Loop node run does not belong to workflow run: {node_run_id}"
        )
    return node_run
