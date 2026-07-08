from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
)
from flowweaver.engine.runtime_loop_run_store import RuntimeLoopRunStoreMixin
from flowweaver.engine.runtime_loop_validators import (
    validate_loop_node_run as _validate_loop_node_run,
)
from flowweaver.engine.runtime_loop_validators import (
    validate_loop_table_ref as _validate_loop_table_ref,
)
from flowweaver.engine.runtime_models import (
    LoopIterationNodeRun,
    LoopIterationRun,
    LoopIterationTableRef,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
    _loop_iteration_node_run_from_record,
    _loop_iteration_run_from_record,
    _loop_iteration_table_ref_from_record,
    _optional_datetime_to_text,
)
from flowweaver.engine.runtime_status_guards import (
    LOOP_ITERATION_STATUS_SOURCES as _LOOP_ITERATION_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_LOOP_ITERATION_STATUSES as _TERMINAL_LOOP_ITERATION_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    loop_iteration_status_values as _loop_iteration_status_values,
)
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopIterationTableRefRole,
)


class RuntimeLoopStoreMixin(RuntimeLoopRunStoreMixin):
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
            record = session.get(LoopIterationRunRecord, loop_iteration_id)
            if record is None:
                return None
            return _loop_iteration_run_from_record(record)

    def get_loop_iteration_run_for_index(
        self,
        *,
        loop_run_id: str,
        iteration_index: int,
    ) -> LoopIterationRun | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(LoopIterationRunRecord)
                .where(LoopIterationRunRecord.loop_run_id == loop_run_id)
                .where(LoopIterationRunRecord.iteration_index == iteration_index)
            )
            if record is None:
                return None
            return _loop_iteration_run_from_record(record)

    def list_loop_iteration_runs(
        self,
        loop_run_id: str,
        *,
        statuses: Iterable[LoopIterationRunStatus | str] | None = None,
    ) -> list[LoopIterationRun]:
        statement = (
            select(LoopIterationRunRecord)
            .where(LoopIterationRunRecord.loop_run_id == loop_run_id)
            .order_by(LoopIterationRunRecord.iteration_index)
        )
        if statuses is not None:
            statement = statement.where(
                LoopIterationRunRecord.status.in_(
                    _loop_iteration_status_values(statuses)
                )
            )
        with self._session_factory() as session:
            return [
                _loop_iteration_run_from_record(record)
                for record in session.scalars(statement)
            ]

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
            iteration = session.get(LoopIterationRunRecord, loop_iteration_id)
            if iteration is None:
                return None
            loop = session.get(LoopRunRecord, iteration.loop_run_id)
            if loop is None:
                return None
            if output_table_ref_id is not None:
                _validate_loop_table_ref(
                    session,
                    loop=loop,
                    table_ref_id=output_table_ref_id,
                )
            if failed_node_run_id is not None:
                _validate_loop_node_run(
                    session,
                    loop=loop,
                    node_run_id=failed_node_run_id,
                )

            source_statuses = (
                _loop_iteration_status_values(allowed_source_statuses)
                if allowed_source_statuses is not None
                else list(_LOOP_ITERATION_STATUS_SOURCES.get(status.value, ()))
            )
            values: dict[str, Any] = {
                "status": status.value,
                "state_version": LoopIterationRunRecord.state_version + 1,
                "error_json": _json_dumps(error) if error is not None else None,
            }
            if output_table_ref_id is not None:
                values["output_table_ref_id"] = output_table_ref_id
            if failed_node_run_id is not None:
                values["failed_node_run_id"] = failed_node_run_id
            if started_at is not None:
                values["started_at"] = _datetime_to_text(started_at)
            if finished_at is not None:
                values["finished_at"] = _datetime_to_text(finished_at)

            statement = (
                update(LoopIterationRunRecord)
                .where(LoopIterationRunRecord.loop_iteration_id == loop_iteration_id)
                .where(
                    LoopIterationRunRecord.status.notin_(
                        _TERMINAL_LOOP_ITERATION_STATUSES
                    )
                )
                .where(LoopIterationRunRecord.status.in_(source_statuses))
                .values(**values)
            )
            if expected_state_version is not None:
                statement = statement.where(
                    LoopIterationRunRecord.state_version == expected_state_version
                )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(LoopIterationRunRecord, loop_iteration_id)
            if record is None:
                return None
            return _loop_iteration_run_from_record(record)

    def add_loop_iteration_table_ref(
        self,
        *,
        loop_iteration_id: str,
        table_ref_id: str,
        role: LoopIterationTableRefRole | str,
    ) -> LoopIterationTableRef | None:
        role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
        now = utc_now()
        record = LoopIterationTableRefRecord(
            loop_iteration_id=loop_iteration_id,
            table_ref_id=table_ref_id,
            role=role_value,
            created_at=_datetime_to_text(now),
        )
        try:
            with self._session_factory.begin() as session:
                iteration = session.get(LoopIterationRunRecord, loop_iteration_id)
                if iteration is None:
                    raise ValueError(f"Loop iteration not found: {loop_iteration_id}")
                loop = session.get(LoopRunRecord, iteration.loop_run_id)
                if loop is None:
                    raise ValueError(f"Loop run not found: {iteration.loop_run_id}")
                _validate_loop_table_ref(
                    session,
                    loop=loop,
                    table_ref_id=table_ref_id,
                )
                session.add(record)
            return _loop_iteration_table_ref_from_record(record)
        except IntegrityError:
            return self.get_loop_iteration_table_ref(
                loop_iteration_id=loop_iteration_id,
                table_ref_id=table_ref_id,
                role=role_value,
            )

    def get_loop_iteration_table_ref(
        self,
        *,
        loop_iteration_id: str,
        table_ref_id: str,
        role: LoopIterationTableRefRole | str,
    ) -> LoopIterationTableRef | None:
        role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
        with self._session_factory() as session:
            record = session.get(
                LoopIterationTableRefRecord,
                {
                    "loop_iteration_id": loop_iteration_id,
                    "table_ref_id": table_ref_id,
                    "role": role_value,
                },
            )
            if record is None:
                return None
            return _loop_iteration_table_ref_from_record(record)

    def list_loop_iteration_table_refs(
        self,
        loop_iteration_id: str,
        *,
        role: LoopIterationTableRefRole | str | None = None,
    ) -> list[LoopIterationTableRef]:
        statement = (
            select(LoopIterationTableRefRecord)
            .where(LoopIterationTableRefRecord.loop_iteration_id == loop_iteration_id)
            .order_by(
                LoopIterationTableRefRecord.role,
                LoopIterationTableRefRecord.table_ref_id,
            )
        )
        if role is not None:
            role_value = (
                role.value if isinstance(role, LoopIterationTableRefRole) else role
            )
            statement = statement.where(LoopIterationTableRefRecord.role == role_value)
        with self._session_factory() as session:
            return [
                _loop_iteration_table_ref_from_record(record)
                for record in session.scalars(statement)
            ]

    def add_loop_iteration_node_run(
        self,
        *,
        loop_iteration_id: str,
        node_run_id: str,
        node_instance_id: str | None = None,
        role: str = "BODY",
    ) -> LoopIterationNodeRun | None:
        if not role:
            raise ValueError("Loop iteration node run role cannot be empty")
        now = utc_now()
        try:
            with self._session_factory.begin() as session:
                iteration = session.get(LoopIterationRunRecord, loop_iteration_id)
                if iteration is None:
                    raise ValueError(f"Loop iteration not found: {loop_iteration_id}")
                loop = session.get(LoopRunRecord, iteration.loop_run_id)
                if loop is None:
                    raise ValueError(f"Loop run not found: {iteration.loop_run_id}")
                node_run = _validate_loop_node_run(
                    session,
                    loop=loop,
                    node_run_id=node_run_id,
                )
                resolved_node_instance_id = (
                    node_instance_id
                    if node_instance_id is not None
                    else node_run.node_instance_id
                )
                if resolved_node_instance_id != node_run.node_instance_id:
                    raise ValueError(
                        "Loop node instance id does not match node run: "
                        f"{resolved_node_instance_id}"
                    )
                record = LoopIterationNodeRunRecord(
                    loop_iteration_id=loop_iteration_id,
                    node_run_id=node_run_id,
                    node_instance_id=resolved_node_instance_id,
                    role=role,
                    created_at=_datetime_to_text(now),
                )
                session.add(record)
            return _loop_iteration_node_run_from_record(record)
        except IntegrityError:
            return self.get_loop_iteration_node_run(
                loop_iteration_id=loop_iteration_id,
                node_run_id=node_run_id,
            )

    def get_loop_iteration_node_run(
        self,
        *,
        loop_iteration_id: str,
        node_run_id: str,
    ) -> LoopIterationNodeRun | None:
        with self._session_factory() as session:
            record = session.get(
                LoopIterationNodeRunRecord,
                {
                    "loop_iteration_id": loop_iteration_id,
                    "node_run_id": node_run_id,
                },
            )
            if record is None:
                return None
            return _loop_iteration_node_run_from_record(record)

    def list_loop_iteration_node_runs(
        self,
        loop_iteration_id: str,
        *,
        node_instance_id: str | None = None,
        role: str | None = None,
    ) -> list[LoopIterationNodeRun]:
        statement = (
            select(LoopIterationNodeRunRecord)
            .where(LoopIterationNodeRunRecord.loop_iteration_id == loop_iteration_id)
            .order_by(
                LoopIterationNodeRunRecord.node_instance_id,
                LoopIterationNodeRunRecord.node_run_id,
            )
        )
        if node_instance_id is not None:
            statement = statement.where(
                LoopIterationNodeRunRecord.node_instance_id == node_instance_id
            )
        if role is not None:
            statement = statement.where(LoopIterationNodeRunRecord.role == role)
        with self._session_factory() as session:
            return [
                _loop_iteration_node_run_from_record(record)
                for record in session.scalars(statement)
            ]

    def list_loop_iteration_node_runs_by_node_run(
        self,
        node_run_id: str,
    ) -> list[LoopIterationNodeRun]:
        statement = (
            select(LoopIterationNodeRunRecord)
            .where(LoopIterationNodeRunRecord.node_run_id == node_run_id)
            .order_by(
                LoopIterationNodeRunRecord.loop_iteration_id,
                LoopIterationNodeRunRecord.role,
            )
        )
        with self._session_factory() as session:
            return [
                _loop_iteration_node_run_from_record(record)
                for record in session.scalars(statement)
            ]


