from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    InputSnapshotRecord,
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
    NodeRunRecord,
    ReadLeaseRecord,
    RuntimeEventRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    LoopIterationNodeRun,
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
    ReadLease,
    RuntimeEventLog,
    SharedPublication,
)
from flowweaver.engine.runtime_models import (
    NodeRun as NodeRun,
)
from flowweaver.engine.runtime_models import (
    WorkflowProcess as WorkflowProcess,
)
from flowweaver.engine.runtime_models import (
    WorkflowRun as WorkflowRun,
)
from flowweaver.engine.runtime_node_run_store import (
    RuntimeNodeRunStoreMixin,
)
from flowweaver.engine.runtime_record_mappers import (
    _data_ref_from_model,
    _datetime_to_text,
    _input_snapshot_from_record,
    _input_snapshot_json,
    _json_dumps,
    _loop_iteration_node_run_from_record,
    _loop_iteration_run_from_record,
    _loop_iteration_table_ref_from_record,
    _loop_run_from_record,
    _optional_datetime_to_text,
    _read_lease_from_record,
    _runtime_event_from_record,
    _selected_members_json,
    _shared_publication_from_records,
    _table_ref_from_record,
)
from flowweaver.engine.runtime_status_guards import (
    LOOP_ITERATION_STATUS_SOURCES as _LOOP_ITERATION_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    LOOP_RUN_STATUS_SOURCES as _LOOP_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_LOOP_ITERATION_STATUSES as _TERMINAL_LOOP_ITERATION_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_LOOP_RUN_STATUSES as _TERMINAL_LOOP_RUN_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUS_VALUES as TERMINAL_WORKFLOW_STATUS_VALUES,
)
from flowweaver.engine.runtime_status_guards import (
    loop_iteration_status_values as _loop_iteration_status_values,
)
from flowweaver.engine.runtime_status_guards import (
    loop_run_status_values as _loop_run_status_values,
)
from flowweaver.engine.runtime_workflow_definition_store import (
    RuntimeWorkflowDefinitionStoreMixin,
)
from flowweaver.engine.runtime_workflow_run_store import (
    RuntimeWorkflowRunStoreMixin,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    LoopIterationRunStatus,
    LoopIterationTableRefRole,
    LoopRunStatus,
    TableMutability,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.table_ref import TableRefModel


class RuntimeStore(
    RuntimeWorkflowDefinitionStoreMixin,
    RuntimeWorkflowRunStoreMixin,
    RuntimeNodeRunStoreMixin,
):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = create_sqlite_engine(database_url)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> RuntimeStore:
        return cls(sqlite_url(path))

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

    def mark_table_ref_released(
        self,
        table_ref_id: str,
    ) -> TableRefModel | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None or record.lifecycle_status in {
                LifecycleStatus.RELEASED.value,
                LifecycleStatus.RETIRED.value,
                LifecycleStatus.ORPHANED.value,
            }:
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
                    f"Producer run does not belong to workflow: {producer_run_id}"
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
                        f"Shared publication member must be PUBLISHED: {table_ref_id}"
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
                    select(func.max(SharedPublicationRecord.publication_version)).where(
                        SharedPublicationRecord.share_name == share_name
                    )
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
                    SharedPublicationRecord.publication_version == publication_version
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

    def list_shared_publications(
        self,
        *,
        share_name: str | None = None,
        limit: int = 100,
    ) -> list[SharedPublication]:
        limit = max(1, min(limit, 1000))
        statement = select(SharedPublicationRecord).order_by(
            SharedPublicationRecord.share_name,
            SharedPublicationRecord.publication_version.desc(),
            SharedPublicationRecord.created_at.desc(),
        )
        if share_name is not None:
            statement = statement.where(
                SharedPublicationRecord.share_name == share_name
            )
        statement = statement.limit(limit)
        with self._session_factory() as session:
            records = session.scalars(statement).all()
            return [
                _shared_publication_from_records(
                    record,
                    _get_shared_publication_member_records(
                        session,
                        record.publication_id,
                    ),
                )
                for record in records
            ]

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
            _validate_input_snapshot_publications(session, inputs_tuple)
            record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
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
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add(record)
            session.flush()
            return _read_lease_from_record(record)

    def create_input_snapshot_and_read_lease(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        publication_id: str,
        publication_version: int,
        selected_members: Iterable[str],
        expires_at: datetime,
    ) -> tuple[InputSnapshot, ReadLease]:
        input_snapshot_id = new_id()
        lease_id = new_id()
        inputs_tuple = tuple(inputs)
        selected_members_tuple = tuple(selected_members)
        if len(inputs_tuple) != 1:
            raise ValueError(
                "Atomic input snapshot/read lease requires exactly one input"
            )
        snapshot_input = inputs_tuple[0]
        if snapshot_input.publication_id != publication_id:
            raise ValueError("Input snapshot and read lease publication mismatch")
        if snapshot_input.publication_version != publication_version:
            raise ValueError(
                "Input snapshot and read lease publication version mismatch"
            )
        if snapshot_input.selected_members != selected_members_tuple:
            raise ValueError("Input snapshot and read lease selected members mismatch")
        now = utc_now()
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            snapshot_record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
                created_at=_datetime_to_text(now),
            )
            lease_record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=workflow_run_id,
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add_all([snapshot_record, lease_record])
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return (
                _input_snapshot_from_record(snapshot_record),
                _read_lease_from_record(lease_record),
            )

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
                _read_lease_from_record(record) for record in session.scalars(statement)
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

    def release_unreleased_read_leases_for_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[ReadLease]:
        now = utc_now()
        with self._session_factory.begin() as session:
            records = session.scalars(
                select(ReadLeaseRecord)
                .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
                .where(ReadLeaseRecord.released_at.is_(None))
                .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
            ).all()
            for record in records:
                record.released_at = _datetime_to_text(now)
            session.flush()
            return [_read_lease_from_record(record) for record in records]

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
        workflow_run_id: str | None = None,
        node_run_id: str | None = None,
        event_type: str | None = None,
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
        if workflow_run_id is not None:
            statement = statement.where(
                RuntimeEventRecord.workflow_run_id == workflow_run_id
            )
        if node_run_id is not None:
            statement = statement.where(RuntimeEventRecord.node_run_id == node_run_id)
        if event_type is not None:
            statement = statement.where(RuntimeEventRecord.event_type == event_type)
        with self._session_factory() as session:
            return [
                _runtime_event_from_record(record)
                for record in session.scalars(statement.limit(limit))
            ]

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_sqlite_engine(database_url)


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


