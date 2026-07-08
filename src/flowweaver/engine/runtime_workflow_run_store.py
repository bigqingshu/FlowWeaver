from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.engine.db_models import (
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_record_mappers import (
    _json_dumps,
    _optional_datetime_to_text,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUSES as _TERMINAL_WORKFLOW_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    WORKFLOW_RUN_STATUS_SOURCES as _WORKFLOW_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    optional_completion_reason_value as _optional_completion_reason_value,
)
from flowweaver.engine.runtime_status_guards import (
    workflow_run_matches_owner as _workflow_run_matches_owner,
)
from flowweaver.engine.runtime_status_guards import (
    workflow_run_status_values as _workflow_run_status_values,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_run_from_record,
)
from flowweaver.protocols.enums import (
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)


class RuntimeWorkflowRunStoreMixin:
    database_url: str
    engine: Engine
    _session_factory: sessionmaker[Session]

    def create_workflow_run(
        self,
        *,
        workflow_id: str,
        workflow_version: int | None = None,
        revision_id: str | None = None,
        workflow_run_id: str | None = None,
        status: WorkflowRunStatus = WorkflowRunStatus.PENDING,
        started_at: datetime | None = None,
        run_mode: str = "full",
        trigger_source: str = "manual",
        target_node_instance_id: str | None = None,
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
                run_mode=run_mode,
                trigger_source=trigger_source,
                target_node_instance_id=target_node_instance_id,
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
        run_mode: str | None = None,
        trigger_source: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[WorkflowRun]:
        statement = select(WorkflowRunRecord).order_by(
            WorkflowRunRecord.started_at.desc(),
            WorkflowRunRecord.workflow_run_id,
        )
        if workflow_id is not None:
            statement = statement.where(WorkflowRunRecord.workflow_id == workflow_id)
        if statuses is not None:
            status_values = [
                status.value if isinstance(status, WorkflowRunStatus) else status
                for status in statuses
            ]
            statement = statement.where(WorkflowRunRecord.status.in_(status_values))
        if run_mode is not None:
            statement = statement.where(WorkflowRunRecord.run_mode == run_mode)
        if trigger_source is not None:
            statement = statement.where(
                WorkflowRunRecord.trigger_source == trigger_source
            )
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

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

