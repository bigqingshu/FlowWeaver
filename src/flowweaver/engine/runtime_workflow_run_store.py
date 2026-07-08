from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import Connection, CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    NodeRunRecord,
    WorkflowProcessRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import WorkflowProcess, WorkflowRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
    _optional_datetime_to_text,
    _workflow_process_from_record,
    _workflow_run_from_record,
)
from flowweaver.engine.runtime_status_guards import (
    ACTIVE_WORKFLOW_PROCESS_STATUSES as _ACTIVE_WORKFLOW_PROCESS_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    INTERRUPTED_NODE_STATUSES as _INTERRUPTED_NODE_STATUSES,
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
from flowweaver.protocols.enums import (
    NodeRunStatus,
    WorkflowProcessStatus,
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
                    WorkflowProcessRecord.status.in_(_ACTIVE_WORKFLOW_PROCESS_STATUSES)
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
                    select(WorkflowProcessRecord).where(
                        WorkflowProcessRecord.status.in_(
                            _ACTIVE_WORKFLOW_PROCESS_STATUSES
                        )
                    )
                )
            )
            now = utc_now()
            for record in records:
                if record.status == WorkflowProcessStatus.STARTING.value:
                    if (
                        starting_stale_before is None
                        or record.started_at > _datetime_to_text(starting_stale_before)
                    ):
                        continue
                elif (
                    record.last_heartbeat_at is None
                    or record.last_heartbeat_at > _datetime_to_text(stale_before)
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
                    WorkflowRunRecord.process_generation == process.process_generation
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
