from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from workflow_platform.common.ids import new_id
from workflow_platform.common.time import utc_now
from workflow_platform.engine.db_models import (
    WorkflowDefinitionRecord,
    WorkflowRunRecord,
)
from workflow_platform.protocols.enums import WorkflowRunStatus


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: int
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkflowRun:
    workflow_run_id: str
    workflow_id: str
    workflow_version: int
    status: str
    input_snapshot_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None


def sqlite_url(path: str | Path) -> str:
    return f"sqlite:///{Path(path).as_posix()}"


class RuntimeStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, future=True)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> "RuntimeStore":
        return cls(sqlite_url(path))

    def create_workflow_definition(
        self,
        *,
        name: str,
        definition: dict[str, Any],
        workflow_id: str | None = None,
        version: int = 1,
    ) -> WorkflowDefinition:
        now = utc_now()
        record = WorkflowDefinitionRecord(
            workflow_id=workflow_id or new_id(),
            name=name,
            version=version,
            definition_json=_json_dumps(definition),
            created_at=_datetime_to_text(now),
            updated_at=_datetime_to_text(now),
        )
        with self._session_factory.begin() as session:
            session.add(record)
        return _workflow_definition_from_record(record)

    def get_workflow_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._session_factory() as session:
            record = session.get(WorkflowDefinitionRecord, workflow_id)
            if record is None:
                return None
            return _workflow_definition_from_record(record)

    def list_workflow_definitions(self) -> list[WorkflowDefinition]:
        with self._session_factory() as session:
            records = session.scalars(
                select(WorkflowDefinitionRecord).order_by(
                    WorkflowDefinitionRecord.created_at
                )
            ).all()
            return [_workflow_definition_from_record(record) for record in records]

    def update_workflow_definition(
        self,
        workflow_id: str,
        *,
        name: str | None = None,
        definition: dict[str, Any] | None = None,
    ) -> WorkflowDefinition | None:
        with self._session_factory.begin() as session:
            record = session.get(WorkflowDefinitionRecord, workflow_id)
            if record is None:
                return None
            if name is not None:
                record.name = name
            if definition is not None:
                record.definition_json = _json_dumps(definition)
                record.version += 1
            record.updated_at = _datetime_to_text(utc_now())
        return _workflow_definition_from_record(record)

    def delete_workflow_definition(self, workflow_id: str) -> bool:
        with self._session_factory.begin() as session:
            record = session.get(WorkflowDefinitionRecord, workflow_id)
            if record is None:
                return False
            session.delete(record)
        return True

    def create_workflow_run(
        self,
        *,
        workflow_id: str,
        workflow_version: int,
        workflow_run_id: str | None = None,
        status: WorkflowRunStatus = WorkflowRunStatus.PENDING,
        started_at: datetime | None = None,
    ) -> WorkflowRun:
        record = WorkflowRunRecord(
            workflow_run_id=workflow_run_id or new_id(),
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            status=status.value,
            input_snapshot_id=None,
            started_at=_optional_datetime_to_text(started_at),
            finished_at=None,
            error_json=None,
        )
        with self._session_factory.begin() as session:
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
            return [_workflow_run_from_record(record) for record in session.scalars(statement)]

    def update_workflow_run_status(
        self,
        workflow_run_id: str,
        status: WorkflowRunStatus,
        *,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
    ) -> WorkflowRun | None:
        with self._session_factory.begin() as session:
            record = session.get(WorkflowRunRecord, workflow_run_id)
            if record is None:
                return None
            record.status = status.value
            record.finished_at = _optional_datetime_to_text(finished_at)
            record.error_json = _json_dumps(error) if error is not None else None
        return _workflow_run_from_record(record)

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def _workflow_definition_from_record(
    record: WorkflowDefinitionRecord,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        definition=json.loads(record.definition_json),
        created_at=_datetime_from_text(record.created_at),
        updated_at=_datetime_from_text(record.updated_at),
    )


def _workflow_run_from_record(record: WorkflowRunRecord) -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=record.workflow_run_id,
        workflow_id=record.workflow_id,
        workflow_version=record.workflow_version,
        status=record.status,
        input_snapshot_id=record.input_snapshot_id,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _datetime_to_text(value: datetime) -> str:
    return value.isoformat()


def _optional_datetime_to_text(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _datetime_from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime_from_text(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None
