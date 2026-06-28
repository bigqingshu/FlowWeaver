from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import Connection, CursorResult, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    InputSnapshotRecord,
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultRecord,
    ReadLeaseRecord,
    RuntimeEventRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    WorkflowDefinitionRecord,
    WorkflowProcessRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeResultStatus,
    NodeRunStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowProcessStatus,
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    revision_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkflowRevision:
    revision_id: str
    workflow_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    created_at: datetime
    created_by: str | None


@dataclass(frozen=True)
class WorkflowRun:
    workflow_run_id: str
    workflow_id: str
    revision_id: str | None
    workflow_version: int
    definition_hash: str | None
    status: str
    state_version: int
    owner_process_id: str | None
    process_generation: int
    fencing_token: str | None
    input_snapshot_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    completion_reason: str | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class WorkflowProcess:
    process_id: str
    workflow_run_id: str
    os_pid: int | None
    process_generation: int
    fencing_token: str | None
    status: str
    started_at: datetime
    last_heartbeat_at: datetime | None
    cancel_requested_at: datetime | None
    exited_at: datetime | None
    exit_code: int | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class NodeRun:
    node_run_id: str
    workflow_run_id: str
    node_instance_id: str
    node_type: str
    status: str
    state_version: int
    executor_id: str | None
    progress: float | None
    current_stage: str | None
    attempt: int
    started_at: datetime | None
    finished_at: datetime | None
    last_heartbeat: datetime | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class RuntimeEventLog:
    event_id: str
    sequence_number: int
    event_version: str
    event_type: str
    timestamp: datetime
    workflow_run_id: str | None
    node_run_id: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class SharedPublicationMember:
    publication_id: str
    export_name: str
    table_ref_id: str
    exact_table_version: int


@dataclass(frozen=True)
class SharedPublication:
    publication_id: str
    share_name: str
    publication_version: int
    producer_workflow_id: str
    producer_run_id: str
    status: str
    input_snapshot_id: str | None
    retention_policy: dict[str, Any]
    created_at: datetime
    members: tuple[SharedPublicationMember, ...]


@dataclass(frozen=True)
class InputSnapshotEntry:
    source_name: str
    publication_id: str
    publication_version: int
    selected_members: tuple[str, ...]


@dataclass(frozen=True)
class InputSnapshot:
    input_snapshot_id: str
    workflow_run_id: str
    inputs: tuple[InputSnapshotEntry, ...]
    created_at: datetime


@dataclass(frozen=True)
class ReadLease:
    lease_id: str
    publication_id: str
    publication_version: int
    selected_members: tuple[str, ...]
    consumer_workflow_run_id: str
    acquired_at: datetime
    expires_at: datetime
    released_at: datetime | None


_TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowRunStatus.SUCCEEDED.value,
        WorkflowRunStatus.FAILED.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.ABORTED.value,
    }
)
_TERMINAL_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.TIMED_OUT.value,
        NodeRunStatus.SUCCEEDED.value,
        NodeRunStatus.FAILED.value,
        NodeRunStatus.CANCELLED.value,
        NodeRunStatus.SKIPPED.value,
    }
)
_WORKFLOW_RUN_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    WorkflowRunStatus.RUNNING.value: (WorkflowRunStatus.PENDING.value,),
    WorkflowRunStatus.SUCCEEDED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.FAILED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.CANCELLED.value: (WorkflowRunStatus.RUNNING.value,),
    WorkflowRunStatus.ABORTED.value: (WorkflowRunStatus.RUNNING.value,),
}
_NODE_RUN_STATUS_SOURCES: dict[str, tuple[str, ...]] = {
    NodeRunStatus.READY.value: (NodeRunStatus.WAITING_DEPENDENCY.value,),
    NodeRunStatus.QUEUED.value: (NodeRunStatus.READY.value,),
    NodeRunStatus.RUNNING.value: (NodeRunStatus.QUEUED.value,),
    NodeRunStatus.LONG_RUNNING.value: (NodeRunStatus.RUNNING.value,),
    NodeRunStatus.SUCCEEDED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.FAILED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.CANCELLED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    ),
    NodeRunStatus.CANCEL_REQUESTED.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
    ),
    NodeRunStatus.TIMED_OUT.value: (
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    ),
    NodeRunStatus.SKIPPED.value: (
        NodeRunStatus.PENDING.value,
        NodeRunStatus.READY.value,
        NodeRunStatus.WAITING_DEPENDENCY.value,
        NodeRunStatus.WAITING_PERMISSION.value,
    ),
}
_ACTIVE_WORKFLOW_PROCESS_STATUSES = frozenset(
    {
        WorkflowProcessStatus.STARTING.value,
        WorkflowProcessStatus.RUNNING.value,
        WorkflowProcessStatus.CANCEL_REQUESTED.value,
    }
)
_INTERRUPTED_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.QUEUED.value,
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }
)


class _AtomicNodeTaskResultUpdateRejected(Exception):
    pass


class RuntimeStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = create_sqlite_engine(database_url)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> RuntimeStore:
        return cls(sqlite_url(path))

    def create_workflow_definition(
        self,
        *,
        name: str,
        definition: dict[str, Any],
        workflow_id: str | None = None,
        created_by: str | None = None,
    ) -> WorkflowDefinition:
        now = utc_now()
        workflow_id = workflow_id or new_id()
        revision_id = new_id()
        definition_json = _json_dumps(definition)
        definition_hash = _definition_hash(definition_json)
        workflow = WorkflowRecord(
            workflow_id=workflow_id,
            name=name,
            current_revision_id=revision_id,
            status="ACTIVE",
            created_at=_datetime_to_text(now),
            updated_at=_datetime_to_text(now),
        )
        revision = WorkflowRevisionRecord(
            revision_id=revision_id,
            workflow_id=workflow_id,
            version=1,
            definition_json=definition_json,
            definition_hash=definition_hash,
            created_at=_datetime_to_text(now),
            created_by=created_by,
        )
        legacy = WorkflowDefinitionRecord(
            workflow_id=workflow_id,
            name=name,
            version=1,
            definition_json=definition_json,
            created_at=_datetime_to_text(now),
            updated_at=_datetime_to_text(now),
        )
        with self._session_factory.begin() as session:
            session.add_all([workflow, revision, legacy])
        return _workflow_definition_from_records(workflow, revision)

    def get_workflow_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._session_factory() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return None
            revision = session.get(WorkflowRevisionRecord, workflow.current_revision_id)
            if revision is None:
                return None
            return _workflow_definition_from_records(workflow, revision)

    def list_workflow_definitions(self) -> list[WorkflowDefinition]:
        with self._session_factory() as session:
            workflows = session.scalars(
                select(WorkflowRecord)
                .where(WorkflowRecord.status != "DELETED")
                .order_by(WorkflowRecord.created_at)
            ).all()
            revisions = {
                revision.revision_id: revision
                for revision in session.scalars(
                    select(WorkflowRevisionRecord).where(
                        WorkflowRevisionRecord.revision_id.in_(
                            [
                                workflow.current_revision_id
                                for workflow in workflows
                                if workflow.current_revision_id
                            ]
                        )
                    )
                )
            }
            return [
                _workflow_definition_from_records(
                    workflow,
                    revisions[workflow.current_revision_id],
                )
                for workflow in workflows
                if workflow.current_revision_id in revisions
            ]

    def update_workflow_definition(
        self,
        workflow_id: str,
        *,
        name: str | None = None,
        definition: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> WorkflowDefinition | None:
        updated: WorkflowDefinition | None = None
        with self._session_factory.begin() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return None
            if name is not None:
                workflow.name = name
            current_revision = session.get(
                WorkflowRevisionRecord,
                workflow.current_revision_id,
            )
            if current_revision is None:
                return None
            if definition is not None:
                revision = WorkflowRevisionRecord(
                    revision_id=new_id(),
                    workflow_id=workflow_id,
                    version=current_revision.version + 1,
                    definition_json=_json_dumps(definition),
                    definition_hash=_definition_hash(_json_dumps(definition)),
                    created_at=_datetime_to_text(utc_now()),
                    created_by=created_by,
                )
                session.add(revision)
                workflow.current_revision_id = revision.revision_id
                current_revision = revision
            workflow.updated_at = _datetime_to_text(utc_now())
            legacy = session.get(WorkflowDefinitionRecord, workflow_id)
            if legacy is not None:
                legacy.name = workflow.name
                legacy.version = current_revision.version
                legacy.definition_json = current_revision.definition_json
                legacy.updated_at = workflow.updated_at
            updated = _workflow_definition_from_records(workflow, current_revision)
        return updated

    def delete_workflow_definition(self, workflow_id: str) -> bool:
        with self._session_factory.begin() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return False
            workflow.status = "DELETED"
            workflow.updated_at = _datetime_to_text(utc_now())
        return True

    def list_workflow_revisions(self, workflow_id: str) -> list[WorkflowRevision]:
        with self._session_factory() as session:
            records = session.scalars(
                select(WorkflowRevisionRecord)
                .where(WorkflowRevisionRecord.workflow_id == workflow_id)
                .order_by(WorkflowRevisionRecord.version)
            ).all()
            return [_workflow_revision_from_record(record) for record in records]

    def get_workflow_revision(self, revision_id: str) -> WorkflowRevision | None:
        with self._session_factory() as session:
            record = session.get(WorkflowRevisionRecord, revision_id)
            if record is None:
                return None
            return _workflow_revision_from_record(record)

    def create_workflow_run(
        self,
        *,
        workflow_id: str,
        workflow_version: int | None = None,
        revision_id: str | None = None,
        workflow_run_id: str | None = None,
        status: WorkflowRunStatus = WorkflowRunStatus.PENDING,
        started_at: datetime | None = None,
    ) -> WorkflowRun:
        if workflow_version is not None:
            raise ValueError("Workflow run version is derived from revision")
        with self._session_factory.begin() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None:
                raise ValueError(f"Workflow not found: {workflow_id}")
            if revision_id is None:
                if workflow.current_revision_id is None:
                    raise ValueError(f"Workflow not found: {workflow_id}")
                revision_id = workflow.current_revision_id
            revision = session.get(WorkflowRevisionRecord, revision_id)
            if revision is None:
                raise ValueError(f"Workflow revision not found: {revision_id}")
            if revision.workflow_id != workflow_id:
                raise ValueError(
                    f"Workflow revision {revision_id} does not belong to {workflow_id}"
                )
            record = WorkflowRunRecord(
                workflow_run_id=workflow_run_id or new_id(),
                workflow_id=workflow_id,
                revision_id=revision.revision_id,
                workflow_version=revision.version,
                definition_hash=revision.definition_hash,
                status=status.value,
                state_version=0,
                owner_process_id=None,
                process_generation=0,
                fencing_token=None,
                input_snapshot_id=None,
                started_at=_optional_datetime_to_text(started_at),
                finished_at=None,
                completion_reason=None,
                error_json=None,
            )
            session.add(record)
        return _workflow_run_from_record(record)

    def get_workflow_run(self, workflow_run_id: str) -> WorkflowRun | None:
        with self._session_factory() as session:
            record = session.get(WorkflowRunRecord, workflow_run_id)
            if record is None:
                return None
            return _workflow_run_from_record(record)

    def workflow_run_is_owned_by(
        self,
        *,
        workflow_run_id: str,
        process_id: str,
        process_generation: int,
    ) -> bool:
        with self._session_factory() as session:
            return _workflow_run_matches_owner(
                session,
                workflow_run_id=workflow_run_id,
                owner_process_id=process_id,
                process_generation=process_generation,
            )

    def list_workflow_runs(
        self,
        *,
        workflow_id: str | None = None,
        statuses: Iterable[WorkflowRunStatus | str] | None = None,
    ) -> list[WorkflowRun]:
        statement = select(WorkflowRunRecord).order_by(WorkflowRunRecord.started_at)
        if workflow_id is not None:
            statement = statement.where(WorkflowRunRecord.workflow_id == workflow_id)
        if statuses is not None:
            status_values = [
                status.value if isinstance(status, WorkflowRunStatus) else status
                for status in statuses
            ]
            statement = statement.where(WorkflowRunRecord.status.in_(status_values))

        with self._session_factory() as session:
            return [
                _workflow_run_from_record(record)
                for record in session.scalars(statement)
            ]

    def update_workflow_run_status(
        self,
        workflow_run_id: str,
        status: WorkflowRunStatus,
        *,
        finished_at: datetime | None = None,
        completion_reason: WorkflowRunCompletionReason | str | None = None,
        error: dict[str, Any] | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[WorkflowRunStatus | str] | None = None,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> WorkflowRun | None:
        with self._session_factory.begin() as session:
            source_statuses = (
                _workflow_run_status_values(allowed_source_statuses)
                if allowed_source_statuses is not None
                else list(_WORKFLOW_RUN_STATUS_SOURCES.get(status.value, ()))
            )
            statement = (
                update(WorkflowRunRecord)
                .where(WorkflowRunRecord.workflow_run_id == workflow_run_id)
                .where(WorkflowRunRecord.status.notin_(_TERMINAL_WORKFLOW_STATUSES))
                .values(
                    status=status.value,
                    state_version=WorkflowRunRecord.state_version + 1,
                    finished_at=_optional_datetime_to_text(finished_at),
                    completion_reason=_optional_completion_reason_value(
                        completion_reason
                    ),
                    error_json=_json_dumps(error) if error is not None else None,
                )
            )
            if expected_state_version is not None:
                statement = statement.where(
                    WorkflowRunRecord.state_version == expected_state_version
                )
            statement = statement.where(WorkflowRunRecord.status.in_(source_statuses))
            if owner_process_id is not None:
                statement = statement.where(
                    WorkflowRunRecord.owner_process_id == owner_process_id
                )
            if process_generation is not None:
                statement = statement.where(
                    WorkflowRunRecord.process_generation == process_generation
                )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(WorkflowRunRecord, workflow_run_id)
            if record is None:
                return None
            return _workflow_run_from_record(record)

    def create_workflow_process(
        self,
        *,
        workflow_run_id: str,
        process_id: str | None = None,
        os_pid: int | None = None,
        process_generation: int = 0,
        fencing_token: str | None = None,
    ) -> WorkflowProcess:
        now = utc_now()
        record = WorkflowProcessRecord(
            process_id=process_id or new_id(),
            workflow_run_id=workflow_run_id,
            os_pid=os_pid,
            process_generation=process_generation,
            fencing_token=fencing_token,
            status=WorkflowProcessStatus.STARTING.value,
            started_at=_datetime_to_text(now),
            last_heartbeat_at=None,
            cancel_requested_at=None,
            exited_at=None,
            exit_code=None,
            error_json=None,
        )
        with self._session_factory.begin() as session:
            session.add(record)
        return _workflow_process_from_record(record)

    def claim_workflow_process(
        self,
        *,
        workflow_run_id: str,
        process_id: str | None = None,
    ) -> WorkflowProcess | None:
        now = utc_now()
        process_id = process_id or new_id()
        fencing_token = new_id()
        with self._immediate_session() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None or run.status in _TERMINAL_WORKFLOW_STATUSES:
                return None
            active_process = session.scalar(
                select(WorkflowProcessRecord)
                .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
                .where(
                    WorkflowProcessRecord.status.in_(
                        _ACTIVE_WORKFLOW_PROCESS_STATUSES
                    )
                )
                .order_by(WorkflowProcessRecord.started_at.desc())
            )
            if active_process is not None:
                return None
            generation = run.process_generation + 1
            run.owner_process_id = process_id
            run.process_generation = generation
            run.fencing_token = fencing_token
            run.state_version += 1
            record = WorkflowProcessRecord(
                process_id=process_id,
                workflow_run_id=workflow_run_id,
                os_pid=None,
                process_generation=generation,
                fencing_token=fencing_token,
                status=WorkflowProcessStatus.STARTING.value,
                started_at=_datetime_to_text(now),
                last_heartbeat_at=None,
                cancel_requested_at=None,
                exited_at=None,
                exit_code=None,
                error_json=None,
            )
            session.add(record)
            return _workflow_process_from_record(record)

    def get_workflow_process(self, process_id: str) -> WorkflowProcess | None:
        with self._session_factory() as session:
            record = session.get(WorkflowProcessRecord, process_id)
            if record is None:
                return None
            return _workflow_process_from_record(record)

    def get_workflow_process_for_run(
        self,
        workflow_run_id: str,
    ) -> WorkflowProcess | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(WorkflowProcessRecord)
                .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
                .order_by(WorkflowProcessRecord.started_at.desc())
            )
            if record is None:
                return None
            return _workflow_process_from_record(record)

    def update_workflow_process_pid(
        self,
        process_id: str,
        os_pid: int,
    ) -> WorkflowProcess | None:
        with self._session_factory.begin() as session:
            record = session.get(WorkflowProcessRecord, process_id)
            if record is None:
                return None
            record.os_pid = os_pid
            return _workflow_process_from_record(record)

    def record_workflow_process_heartbeat(
        self,
        process_id: str,
        *,
        process_generation: int | None = None,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(WorkflowProcessRecord, process_id)
            if record is None:
                return None
            if (
                process_generation is not None
                and record.process_generation != process_generation
            ):
                return None
            if record.status not in _ACTIVE_WORKFLOW_PROCESS_STATUSES:
                return None
            if record.status == WorkflowProcessStatus.STARTING.value:
                record.status = WorkflowProcessStatus.RUNNING.value
            record.last_heartbeat_at = _datetime_to_text(now)
            return _workflow_process_from_record(record)

    def request_workflow_process_cancel(
        self,
        workflow_run_id: str,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(WorkflowProcessRecord)
                .where(WorkflowProcessRecord.workflow_run_id == workflow_run_id)
                .order_by(WorkflowProcessRecord.started_at.desc())
            )
            if record is None:
                return None
            if record.status in {
                WorkflowProcessStatus.STARTING.value,
                WorkflowProcessStatus.RUNNING.value,
            }:
                record.status = WorkflowProcessStatus.CANCEL_REQUESTED.value
                record.cancel_requested_at = _datetime_to_text(now)
            return _workflow_process_from_record(record)

    def mark_workflow_process_exited(
        self,
        process_id: str,
        *,
        exit_code: int,
        error: dict[str, Any] | None = None,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(WorkflowProcessRecord, process_id)
            if record is None:
                return None
            record.status = (
                WorkflowProcessStatus.EXITED.value
                if exit_code == 0
                else WorkflowProcessStatus.FAILED.value
            )
            record.exited_at = _datetime_to_text(now)
            record.exit_code = exit_code
            record.error_json = _json_dumps(error) if error else None
            return _workflow_process_from_record(record)

    def mark_lost_workflow_processes(
        self,
        *,
        stale_before: datetime,
        starting_stale_before: datetime | None = None,
    ) -> list[WorkflowProcess]:
        lost: list[WorkflowProcess] = []
        with self._session_factory.begin() as session:
            records = list(
                session.scalars(
                    select(WorkflowProcessRecord)
                    .where(WorkflowProcessRecord.status.in_(_ACTIVE_WORKFLOW_PROCESS_STATUSES))
                )
            )
            now = utc_now()
            for record in records:
                if record.status == WorkflowProcessStatus.STARTING.value:
                    if (
                        starting_stale_before is None
                        or record.started_at >= _datetime_to_text(starting_stale_before)
                    ):
                        continue
                elif (
                    record.last_heartbeat_at is None
                    or record.last_heartbeat_at >= _datetime_to_text(stale_before)
                ):
                    continue
                record.status = WorkflowProcessStatus.LOST.value
                record.exited_at = _datetime_to_text(now)
                lost.append(_workflow_process_from_record(record))
        return lost

    def abort_workflow_run_for_process(
        self,
        process_id: str,
        *,
        reason: str,
    ) -> WorkflowRun | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            process = session.get(WorkflowProcessRecord, process_id)
            if process is None:
                return None
            run = session.get(WorkflowRunRecord, process.workflow_run_id)
            if run is None:
                return None
            statement = (
                update(WorkflowRunRecord)
                .where(WorkflowRunRecord.workflow_run_id == run.workflow_run_id)
                .where(WorkflowRunRecord.status.notin_(_TERMINAL_WORKFLOW_STATUSES))
                .where(WorkflowRunRecord.owner_process_id == process.process_id)
                .where(
                    WorkflowRunRecord.process_generation
                    == process.process_generation
                )
                .values(
                    status=WorkflowRunStatus.ABORTED.value,
                    state_version=WorkflowRunRecord.state_version + 1,
                    finished_at=_datetime_to_text(now),
                    error_json=_json_dumps(
                        {
                            "reason": reason,
                            "process_id": process.process_id,
                            "process_generation": process.process_generation,
                        }
                    ),
                )
            )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return _workflow_run_from_record(run)
            session.execute(
                update(NodeRunRecord)
                .where(NodeRunRecord.workflow_run_id == run.workflow_run_id)
                .where(NodeRunRecord.status.in_(_INTERRUPTED_NODE_STATUSES))
                .values(
                    status=NodeRunStatus.CANCELLED.value,
                    state_version=NodeRunRecord.state_version + 1,
                    finished_at=_datetime_to_text(now),
                    error_json=_json_dumps(
                        {
                            "reason": reason,
                            "process_id": process.process_id,
                            "process_generation": process.process_generation,
                        }
                    ),
                )
            )
            loaded = session.get(WorkflowRunRecord, run.workflow_run_id)
            if loaded is None:
                return None
            return _workflow_run_from_record(loaded)

    @contextmanager
    def _immediate_session(self) -> Iterator[Session]:
        connection: Connection = self.engine.connect()
        session = Session(bind=connection, expire_on_commit=False)
        try:
            if self.database_url.startswith("sqlite"):
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                connection.begin()
            yield session
            session.flush()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            session.close()
            connection.close()

    def create_node_run(
        self,
        *,
        workflow_run_id: str,
        node_instance_id: str,
        node_type: str,
        node_run_id: str | None = None,
        status: NodeRunStatus = NodeRunStatus.PENDING,
        executor_id: str | None = None,
        attempt: int = 1,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> NodeRun:
        record = NodeRunRecord(
            node_run_id=node_run_id or new_id(),
            workflow_run_id=workflow_run_id,
            node_instance_id=node_instance_id,
            node_type=node_type,
            status=status.value,
            state_version=0,
            executor_id=executor_id,
            progress=None,
            current_stage=None,
            attempt=attempt,
            started_at=None,
            finished_at=None,
            last_heartbeat=None,
            error_json=None,
        )
        with self._session_factory.begin() as session:
            if owner_process_id is not None or process_generation is not None:
                if not _workflow_run_matches_owner(
                    session,
                    workflow_run_id=workflow_run_id,
                    owner_process_id=owner_process_id,
                    process_generation=process_generation,
                ):
                    raise PermissionError("WORKFLOW_RUN_OWNER_MISMATCH")
            session.add(record)
        return _node_run_from_record(record)

    def get_node_run(self, node_run_id: str) -> NodeRun | None:
        with self._session_factory() as session:
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def get_node_run_for_instance(
        self,
        *,
        workflow_run_id: str,
        node_instance_id: str,
    ) -> NodeRun | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeRunRecord)
                .where(NodeRunRecord.workflow_run_id == workflow_run_id)
                .where(NodeRunRecord.node_instance_id == node_instance_id)
            )
            if record is None:
                return None
            return _node_run_from_record(record)

    def create_node_task(self, task: NodeTaskModel) -> NodeTaskModel:
        with self._session_factory.begin() as session:
            session.add(_node_task_to_record(task))
        return task

    def get_node_task(self, task_id: str) -> NodeTaskModel | None:
        with self._session_factory() as session:
            record = session.get(NodeTaskRecord, task_id)
            if record is None:
                return None
            return _node_task_from_record(record)

    def update_node_task_runtime_state(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
        heartbeat_at: datetime | None = None,
        progress: float | None = None,
        current_stage: str | None = None,
    ) -> NodeRun | None:
        values: dict[str, Any] = {
            "last_heartbeat": _datetime_to_text(heartbeat_at or utc_now()),
        }
        if progress is not None:
            values["progress"] = progress
        if current_stage is not None:
            values["current_stage"] = current_stage
        with self._session_factory.begin() as session:
            task_check = (
                select(NodeTaskRecord.task_id)
                .where(NodeTaskRecord.task_id == task.task_id)
                .where(NodeTaskRecord.node_run_id == task.node_run_id)
                .where(NodeTaskRecord.attempt == task.attempt)
                .where(NodeTaskRecord.workflow_process_id == task.workflow_process_id)
                .where(NodeTaskRecord.process_generation == task.process_generation)
            )
            owner_check = (
                select(WorkflowRunRecord.workflow_run_id)
                .where(
                    WorkflowRunRecord.workflow_run_id
                    == NodeRunRecord.workflow_run_id
                )
                .where(WorkflowRunRecord.owner_process_id == task.workflow_process_id)
                .where(WorkflowRunRecord.process_generation == task.process_generation)
            )
            statement = (
                update(NodeRunRecord)
                .where(NodeRunRecord.node_run_id == task.node_run_id)
                .where(NodeRunRecord.status.in_([
                    NodeRunStatus.RUNNING.value,
                    NodeRunStatus.LONG_RUNNING.value,
                    NodeRunStatus.CANCEL_REQUESTED.value,
                ]))
                .where(NodeRunRecord.executor_id == executor_id)
                .where(NodeRunRecord.attempt == task.attempt)
                .where(task_check.exists())
                .where(owner_check.exists())
                .values(**values)
            )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(NodeRunRecord, task.node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def record_node_task_result_once(self, result: NodeTaskResultModel) -> bool:
        try:
            with self._session_factory.begin() as session:
                session.add(_node_task_result_to_record(result))
            return True
        except IntegrityError:
            return False

    def record_node_task_result_and_update_node_run_status(
        self,
        result: NodeTaskResultModel,
        status: NodeRunStatus,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        executor_id: str | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[NodeRunStatus | str] | None = None,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> NodeRun | None:
        try:
            with self._session_factory.begin() as session:
                session.add(_node_task_result_to_record(result))
                session.flush()
                source_statuses = (
                    _node_run_status_values(allowed_source_statuses)
                    if allowed_source_statuses is not None
                    else list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))
                )
                values: dict[str, Any] = {
                    "status": status.value,
                    "state_version": NodeRunRecord.state_version + 1,
                    "error_json": _json_dumps(error) if error is not None else None,
                }
                if progress is not None:
                    values["progress"] = progress
                if current_stage is not None:
                    values["current_stage"] = current_stage
                if finished_at is not None:
                    values["finished_at"] = _datetime_to_text(finished_at)
                if executor_id is not None:
                    values["executor_id"] = executor_id

                statement = (
                    update(NodeRunRecord)
                    .where(NodeRunRecord.node_run_id == result.node_run_id)
                    .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
                    .values(**values)
                )
                if expected_state_version is not None:
                    statement = statement.where(
                        NodeRunRecord.state_version == expected_state_version
                    )
                statement = statement.where(NodeRunRecord.status.in_(source_statuses))
                if owner_process_id is not None or process_generation is not None:
                    owner_check = select(WorkflowRunRecord.workflow_run_id).where(
                        WorkflowRunRecord.workflow_run_id
                        == NodeRunRecord.workflow_run_id
                    )
                    if owner_process_id is not None:
                        owner_check = owner_check.where(
                            WorkflowRunRecord.owner_process_id == owner_process_id
                        )
                    if process_generation is not None:
                        owner_check = owner_check.where(
                            WorkflowRunRecord.process_generation
                            == process_generation
                        )
                    statement = statement.where(owner_check.exists())
                update_result = cast(CursorResult[Any], session.execute(statement))
                if update_result.rowcount != 1:
                    raise _AtomicNodeTaskResultUpdateRejected
                record = session.get(NodeRunRecord, result.node_run_id)
                if record is None:
                    raise _AtomicNodeTaskResultUpdateRejected
                return _node_run_from_record(record)
        except (IntegrityError, _AtomicNodeTaskResultUpdateRejected):
            return None

    def get_node_task_result(
        self,
        *,
        task_id: str,
        result_id: str,
    ) -> NodeTaskResultModel | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeTaskResultRecord)
                .where(NodeTaskResultRecord.task_id == task_id)
                .where(NodeTaskResultRecord.result_id == result_id)
            )
            if record is None:
                return None
            return _node_task_result_from_record(record)

    def get_latest_succeeded_node_task_result_for_node_run(
        self,
        node_run_id: str,
    ) -> NodeTaskResultModel | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeTaskResultRecord)
                .where(NodeTaskResultRecord.node_run_id == node_run_id)
                .where(NodeTaskResultRecord.status == NodeResultStatus.SUCCEEDED.value)
                .order_by(
                    NodeTaskResultRecord.finished_at.desc(),
                    NodeTaskResultRecord.result_id.desc(),
                )
            )
            if record is None:
                return None
            return _node_task_result_from_record(record)

    def list_node_runs(self, workflow_run_id: str) -> list[NodeRun]:
        with self._session_factory() as session:
            records = session.scalars(
                select(NodeRunRecord)
                .where(NodeRunRecord.workflow_run_id == workflow_run_id)
                .order_by(NodeRunRecord.node_instance_id)
            ).all()
            return [_node_run_from_record(record) for record in records]

    def update_node_run_status(
        self,
        node_run_id: str,
        status: NodeRunStatus,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        executor_id: str | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[NodeRunStatus | str] | None = None,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> NodeRun | None:
        with self._session_factory.begin() as session:
            source_statuses = (
                _node_run_status_values(allowed_source_statuses)
                if allowed_source_statuses is not None
                else list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))
            )
            values: dict[str, Any] = {
                "status": status.value,
                "state_version": NodeRunRecord.state_version + 1,
                "error_json": _json_dumps(error) if error is not None else None,
            }
            if progress is not None:
                values["progress"] = progress
            if current_stage is not None:
                values["current_stage"] = current_stage
            if started_at is not None:
                values["started_at"] = _datetime_to_text(started_at)
            if finished_at is not None:
                values["finished_at"] = _datetime_to_text(finished_at)
            if executor_id is not None:
                values["executor_id"] = executor_id

            statement = (
                update(NodeRunRecord)
                .where(NodeRunRecord.node_run_id == node_run_id)
                .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
                .values(**values)
            )
            if expected_state_version is not None:
                statement = statement.where(
                    NodeRunRecord.state_version == expected_state_version
                )
            statement = statement.where(NodeRunRecord.status.in_(source_statuses))
            if owner_process_id is not None or process_generation is not None:
                owner_check = select(WorkflowRunRecord.workflow_run_id).where(
                    WorkflowRunRecord.workflow_run_id
                    == NodeRunRecord.workflow_run_id
                )
                if owner_process_id is not None:
                    owner_check = owner_check.where(
                        WorkflowRunRecord.owner_process_id == owner_process_id
                    )
                if process_generation is not None:
                    owner_check = owner_check.where(
                        WorkflowRunRecord.process_generation == process_generation
                    )
                statement = statement.where(owner_check.exists())
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def register_table_ref(self, table_ref: TableRefModel) -> None:
        with self._session_factory.begin() as session:
            session.add(_data_ref_from_model(table_ref))

    def get_table_ref(self, table_ref_id: str) -> TableRefModel | None:
        with self._session_factory() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None:
                return None
            return _table_ref_from_record(record)

    def list_table_refs_by_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DataRefRecord)
                .where(DataRefRecord.workflow_run_id == workflow_run_id)
                .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
            ).all()
            return [_table_ref_from_record(record) for record in records]

    def list_table_refs_by_node_run(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DataRefRecord)
                .where(DataRefRecord.workflow_run_id == workflow_run_id)
                .where(DataRefRecord.node_run_id == node_run_id)
                .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
            ).all()
            return [_table_ref_from_record(record) for record in records]

    def mark_staging_table_ref_released(
        self,
        table_ref_id: str,
    ) -> TableRefModel | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if (
                record is None
                or record.lifecycle_status != LifecycleStatus.STAGING.value
            ):
                return None
            record.lifecycle_status = LifecycleStatus.RELEASED.value
            record.released_at = _datetime_to_text(now)
            return _table_ref_from_record(record)

    def create_shared_publication(
        self,
        *,
        share_name: str,
        producer_workflow_id: str,
        producer_run_id: str,
        members: Mapping[str, str],
        publication_id: str | None = None,
        input_snapshot_id: str | None = None,
        retention_policy: dict[str, Any] | None = None,
    ) -> SharedPublication:
        if not members:
            raise ValueError("Shared publication requires at least one member")

        now = utc_now()
        publication_id = publication_id or new_id()
        member_records: list[SharedPublicationMemberRecord] = []
        with self._session_factory.begin() as session:
            producer_run = session.get(WorkflowRunRecord, producer_run_id)
            if producer_run is None:
                raise ValueError(f"Producer run not found: {producer_run_id}")
            if producer_run.workflow_id != producer_workflow_id:
                raise ValueError(
                    "Producer run does not belong to workflow: "
                    f"{producer_run_id}"
                )
            table_ref_records: dict[str, DataRefRecord] = {}
            for export_name, table_ref_id in members.items():
                table_ref_record = session.get(DataRefRecord, table_ref_id)
                if table_ref_record is None:
                    raise ValueError(f"TableRef not found: {table_ref_id}")
                if table_ref_record.workflow_run_id != producer_run_id:
                    raise ValueError(
                        "Shared publication member does not belong to "
                        f"producer run: {table_ref_id}"
                    )
                if table_ref_record.lifecycle_status != LifecycleStatus.PUBLISHED.value:
                    raise ValueError(
                        "Shared publication member must be PUBLISHED: "
                        f"{table_ref_id}"
                    )
                if (
                    table_ref_record.mutability
                    != TableMutability.PUBLISHED_IMMUTABLE.value
                ):
                    raise ValueError(
                        "Shared publication member must be PUBLISHED_IMMUTABLE: "
                        f"{table_ref_id}"
                    )
                table_ref_records[export_name] = table_ref_record

            max_version = cast(
                int | None,
                session.scalar(
                    select(func.max(SharedPublicationRecord.publication_version))
                    .where(SharedPublicationRecord.share_name == share_name)
                ),
            )
            publication_version = 1 if max_version is None else max_version + 1
            publication_record = SharedPublicationRecord(
                publication_id=publication_id,
                share_name=share_name,
                publication_version=publication_version,
                producer_workflow_id=producer_workflow_id,
                producer_run_id=producer_run_id,
                status="PUBLISHED",
                input_snapshot_id=input_snapshot_id,
                retention_policy_json=_json_dumps(retention_policy or {}),
                created_at=_datetime_to_text(now),
            )
            session.add(publication_record)
            session.flush()
            for export_name, table_ref_record in table_ref_records.items():
                member_record = SharedPublicationMemberRecord(
                    publication_id=publication_id,
                    export_name=export_name,
                    table_ref_id=table_ref_record.table_ref_id,
                    exact_table_version=table_ref_record.version,
                )
                session.add(member_record)
                member_records.append(member_record)
            session.flush()
            return _shared_publication_from_records(
                publication_record,
                sorted(member_records, key=lambda record: record.export_name),
            )

    def get_shared_publication(
        self,
        publication_id: str,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.get(SharedPublicationRecord, publication_id)
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(session, publication_id),
            )

    def get_shared_publication_version(
        self,
        *,
        share_name: str,
        publication_version: int,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(SharedPublicationRecord)
                .where(SharedPublicationRecord.share_name == share_name)
                .where(
                    SharedPublicationRecord.publication_version
                    == publication_version
                )
            )
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(
                    session,
                    record.publication_id,
                ),
            )

    def get_latest_shared_publication(
        self,
        share_name: str,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(SharedPublicationRecord)
                .where(SharedPublicationRecord.share_name == share_name)
                .order_by(SharedPublicationRecord.publication_version.desc())
                .limit(1)
            )
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(
                    session,
                    record.publication_id,
                ),
            )

    def create_input_snapshot(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        input_snapshot_id: str | None = None,
    ) -> InputSnapshot:
        input_snapshot_id = input_snapshot_id or new_id()
        inputs_tuple = tuple(inputs)
        now = utc_now()
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            for item in inputs_tuple:
                publication = session.get(
                    SharedPublicationRecord,
                    item.publication_id,
                )
                if publication is None:
                    raise ValueError(
                        "Input snapshot publication not found: "
                        f"{item.publication_id}"
                    )
                if publication.publication_version != item.publication_version:
                    raise ValueError(
                        "Input snapshot publication version mismatch: "
                        f"{item.publication_id}"
                    )
            snapshot_json = _json_dumps(
                {
                    "inputs": [
                        _input_snapshot_entry_to_json(item)
                        for item in inputs_tuple
                    ]
                }
            )
            record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=snapshot_json,
                created_at=_datetime_to_text(now),
            )
            session.add(record)
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return _input_snapshot_from_record(record)

    def get_input_snapshot(
        self,
        input_snapshot_id: str,
    ) -> InputSnapshot | None:
        with self._session_factory() as session:
            record = session.get(InputSnapshotRecord, input_snapshot_id)
            if record is None:
                return None
            return _input_snapshot_from_record(record)

    def create_read_lease(
        self,
        *,
        publication_id: str,
        publication_version: int,
        consumer_workflow_run_id: str,
        selected_members: Iterable[str],
        expires_at: datetime,
        lease_id: str | None = None,
    ) -> ReadLease:
        lease_id = lease_id or new_id()
        selected_members_tuple = tuple(selected_members)
        now = utc_now()
        with self._session_factory.begin() as session:
            consumer_run = session.get(WorkflowRunRecord, consumer_workflow_run_id)
            if consumer_run is None:
                raise ValueError(
                    f"Consumer workflow run not found: {consumer_workflow_run_id}"
                )
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=consumer_workflow_run_id,
                selected_members_json=json.dumps(
                    list(selected_members_tuple),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add(record)
            session.flush()
            return _read_lease_from_record(record)

    def get_read_lease(self, lease_id: str) -> ReadLease | None:
        with self._session_factory() as session:
            record = session.get(ReadLeaseRecord, lease_id)
            if record is None:
                return None
            return _read_lease_from_record(record)

    def list_read_leases_by_workflow_run(
        self,
        workflow_run_id: str,
        *,
        active_only: bool = False,
    ) -> list[ReadLease]:
        statement = (
            select(ReadLeaseRecord)
            .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
            .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
        )
        if active_only:
            statement = statement.where(ReadLeaseRecord.released_at.is_(None))
            statement = statement.where(
                ReadLeaseRecord.expires_at > _datetime_to_text(utc_now())
            )
        with self._session_factory() as session:
            return [
                _read_lease_from_record(record)
                for record in session.scalars(statement)
            ]

    def release_read_lease(self, lease_id: str) -> ReadLease | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(ReadLeaseRecord, lease_id)
            if record is None:
                return None
            if record.released_at is None:
                record.released_at = _datetime_to_text(now)
            return _read_lease_from_record(record)

    def append_runtime_event(self, event: EventModel) -> int:
        with self._session_factory.begin() as session:
            record = RuntimeEventRecord(
                event_id=event.event_id,
                event_version=event.event_version,
                event_type=event.event_type.value,
                timestamp=_datetime_to_text(event.timestamp),
                workflow_run_id=event.workflow_run_id,
                node_run_id=event.node_run_id,
                payload_json=_json_dumps(event.payload),
            )
            session.add(record)
            session.flush()
            return record.sequence_number

    def list_runtime_events(
        self,
        *,
        after_sequence_number: int | None = None,
        limit: int = 100,
    ) -> list[RuntimeEventLog]:
        limit = max(1, min(limit, 1000))
        statement = select(RuntimeEventRecord).order_by(
            RuntimeEventRecord.sequence_number
        )
        if after_sequence_number is not None:
            statement = statement.where(
                RuntimeEventRecord.sequence_number > after_sequence_number
            )
        with self._session_factory() as session:
            return [
                _runtime_event_from_record(record)
                for record in session.scalars(statement.limit(limit))
            ]

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_sqlite_engine(database_url)


def _workflow_definition_from_records(
    workflow: WorkflowRecord,
    revision: WorkflowRevisionRecord,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=workflow.workflow_id,
        name=workflow.name,
        revision_id=revision.revision_id,
        version=revision.version,
        definition_hash=revision.definition_hash,
        definition=json.loads(revision.definition_json),
        status=workflow.status,
        created_at=_datetime_from_text(workflow.created_at),
        updated_at=_datetime_from_text(workflow.updated_at),
    )


def _workflow_revision_from_record(record: WorkflowRevisionRecord) -> WorkflowRevision:
    return WorkflowRevision(
        revision_id=record.revision_id,
        workflow_id=record.workflow_id,
        version=record.version,
        definition_hash=record.definition_hash,
        definition=json.loads(record.definition_json),
        created_at=_datetime_from_text(record.created_at),
        created_by=record.created_by,
    )


def _workflow_run_from_record(record: WorkflowRunRecord) -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=record.workflow_run_id,
        workflow_id=record.workflow_id,
        revision_id=record.revision_id,
        workflow_version=record.workflow_version,
        definition_hash=record.definition_hash,
        status=record.status,
        state_version=record.state_version,
        owner_process_id=record.owner_process_id,
        process_generation=record.process_generation,
        fencing_token=record.fencing_token,
        input_snapshot_id=record.input_snapshot_id,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        completion_reason=record.completion_reason,
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _workflow_process_from_record(record: WorkflowProcessRecord) -> WorkflowProcess:
    return WorkflowProcess(
        process_id=record.process_id,
        workflow_run_id=record.workflow_run_id,
        os_pid=record.os_pid,
        process_generation=record.process_generation,
        fencing_token=record.fencing_token,
        status=record.status,
        started_at=_datetime_from_text(record.started_at),
        last_heartbeat_at=_optional_datetime_from_text(record.last_heartbeat_at),
        cancel_requested_at=_optional_datetime_from_text(record.cancel_requested_at),
        exited_at=_optional_datetime_from_text(record.exited_at),
        exit_code=record.exit_code,
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _node_run_from_record(record: NodeRunRecord) -> NodeRun:
    return NodeRun(
        node_run_id=record.node_run_id,
        workflow_run_id=record.workflow_run_id,
        node_instance_id=record.node_instance_id,
        node_type=record.node_type,
        status=record.status,
        state_version=record.state_version,
        executor_id=record.executor_id,
        progress=record.progress,
        current_stage=record.current_stage,
        attempt=record.attempt,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        last_heartbeat=_optional_datetime_from_text(record.last_heartbeat),
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _node_task_to_record(task: NodeTaskModel) -> NodeTaskRecord:
    return NodeTaskRecord(
        task_id=task.task_id,
        workflow_run_id=task.workflow_run_id,
        workflow_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        node_type=task.node_type,
        node_version=task.node_version,
        attempt=task.attempt,
        input_refs_json=json.dumps(
            task.input_refs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        config_json=_json_dumps(task.config),
        permission_handle_id=task.permission_handle_id,
        timeout_seconds=task.timeout_seconds,
        created_at=_datetime_to_text(utc_now()),
    )


def _node_task_from_record(record: NodeTaskRecord) -> NodeTaskModel:
    return NodeTaskModel(
        task_id=record.task_id,
        workflow_run_id=record.workflow_run_id,
        workflow_process_id=record.workflow_process_id,
        process_generation=record.process_generation,
        node_run_id=record.node_run_id,
        node_instance_id=record.node_instance_id,
        node_type=record.node_type,
        node_version=record.node_version,
        attempt=record.attempt,
        input_refs=list(json.loads(record.input_refs_json)),
        config=json.loads(record.config_json),
        permission_handle_id=record.permission_handle_id,
        timeout_seconds=record.timeout_seconds,
    )


def _node_task_result_to_record(
    result: NodeTaskResultModel,
) -> NodeTaskResultRecord:
    return NodeTaskResultRecord(
        result_id=result.result_id,
        task_id=result.task_id,
        node_run_id=result.node_run_id,
        attempt=result.attempt,
        executor_id=result.executor_id,
        process_generation=result.process_generation,
        status=result.status.value,
        output_refs_json=json.dumps(
            result.output_refs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        error_json=_json_dumps(result.error) if result.error is not None else None,
        started_at=_datetime_to_text(result.started_at),
        finished_at=_datetime_to_text(result.finished_at),
    )


def _node_task_result_from_record(
    record: NodeTaskResultRecord,
) -> NodeTaskResultModel:
    return NodeTaskResultModel(
        result_id=record.result_id,
        task_id=record.task_id,
        node_run_id=record.node_run_id,
        attempt=record.attempt,
        executor_id=record.executor_id,
        process_generation=record.process_generation,
        status=NodeResultStatus(record.status),
        output_refs=list(json.loads(record.output_refs_json)),
        error=json.loads(record.error_json) if record.error_json else None,
        started_at=_datetime_from_text(record.started_at),
        finished_at=_datetime_from_text(record.finished_at),
    )


def _runtime_event_from_record(record: RuntimeEventRecord) -> RuntimeEventLog:
    return RuntimeEventLog(
        event_id=record.event_id,
        sequence_number=record.sequence_number,
        event_version=record.event_version,
        event_type=record.event_type,
        timestamp=_datetime_from_text(record.timestamp),
        workflow_run_id=record.workflow_run_id,
        node_run_id=record.node_run_id,
        payload=json.loads(record.payload_json),
    )


def _get_shared_publication_member_records(
    session: Session,
    publication_id: str,
) -> list[SharedPublicationMemberRecord]:
    return list(
        session.scalars(
            select(SharedPublicationMemberRecord)
            .where(SharedPublicationMemberRecord.publication_id == publication_id)
            .order_by(SharedPublicationMemberRecord.export_name)
        ).all()
    )


def _shared_publication_from_records(
    record: SharedPublicationRecord,
    members: Iterable[SharedPublicationMemberRecord],
) -> SharedPublication:
    return SharedPublication(
        publication_id=record.publication_id,
        share_name=record.share_name,
        publication_version=record.publication_version,
        producer_workflow_id=record.producer_workflow_id,
        producer_run_id=record.producer_run_id,
        status=record.status,
        input_snapshot_id=record.input_snapshot_id,
        retention_policy=json.loads(record.retention_policy_json),
        created_at=_datetime_from_text(record.created_at),
        members=tuple(
            _shared_publication_member_from_record(member) for member in members
        ),
    )


def _shared_publication_member_from_record(
    record: SharedPublicationMemberRecord,
) -> SharedPublicationMember:
    return SharedPublicationMember(
        publication_id=record.publication_id,
        export_name=record.export_name,
        table_ref_id=record.table_ref_id,
        exact_table_version=record.exact_table_version,
    )


def _input_snapshot_from_record(record: InputSnapshotRecord) -> InputSnapshot:
    snapshot = json.loads(record.snapshot_json)
    return InputSnapshot(
        input_snapshot_id=record.input_snapshot_id,
        workflow_run_id=record.workflow_run_id,
        inputs=tuple(
            _input_snapshot_entry_from_json(item)
            for item in snapshot.get("inputs", [])
        ),
        created_at=_datetime_from_text(record.created_at),
    )


def _input_snapshot_entry_to_json(
    entry: InputSnapshotEntry,
) -> dict[str, Any]:
    return {
        "source_name": entry.source_name,
        "publication_id": entry.publication_id,
        "publication_version": entry.publication_version,
        "selected_members": list(entry.selected_members),
    }


def _input_snapshot_entry_from_json(
    value: Mapping[str, Any],
) -> InputSnapshotEntry:
    selected_members = value.get("selected_members", [])
    return InputSnapshotEntry(
        source_name=str(value["source_name"]),
        publication_id=str(value["publication_id"]),
        publication_version=int(value["publication_version"]),
        selected_members=tuple(str(item) for item in selected_members),
    )


def _read_lease_from_record(record: ReadLeaseRecord) -> ReadLease:
    return ReadLease(
        lease_id=record.lease_id,
        publication_id=record.publication_id,
        publication_version=record.publication_version,
        selected_members=tuple(
            str(item) for item in json.loads(record.selected_members_json)
        ),
        consumer_workflow_run_id=record.consumer_workflow_run_id,
        acquired_at=_datetime_from_text(record.acquired_at),
        expires_at=_datetime_from_text(record.expires_at),
        released_at=_optional_datetime_from_text(record.released_at),
    )


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _definition_hash(definition_json: str) -> str:
    return sha256(definition_json.encode("utf-8")).hexdigest()


def _data_ref_from_model(table_ref: TableRefModel) -> DataRefRecord:
    return DataRefRecord(
        table_ref_id=table_ref.table_ref_id,
        workflow_run_id=table_ref.created_by_workflow_run_id,
        node_run_id=table_ref.created_by_node_run_id,
        role=table_ref.role.value,
        storage_kind=table_ref.storage_kind.value,
        scope=table_ref.scope.value,
        mutability=table_ref.mutability.value,
        provider_id=table_ref.provider_id,
        resource_profile_id=table_ref.resource_profile_id,
        mount_id=table_ref.mount_id,
        logical_table_id=table_ref.logical_table_id,
        opaque_handle_json=_json_dumps(table_ref.opaque_handle),
        schema_json=json.dumps(
            [field.model_dump(mode="json") for field in table_ref.schema],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        schema_fingerprint=table_ref.schema_fingerprint,
        version=table_ref.version,
        capabilities_json=json.dumps(sorted(table_ref.capabilities)),
        lifecycle_status=table_ref.lifecycle_status.value,
        created_at=_datetime_to_text(table_ref.created_at),
        published_at=None,
        released_at=None,
    )


def _table_ref_from_record(record: DataRefRecord) -> TableRefModel:
    return TableRefModel(
        table_ref_id=record.table_ref_id,
        role=TableRole(record.role),
        storage_kind=TableStorageKind(record.storage_kind),
        scope=TableScope(record.scope),
        mutability=TableMutability(record.mutability),
        provider_id=record.provider_id,
        resource_profile_id=record.resource_profile_id,
        mount_id=record.mount_id,
        logical_table_id=record.logical_table_id,
        opaque_handle=json.loads(record.opaque_handle_json),
        schema=[
            FieldSchemaModel.model_validate(item)
            for item in json.loads(record.schema_json)
        ],
        schema_fingerprint=record.schema_fingerprint,
        version=record.version,
        capabilities=set(json.loads(record.capabilities_json)),
        lifecycle_status=LifecycleStatus(record.lifecycle_status),
        created_by_workflow_run_id=record.workflow_run_id,
        created_by_node_run_id=record.node_run_id,
        created_at=_datetime_from_text(record.created_at),
    )


def _datetime_to_text(value: datetime) -> str:
    return value.isoformat()


def _optional_datetime_to_text(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _datetime_from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime_from_text(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _workflow_run_matches_owner(
    session,
    *,
    workflow_run_id: str,
    owner_process_id: str | None,
    process_generation: int | None,
) -> bool:
    statement = select(WorkflowRunRecord.workflow_run_id).where(
        WorkflowRunRecord.workflow_run_id == workflow_run_id
    )
    if owner_process_id is not None:
        statement = statement.where(
            WorkflowRunRecord.owner_process_id == owner_process_id
        )
    if process_generation is not None:
        statement = statement.where(
            WorkflowRunRecord.process_generation == process_generation
        )
    return session.scalar(statement) is not None


def _workflow_run_status_values(
    statuses: Iterable[WorkflowRunStatus | str],
) -> list[str]:
    return [
        status.value if isinstance(status, WorkflowRunStatus) else status
        for status in statuses
    ]


def _node_run_status_values(statuses: Iterable[NodeRunStatus | str]) -> list[str]:
    return [
        status.value if isinstance(status, NodeRunStatus) else status
        for status in statuses
    ]


def _optional_completion_reason_value(
    value: WorkflowRunCompletionReason | str | None,
) -> str | None:
    if isinstance(value, WorkflowRunCompletionReason):
        return value.value
    return value
