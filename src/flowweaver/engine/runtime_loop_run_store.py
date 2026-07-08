from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import LoopRunRecord, WorkflowRunRecord
from flowweaver.engine.runtime_models import LoopRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
    _loop_run_from_record,
    _optional_datetime_to_text,
)
from flowweaver.engine.runtime_status_guards import (
    LOOP_RUN_STATUS_SOURCES as _LOOP_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_LOOP_RUN_STATUSES as _TERMINAL_LOOP_RUN_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    loop_run_status_values as _loop_run_status_values,
)
from flowweaver.protocols.enums import LoopRunStatus


class RuntimeLoopRunStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_loop_run(
        self,
        *,
        workflow_run_id: str,
        loop_id: str,
        start_node_instance_id: str,
        judge_node_instance_id: str,
        max_iterations: int,
        loop_run_id: str | None = None,
        status: LoopRunStatus = LoopRunStatus.PENDING,
        started_at: datetime | None = None,
    ) -> LoopRun | None:
        if max_iterations < 1:
            raise ValueError("Loop run max_iterations must be at least 1")
        now = utc_now()
        record = LoopRunRecord(
            loop_run_id=loop_run_id or new_id(),
            workflow_run_id=workflow_run_id,
            loop_id=loop_id,
            start_node_instance_id=start_node_instance_id,
            judge_node_instance_id=judge_node_instance_id,
            status=status.value,
            state_version=0,
            current_iteration=0,
            max_iterations=max_iterations,
            exit_reason=None,
            started_at=_optional_datetime_to_text(started_at),
            finished_at=None,
            error_json=None,
            created_at=_datetime_to_text(now),
        )
        try:
            with self._session_factory.begin() as session:
                if session.get(WorkflowRunRecord, workflow_run_id) is None:
                    raise ValueError(f"Workflow run not found: {workflow_run_id}")
                session.add(record)
            return _loop_run_from_record(record)
        except IntegrityError:
            return self.get_loop_run_for_workflow_loop(
                workflow_run_id=workflow_run_id,
                loop_id=loop_id,
            )

    def get_loop_run(self, loop_run_id: str) -> LoopRun | None:
        with self._session_factory() as session:
            record = session.get(LoopRunRecord, loop_run_id)
            if record is None:
                return None
            return _loop_run_from_record(record)

    def get_loop_run_for_workflow_loop(
        self,
        *,
        workflow_run_id: str,
        loop_id: str,
    ) -> LoopRun | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(LoopRunRecord)
                .where(LoopRunRecord.workflow_run_id == workflow_run_id)
                .where(LoopRunRecord.loop_id == loop_id)
            )
            if record is None:
                return None
            return _loop_run_from_record(record)

    def list_loop_runs(
        self,
        workflow_run_id: str,
        *,
        statuses: Iterable[LoopRunStatus | str] | None = None,
    ) -> list[LoopRun]:
        statement = (
            select(LoopRunRecord)
            .where(LoopRunRecord.workflow_run_id == workflow_run_id)
            .order_by(LoopRunRecord.created_at, LoopRunRecord.loop_run_id)
        )
        if statuses is not None:
            statement = statement.where(
                LoopRunRecord.status.in_(_loop_run_status_values(statuses))
            )
        with self._session_factory() as session:
            return [
                _loop_run_from_record(record) for record in session.scalars(statement)
            ]

    def update_loop_run_status(
        self,
        loop_run_id: str,
        status: LoopRunStatus,
        *,
        current_iteration: int | None = None,
        exit_reason: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[LoopRunStatus | str] | None = None,
    ) -> LoopRun | None:
        if current_iteration is not None and current_iteration < 0:
            raise ValueError("Loop run current_iteration cannot be negative")
        with self._session_factory.begin() as session:
            source_statuses = (
                _loop_run_status_values(allowed_source_statuses)
                if allowed_source_statuses is not None
                else list(_LOOP_RUN_STATUS_SOURCES.get(status.value, ()))
            )
            values: dict[str, Any] = {
                "status": status.value,
                "state_version": LoopRunRecord.state_version + 1,
                "error_json": _json_dumps(error) if error is not None else None,
            }
            if current_iteration is not None:
                values["current_iteration"] = current_iteration
            if exit_reason is not None:
                values["exit_reason"] = exit_reason
            if started_at is not None:
                values["started_at"] = _datetime_to_text(started_at)
            if finished_at is not None:
                values["finished_at"] = _datetime_to_text(finished_at)

            statement = (
                update(LoopRunRecord)
                .where(LoopRunRecord.loop_run_id == loop_run_id)
                .where(LoopRunRecord.status.notin_(_TERMINAL_LOOP_RUN_STATUSES))
                .where(LoopRunRecord.status.in_(source_statuses))
                .values(**values)
            )
            if expected_state_version is not None:
                statement = statement.where(
                    LoopRunRecord.state_version == expected_state_version
                )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(LoopRunRecord, loop_run_id)
            if record is None:
                return None
            return _loop_run_from_record(record)
