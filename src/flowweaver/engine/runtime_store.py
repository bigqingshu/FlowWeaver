from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    NodeRunRecord,
    RuntimeEventRecord,
    WorkflowDefinitionRecord,
    WorkflowProcessRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeRunStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowProcessStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
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
    input_snapshot_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class WorkflowProcess:
    process_id: str
    workflow_run_id: str
    os_pid: int | None
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
        with self._session_factory.begin() as session:
            if revision_id is None:
                workflow = session.get(WorkflowRecord, workflow_id)
                if workflow is None or workflow.current_revision_id is None:
                    raise ValueError(f"Workflow not found: {workflow_id}")
                revision_id = workflow.current_revision_id
            revision = session.get(WorkflowRevisionRecord, revision_id)
            if revision is None:
                raise ValueError(f"Workflow revision not found: {revision_id}")
            record = WorkflowRunRecord(
                workflow_run_id=workflow_run_id or new_id(),
                workflow_id=workflow_id,
                revision_id=revision.revision_id,
                workflow_version=workflow_version or revision.version,
                definition_hash=revision.definition_hash,
                status=status.value,
                state_version=0,
                input_snapshot_id=None,
                started_at=_optional_datetime_to_text(started_at),
                finished_at=None,
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
        error: dict[str, Any] | None = None,
        expected_state_version: int | None = None,
    ) -> WorkflowRun | None:
        next_record: WorkflowRunRecord | None = None
        with self._session_factory.begin() as session:
            record = session.get(WorkflowRunRecord, workflow_run_id)
            if record is None:
                return None
            if (
                expected_state_version is not None
                and record.state_version != expected_state_version
            ):
                return None
            record.status = status.value
            record.state_version += 1
            record.finished_at = _optional_datetime_to_text(finished_at)
            record.error_json = _json_dumps(error) if error is not None else None
            next_record = record
        return _workflow_run_from_record(next_record)

    def create_workflow_process(
        self,
        *,
        workflow_run_id: str,
        process_id: str | None = None,
        os_pid: int | None = None,
    ) -> WorkflowProcess:
        now = utc_now()
        record = WorkflowProcessRecord(
            process_id=process_id or new_id(),
            workflow_run_id=workflow_run_id,
            os_pid=os_pid,
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
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(WorkflowProcessRecord, process_id)
            if record is None:
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
    ) -> list[WorkflowProcess]:
        lost: list[WorkflowProcess] = []
        with self._session_factory.begin() as session:
            records = list(
                session.scalars(
                    select(WorkflowProcessRecord)
                    .where(
                        WorkflowProcessRecord.status.in_(
                            [
                                WorkflowProcessStatus.STARTING.value,
                                WorkflowProcessStatus.RUNNING.value,
                                WorkflowProcessStatus.CANCEL_REQUESTED.value,
                            ]
                        )
                    )
                    .where(WorkflowProcessRecord.last_heartbeat_at.is_not(None))
                    .where(
                        WorkflowProcessRecord.last_heartbeat_at
                        < _datetime_to_text(stale_before)
                    )
                )
            )
            now = utc_now()
            for record in records:
                record.status = WorkflowProcessStatus.LOST.value
                record.exited_at = _datetime_to_text(now)
                lost.append(_workflow_process_from_record(record))
        return lost

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
            session.add(record)
        return _node_run_from_record(record)

    def get_node_run(self, node_run_id: str) -> NodeRun | None:
        with self._session_factory() as session:
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def update_node_run_status(
        self,
        node_run_id: str,
        status: NodeRunStatus,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        expected_state_version: int | None = None,
    ) -> NodeRun | None:
        next_record: NodeRunRecord | None = None
        with self._session_factory.begin() as session:
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            if (
                expected_state_version is not None
                and record.state_version != expected_state_version
            ):
                return None
            if (
                _is_terminal_node_status(record.status)
                and record.status != status.value
            ):
                return None
            record.status = status.value
            record.state_version += 1
            if progress is not None:
                record.progress = progress
            if current_stage is not None:
                record.current_stage = current_stage
            if finished_at is not None:
                record.finished_at = _datetime_to_text(finished_at)
            record.error_json = _json_dumps(error) if error is not None else None
            next_record = record
        return _node_run_from_record(next_record)

    def register_table_ref(self, table_ref: TableRefModel) -> None:
        with self._session_factory.begin() as session:
            session.add(_data_ref_from_model(table_ref))

    def get_table_ref(self, table_ref_id: str) -> TableRefModel | None:
        with self._session_factory() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None:
                return None
            return _table_ref_from_record(record)

    def append_runtime_event(self, event: EventModel) -> int:
        with self._session_factory.begin() as session:
            current = session.scalar(func.max(RuntimeEventRecord.sequence_number)) or 0
            sequence_number = int(current) + 1
            session.add(
                RuntimeEventRecord(
                    event_id=event.event_id,
                    sequence_number=sequence_number,
                    event_version=event.event_version,
                    event_type=event.event_type.value,
                    timestamp=_datetime_to_text(event.timestamp),
                    workflow_run_id=event.workflow_run_id,
                    node_run_id=event.node_run_id,
                    payload_json=_json_dumps(event.payload),
                )
            )
            return sequence_number

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
        input_snapshot_id=record.input_snapshot_id,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _workflow_process_from_record(record: WorkflowProcessRecord) -> WorkflowProcess:
    return WorkflowProcess(
        process_id=record.process_id,
        workflow_run_id=record.workflow_run_id,
        os_pid=record.os_pid,
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


def _is_terminal_node_status(status: str) -> bool:
    return status in {
        NodeRunStatus.TIMED_OUT.value,
        NodeRunStatus.SUCCEEDED.value,
        NodeRunStatus.FAILED.value,
        NodeRunStatus.CANCELLED.value,
        NodeRunStatus.SKIPPED.value,
    }
