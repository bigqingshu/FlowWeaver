from __future__ import annotations

from collections.abc import Iterator
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
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import WorkflowProcess, WorkflowRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
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
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
    _workflow_run_from_record,
)
from flowweaver.protocols.enums import (
    NodeRunStatus,
    WorkflowProcessStatus,
    WorkflowRunStatus,
)


class RuntimeWorkflowProcessStoreMixin:
    database_url: str
    engine: Engine
    _session_factory: sessionmaker[Session]

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
