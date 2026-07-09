from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine import runtime_workflow_process_abort as _process_abort
from flowweaver.engine import runtime_workflow_process_claim as _process_claim
from flowweaver.engine import runtime_workflow_process_lifecycle as _process_lifecycle
from flowweaver.engine import runtime_workflow_process_lost as _process_lost
from flowweaver.engine.db_models import WorkflowProcessRecord
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_models import WorkflowProcess, WorkflowRun
from flowweaver.engine.runtime_record_mappers import _datetime_to_text
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_process_from_record,
)
from flowweaver.protocols.enums import WorkflowProcessStatus


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
            return _process_claim.claim_workflow_process_in_session(
                session,
                workflow_run_id,
                process_id=process_id,
                fencing_token=fencing_token,
                now=now,
            )

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
            return _process_lifecycle.update_workflow_process_pid_in_session(
                session,
                process_id,
                os_pid,
            )

    def record_workflow_process_heartbeat(
        self,
        process_id: str,
        *,
        process_generation: int | None = None,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            return _process_lifecycle.record_workflow_process_heartbeat_in_session(
                session,
                process_id,
                process_generation=process_generation,
                now=now,
            )

    def request_workflow_process_cancel(
        self,
        workflow_run_id: str,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            return _process_lifecycle.request_workflow_process_cancel_in_session(
                session,
                workflow_run_id,
                now=now,
            )

    def mark_workflow_process_exited(
        self,
        process_id: str,
        *,
        exit_code: int,
        error: dict[str, Any] | None = None,
    ) -> WorkflowProcess | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            return _process_lifecycle.mark_workflow_process_exited_in_session(
                session,
                process_id,
                exit_code=exit_code,
                error=error,
                now=now,
            )

    def mark_lost_workflow_processes(
        self,
        *,
        stale_before: datetime,
        starting_stale_before: datetime | None = None,
    ) -> list[WorkflowProcess]:
        now = utc_now()
        with self._session_factory.begin() as session:
            return _process_lost.mark_lost_workflow_processes_in_session(
                session,
                stale_before=stale_before,
                starting_stale_before=starting_stale_before,
                now=now,
            )

    def abort_workflow_run_for_process(
        self,
        process_id: str,
        *,
        reason: str,
    ) -> WorkflowRun | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            return _process_abort.abort_workflow_run_for_process_in_session(
                session,
                process_id,
                reason=reason,
                now=now,
            )

    def _immediate_session(self) -> AbstractContextManager[Session]:
        return immediate_session(self.engine, database_url=self.database_url)
