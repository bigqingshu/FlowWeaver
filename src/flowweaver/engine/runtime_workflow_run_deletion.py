from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    InputSnapshotRecord,
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultOutputBindingRecord,
    NodeTaskResultRecord,
    ReadLeaseRecord,
    RuntimeEventRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    TableLeaseRecord,
    WorkflowProcessRecord,
    WorkflowRunRecord,
    WorkflowRunRuntimeOptionsRecord,
)
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_status_guards import (
    ACTIVE_WORKFLOW_PROCESS_STATUSES,
    TERMINAL_WORKFLOW_STATUS_VALUES,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableLeaseStatus,
    TableStorageKind,
)

if TYPE_CHECKING:
    from flowweaver.engine.runtime_store import RuntimeStore

_BLOCKER_SAMPLE_LIMIT = 20
_INTERNAL_STORAGE_KINDS = (
    TableStorageKind.MEMORY.value,
    TableStorageKind.RUNTIME_SQL.value,
)
_CLEANED_LIFECYCLE_STATUSES = (
    LifecycleStatus.RELEASED.value,
    LifecycleStatus.RETIRED.value,
    LifecycleStatus.ORPHANED.value,
)


@dataclass(frozen=True)
class WorkflowRunDeletionResult:
    workflow_run_id: str
    deleted: bool = True


class WorkflowRunDeletionError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


def delete_workflow_run(
    store: RuntimeStore,
    workflow_run_id: str,
) -> WorkflowRunDeletionResult:
    with immediate_session(store.engine) as session:
        return delete_workflow_run_in_session(session, workflow_run_id)


