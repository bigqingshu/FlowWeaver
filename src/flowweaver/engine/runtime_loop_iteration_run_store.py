from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import LoopIterationRunRecord, LoopRunRecord
from flowweaver.engine.runtime_loop_iteration_run_queries import (
    get_loop_iteration_run_for_index_from_session as _get_iteration_for_index,
)
from flowweaver.engine.runtime_loop_iteration_run_queries import (
    get_loop_iteration_run_from_session as _get_iteration,
)
from flowweaver.engine.runtime_loop_iteration_run_queries import (
    list_loop_iteration_runs_from_session as _list_iterations,
)
from flowweaver.engine.runtime_loop_iteration_status_update import (
    update_loop_iteration_run_status_in_session as _update_loop_iteration_run_status,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_run_from_record,
)
from flowweaver.engine.runtime_loop_run_store import RuntimeLoopRunStoreMixin
from flowweaver.engine.runtime_loop_validators import (
    validate_loop_table_ref as _validate_loop_table_ref,
)
from flowweaver.engine.runtime_models import LoopIterationRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
    _optional_datetime_to_text,
)
from flowweaver.protocols.enums import LoopIterationRunStatus


class RuntimeLoopIterationRunStoreMixin(RuntimeLoopRunStoreMixin):
    _session_factory: sessionmaker[Session]

    def create_loop_iteration_run(
        self,
        *,
        loop_run_id: str,
        iteration_index: int,
        loop_iteration_id: str | None = None,
        status: LoopIterationRunStatus = LoopIterationRunStatus.PENDING,
        input_table_ref_id: str | None = None,
        input_selector: Mapping[str, Any] | None = None,
        started_at: datetime | None = None,
    ) -> LoopIterationRun | None:
        if iteration_index < 0:
            raise ValueError("Loop iteration index cannot be negative")
        now = utc_now()
        record = LoopIterationRunRecord(
            loop_iteration_id=loop_iteration_id or new_id(),
            loop_run_id=loop_run_id,
            iteration_index=iteration_index,
            status=status.value,
            state_version=0,
            input_table_ref_id=input_table_ref_id,
            input_selector_json=(
                _json_dumps(dict(input_selector))
                if input_selector is not None
                else None
            ),
            output_table_ref_id=None,
            failed_node_run_id=None,
            started_at=_optional_datetime_to_text(started_at),
            finished_at=None,
            error_json=None,
            created_at=_datetime_to_text(now),
        )
        try:
            with self._session_factory.begin() as session:
                loop = session.get(LoopRunRecord, loop_run_id)
                if loop is None:
                    raise ValueError(f"Loop run not found: {loop_run_id}")
                if input_table_ref_id is not None:
                    _validate_loop_table_ref(
                        session,
                        loop=loop,
                        table_ref_id=input_table_ref_id,
                    )
                session.add(record)
            return _loop_iteration_run_from_record(record)
        except IntegrityError:
            return self.get_loop_iteration_run_for_index(
                loop_run_id=loop_run_id,
                iteration_index=iteration_index,
            )

    def get_loop_iteration_run(
        self,
        loop_iteration_id: str,
    ) -> LoopIterationRun | None:
        with self._session_factory() as session:
            return _get_iteration(session, loop_iteration_id)

    def get_loop_iteration_run_for_index(
        self,
        *,
        loop_run_id: str,
        iteration_index: int,
    ) -> LoopIterationRun | None:
        with self._session_factory() as session:
            return _get_iteration_for_index(
                session,
                loop_run_id=loop_run_id,
                iteration_index=iteration_index,
            )

    def list_loop_iteration_runs(
        self,
        loop_run_id: str,
        *,
        statuses: Iterable[LoopIterationRunStatus | str] | None = None,
    ) -> list[LoopIterationRun]:
        with self._session_factory() as session:
            return _list_iterations(session, loop_run_id, statuses=statuses)

    def update_loop_iteration_run_status(
        self,
        loop_iteration_id: str,
        status: LoopIterationRunStatus,
        *,
        output_table_ref_id: str | None = None,
        failed_node_run_id: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[LoopIterationRunStatus | str] | None = None,
    ) -> LoopIterationRun | None:
        with self._session_factory.begin() as session:
            return _update_loop_iteration_run_status(
                session,
                loop_iteration_id,
                status,
                output_table_ref_id=output_table_ref_id,
                failed_node_run_id=failed_node_run_id,
                started_at=started_at,
                finished_at=finished_at,
                error=error,
                expected_state_version=expected_state_version,
                allowed_source_statuses=allowed_source_statuses,
            )