def _validate_input_snapshot_publications(
    session: Session,
    inputs: tuple[InputSnapshotEntry, ...],
) -> None:
    for item in inputs:
        publication = session.get(
            SharedPublicationRecord,
            item.publication_id,
        )
        if publication is None:
            raise ValueError(
                f"Input snapshot publication not found: {item.publication_id}"
            )
        if publication.publication_version != item.publication_version:
            raise ValueError(
                f"Input snapshot publication version mismatch: {item.publication_id}"
            )


def _validate_loop_table_ref(
    session: Session,
    *,
    loop: LoopRunRecord,
    table_ref_id: str,
) -> DataRefRecord:
    table_ref = session.get(DataRefRecord, table_ref_id)
    if table_ref is None:
        raise ValueError(f"Loop table ref not found: {table_ref_id}")
    if table_ref.workflow_run_id != loop.workflow_run_id:
        raise ValueError(
            f"Loop table ref does not belong to workflow run: {table_ref_id}"
        )
    return table_ref


def _validate_loop_node_run(
    session: Session,
    *,
    loop: LoopRunRecord,
    node_run_id: str,
) -> NodeRunRecord:
    node_run = session.get(NodeRunRecord, node_run_id)
    if node_run is None:
        raise ValueError(f"Loop node run not found: {node_run_id}")
    if node_run.workflow_run_id != loop.workflow_run_id:
        raise ValueError(
            f"Loop node run does not belong to workflow run: {node_run_id}"
        )
    return node_run