def delete_workflow_run_in_session(
    session: Session,
    workflow_run_id: str,
) -> WorkflowRunDeletionResult:
    run = session.get(WorkflowRunRecord, workflow_run_id)
    if run is None:
        raise WorkflowRunDeletionError(
            "WORKFLOW_RUN_NOT_FOUND",
            "Workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    if run.status not in TERMINAL_WORKFLOW_STATUS_VALUES:
        raise WorkflowRunDeletionError(
            "WORKFLOW_RUN_NOT_TERMINAL",
            "Workflow run must be terminal before it can be deleted",
            details={
                "workflow_run_id": workflow_run_id,
                "status": run.status,
            },
        )

    _reject_active_processes(session, workflow_run_id)
    _reject_active_shared_publications(session, workflow_run_id)
    _reject_active_publication_readers(session, workflow_run_id)
    _reject_active_table_leases(session, workflow_run_id)
    _reject_cross_run_table_references(session, workflow_run_id)
    _reject_uncleaned_internal_tables(session, workflow_run_id)
    _delete_run_records(session, run)
    return WorkflowRunDeletionResult(workflow_run_id=workflow_run_id)


def _reject_active_processes(session: Session, workflow_run_id: str) -> None:
    conditions = (
        WorkflowProcessRecord.workflow_run_id == workflow_run_id,
        WorkflowProcessRecord.status.in_(ACTIVE_WORKFLOW_PROCESS_STATUSES),
    )
    count = _count(session, WorkflowProcessRecord, *conditions)
    if count == 0:
        return
    process_ids = list(
        session.scalars(
            select(WorkflowProcessRecord.process_id)
            .where(*conditions)
            .order_by(WorkflowProcessRecord.process_id)
            .limit(_BLOCKER_SAMPLE_LIMIT)
        )
    )
    raise WorkflowRunDeletionError(
        "WORKFLOW_RUN_PROCESS_ACTIVE",
        "Workflow run still has an active process",
        details={
            "workflow_run_id": workflow_run_id,
            "blocking_count": count,
            "process_ids": process_ids,
        },
    )


def _reject_active_shared_publications(
    session: Session,
    workflow_run_id: str,
) -> None:
    conditions = (
        SharedPublicationRecord.producer_run_id == workflow_run_id,
        SharedPublicationRecord.status != "RELEASED",
    )
    count = _count(session, SharedPublicationRecord, *conditions)
    if count == 0:
        return
    publication_ids = list(
        session.scalars(
            select(SharedPublicationRecord.publication_id)
            .where(*conditions)
            .order_by(SharedPublicationRecord.publication_id)
            .limit(_BLOCKER_SAMPLE_LIMIT)
        )
    )
    _raise_delete_blocked(
        workflow_run_id,
        blocker="active_shared_publication",
        count=count,
        ids=publication_ids,
    )


def _reject_active_publication_readers(
    session: Session,
    workflow_run_id: str,
) -> None:
    publication_ids = select(SharedPublicationRecord.publication_id).where(
        SharedPublicationRecord.producer_run_id == workflow_run_id
    )
    now_text = _datetime_to_text(utc_now())
    conditions = (
        ReadLeaseRecord.publication_id.in_(publication_ids),
        ReadLeaseRecord.consumer_workflow_run_id != workflow_run_id,
        ReadLeaseRecord.released_at.is_(None),
        ReadLeaseRecord.expires_at > now_text,
    )
    count = _count(session, ReadLeaseRecord, *conditions)
    if count == 0:
        return
    lease_ids = list(
        session.scalars(
            select(ReadLeaseRecord.lease_id)
            .where(*conditions)
            .order_by(ReadLeaseRecord.lease_id)
            .limit(_BLOCKER_SAMPLE_LIMIT)
        )
    )
    _raise_delete_blocked(
        workflow_run_id,
        blocker="active_publication_read_lease",
        count=count,
        ids=lease_ids,
    )


def _reject_active_table_leases(session: Session, workflow_run_id: str) -> None:
    now_text = _datetime_to_text(utc_now())
    statement = (
        select(TableLeaseRecord.lease_id)
        .join(
            DataRefRecord,
            DataRefRecord.table_ref_id == TableLeaseRecord.table_ref_id,
        )
        .where(DataRefRecord.workflow_run_id == workflow_run_id)
        .where(TableLeaseRecord.status == TableLeaseStatus.ACTIVE.value)
        .where(TableLeaseRecord.expires_at > now_text)
    )
    count = int(
        session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    )
    if count == 0:
        return
    lease_ids = list(
        session.scalars(
            statement.order_by(TableLeaseRecord.lease_id).limit(_BLOCKER_SAMPLE_LIMIT)
        )
    )
    _raise_delete_blocked(
        workflow_run_id,
        blocker="active_table_lease",
        count=count,
        ids=lease_ids,
    )


def _reject_cross_run_table_references(
    session: Session,
    workflow_run_id: str,
) -> None:
    table_ref_ids = select(DataRefRecord.table_ref_id).where(
        DataRefRecord.workflow_run_id == workflow_run_id
    )
    iteration_ref_statement = (
        select(LoopIterationRunRecord.loop_iteration_id)
        .join(
            LoopRunRecord,
            LoopRunRecord.loop_run_id == LoopIterationRunRecord.loop_run_id,
        )
        .where(LoopRunRecord.workflow_run_id != workflow_run_id)
        .where(
            or_(
                LoopIterationRunRecord.input_table_ref_id.in_(table_ref_ids),
                LoopIterationRunRecord.output_table_ref_id.in_(table_ref_ids),
            )
        )
    )
    linked_ref_statement = (
        select(LoopIterationTableRefRecord.loop_iteration_id)
        .join(
            LoopIterationRunRecord,
            LoopIterationRunRecord.loop_iteration_id
            == LoopIterationTableRefRecord.loop_iteration_id,
        )
        .join(
            LoopRunRecord,
            LoopRunRecord.loop_run_id == LoopIterationRunRecord.loop_run_id,
        )
        .where(LoopRunRecord.workflow_run_id != workflow_run_id)
        .where(LoopIterationTableRefRecord.table_ref_id.in_(table_ref_ids))
    )
    foreign_publication_statement = (
        select(SharedPublicationRecord.publication_id)
        .join(
            SharedPublicationMemberRecord,
            SharedPublicationMemberRecord.publication_id
            == SharedPublicationRecord.publication_id,
        )
        .where(SharedPublicationRecord.producer_run_id != workflow_run_id)
        .where(SharedPublicationMemberRecord.table_ref_id.in_(table_ref_ids))
    )
    blockers = (
        ("cross_run_loop_iteration", iteration_ref_statement),
        ("cross_run_loop_table_ref", linked_ref_statement),
        ("foreign_shared_publication", foreign_publication_statement),
    )
    for blocker, statement in blockers:
        count = int(
            session.scalar(
                select(func.count()).select_from(statement.distinct().subquery())
            )
            or 0
        )
        if count == 0:
            continue
        ids = list(
            session.scalars(
                statement.distinct().order_by(*statement.selected_columns).limit(
                    _BLOCKER_SAMPLE_LIMIT
                )
            )
        )
        _raise_delete_blocked(
            workflow_run_id,
            blocker=blocker,
            count=count,
            ids=ids,
        )


def _reject_uncleaned_internal_tables(
    session: Session,
    workflow_run_id: str,
) -> None:
    conditions = (
        DataRefRecord.workflow_run_id == workflow_run_id,
        DataRefRecord.storage_kind.in_(_INTERNAL_STORAGE_KINDS),
        DataRefRecord.lifecycle_status.notin_(_CLEANED_LIFECYCLE_STATUSES),
    )
    count = _count(session, DataRefRecord, *conditions)
    if count == 0:
        return
    table_ref_ids = list(
        session.scalars(
            select(DataRefRecord.table_ref_id)
            .where(*conditions)
            .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
            .limit(_BLOCKER_SAMPLE_LIMIT)
        )
    )
    raise WorkflowRunDeletionError(
        "WORKFLOW_RUN_TABLES_NOT_CLEANED",
        "Workflow run internal tables must be cleaned before deletion",
        details={
            "workflow_run_id": workflow_run_id,
            "blocking_count": count,
            "table_ref_ids": table_ref_ids,
        },
    )


def _delete_run_records(
    session: Session,
    run: WorkflowRunRecord,
) -> None:
    workflow_run_id = run.workflow_run_id
    node_run_ids = select(NodeRunRecord.node_run_id).where(
        NodeRunRecord.workflow_run_id == workflow_run_id
    )
    node_task_ids = select(NodeTaskRecord.task_id).where(
        NodeTaskRecord.workflow_run_id == workflow_run_id
    )
    node_result_ids = select(NodeTaskResultRecord.result_id).where(
        or_(
            NodeTaskResultRecord.node_run_id.in_(node_run_ids),
            NodeTaskResultRecord.task_id.in_(node_task_ids),
        )
    )
    loop_run_ids = select(LoopRunRecord.loop_run_id).where(
        LoopRunRecord.workflow_run_id == workflow_run_id
    )
    loop_iteration_ids = select(LoopIterationRunRecord.loop_iteration_id).where(
        LoopIterationRunRecord.loop_run_id.in_(loop_run_ids)
    )
    table_ref_ids = select(DataRefRecord.table_ref_id).where(
        DataRefRecord.workflow_run_id == workflow_run_id
    )
    publication_ids = select(SharedPublicationRecord.publication_id).where(
        SharedPublicationRecord.producer_run_id == workflow_run_id
    )

    _delete_where(
        session,
        LoopIterationTableRefRecord,
        LoopIterationTableRefRecord.loop_iteration_id.in_(loop_iteration_ids),
    )
    _delete_where(
        session,
        LoopIterationNodeRunRecord,
        LoopIterationNodeRunRecord.loop_iteration_id.in_(loop_iteration_ids),
    )
    _delete_where(
        session,
        LoopIterationRunRecord,
        LoopIterationRunRecord.loop_run_id.in_(loop_run_ids),
    )
    _delete_where(
        session,
        LoopRunRecord,
        LoopRunRecord.workflow_run_id == workflow_run_id,
    )
    _delete_where(
        session,
        NodeTaskResultOutputBindingRecord,
        or_(
            NodeTaskResultOutputBindingRecord.node_run_id.in_(node_run_ids),
            NodeTaskResultOutputBindingRecord.task_id.in_(node_task_ids),
            NodeTaskResultOutputBindingRecord.result_id.in_(node_result_ids),
        ),
    )
    _delete_where(
        session,
        NodeTaskResultRecord,
        or_(
            NodeTaskResultRecord.node_run_id.in_(node_run_ids),
            NodeTaskResultRecord.task_id.in_(node_task_ids),
        ),
    )
    _delete_where(
        session,
        NodeTaskRecord,
        NodeTaskRecord.workflow_run_id == workflow_run_id,
    )
    _delete_where(
        session,
        RuntimeEventRecord,
        or_(
            RuntimeEventRecord.workflow_run_id == workflow_run_id,
            RuntimeEventRecord.node_run_id.in_(node_run_ids),
        ),
    )
    _delete_where(
        session,
        ReadLeaseRecord,
        or_(
            ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id,
            ReadLeaseRecord.publication_id.in_(publication_ids),
        ),
    )
    _delete_where(
        session,
        SharedPublicationMemberRecord,
        SharedPublicationMemberRecord.publication_id.in_(publication_ids),
    )
    _delete_where(
        session,
        SharedPublicationRecord,
        SharedPublicationRecord.producer_run_id == workflow_run_id,
    )
    _delete_where(
        session,
        TableLeaseRecord,
        TableLeaseRecord.table_ref_id.in_(table_ref_ids),
    )
    _delete_where(
        session,
        DataRefRecord,
        DataRefRecord.workflow_run_id == workflow_run_id,
    )
    _delete_where(
        session,
        NodeRunRecord,
        NodeRunRecord.workflow_run_id == workflow_run_id,
    )
    _delete_where(
        session,
        WorkflowRunRuntimeOptionsRecord,
        WorkflowRunRuntimeOptionsRecord.workflow_run_id == workflow_run_id,
    )
    input_snapshot_condition = (
        InputSnapshotRecord.workflow_run_id == workflow_run_id
    )
    if run.input_snapshot_id is not None:
        input_snapshot_condition = or_(
            input_snapshot_condition,
            InputSnapshotRecord.input_snapshot_id == run.input_snapshot_id,
        )
    _delete_where(session, InputSnapshotRecord, input_snapshot_condition)
    _delete_where(
        session,
        WorkflowProcessRecord,
        WorkflowProcessRecord.workflow_run_id == workflow_run_id,
    )
    session.delete(run)


def _delete_where(session: Session, record_type: type[Any], condition: Any) -> None:
    session.execute(
        sa_delete(record_type)
        .where(condition)
        .execution_options(synchronize_session=False)
    )


def _count(session: Session, record_type: type[Any], *conditions: Any) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(record_type).where(*conditions)
        )
        or 0
    )


def _raise_delete_blocked(
    workflow_run_id: str,
    *,
    blocker: str,
    count: int,
    ids: list[str],
) -> None:
    raise WorkflowRunDeletionError(
        "WORKFLOW_RUN_DELETE_BLOCKED",
        "Workflow run still has dependent runtime records",
        details={
            "workflow_run_id": workflow_run_id,
            "blocker": blocker,
            "blocking_count": count,
            "blocking_ids": ids,
        },
    )
