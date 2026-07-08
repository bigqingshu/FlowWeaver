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
from flowweaver.engine.db_models import (
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_run_from_record,
    _node_task_from_record,
    _node_task_result_from_record,
    _node_task_result_to_record,
    _node_task_to_record,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_status_guards import (
    NODE_RUN_STATUS_SOURCES as _NODE_RUN_STATUS_SOURCES,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_NODE_STATUSES as _TERMINAL_NODE_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    node_run_status_values as _node_run_status_values,
)
from flowweaver.engine.runtime_status_guards import (
    workflow_run_matches_owner as _workflow_run_matches_owner,
)
from flowweaver.protocols.enums import NodeResultStatus, NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class _AtomicNodeTaskResultUpdateRejected(Exception):
    pass


class RuntimeNodeRunStoreMixin:
    _session_factory: sessionmaker[Session]

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
        owner_process_id: str | None = None,
        process_generation: int | None = None,
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
            if owner_process_id is not None or process_generation is not None:
                if not _workflow_run_matches_owner(
                    session,
                    workflow_run_id=workflow_run_id,
                    owner_process_id=owner_process_id,
                    process_generation=process_generation,
                ):
                    raise PermissionError("WORKFLOW_RUN_OWNER_MISMATCH")
            session.add(record)
        return _node_run_from_record(record)

    def get_node_run(self, node_run_id: str) -> NodeRun | None:
        with self._session_factory() as session:
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def get_node_run_for_instance(
        self,
        *,
        workflow_run_id: str,
        node_instance_id: str,
    ) -> NodeRun | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeRunRecord)
                .where(NodeRunRecord.workflow_run_id == workflow_run_id)
                .where(NodeRunRecord.node_instance_id == node_instance_id)
            )
            if record is None:
                return None
            return _node_run_from_record(record)

    def create_node_task(self, task: NodeTaskModel) -> NodeTaskModel:
        with self._session_factory.begin() as session:
            session.add(_node_task_to_record(task))
        return task

    def get_node_task(self, task_id: str) -> NodeTaskModel | None:
        with self._session_factory() as session:
            record = session.get(NodeTaskRecord, task_id)
            if record is None:
                return None
            return _node_task_from_record(record)

    def update_node_task_runtime_state(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
        heartbeat_at: datetime | None = None,
        progress: float | None = None,
        current_stage: str | None = None,
    ) -> NodeRun | None:
        values: dict[str, Any] = {
            "last_heartbeat": _datetime_to_text(heartbeat_at or utc_now()),
        }
        if progress is not None:
            values["progress"] = progress
        if current_stage is not None:
            values["current_stage"] = current_stage
        with self._session_factory.begin() as session:
            task_check = (
                select(NodeTaskRecord.task_id)
                .where(NodeTaskRecord.task_id == task.task_id)
                .where(NodeTaskRecord.node_run_id == task.node_run_id)
                .where(NodeTaskRecord.attempt == task.attempt)
                .where(NodeTaskRecord.workflow_process_id == task.workflow_process_id)
                .where(NodeTaskRecord.process_generation == task.process_generation)
            )
            owner_check = (
                select(WorkflowRunRecord.workflow_run_id)
                .where(
                    WorkflowRunRecord.workflow_run_id == NodeRunRecord.workflow_run_id
                )
                .where(WorkflowRunRecord.owner_process_id == task.workflow_process_id)
                .where(WorkflowRunRecord.process_generation == task.process_generation)
            )
            statement = (
                update(NodeRunRecord)
                .where(NodeRunRecord.node_run_id == task.node_run_id)
                .where(
                    NodeRunRecord.status.in_(
                        [
                            NodeRunStatus.RUNNING.value,
                            NodeRunStatus.LONG_RUNNING.value,
                            NodeRunStatus.CANCEL_REQUESTED.value,
                        ]
                    )
                )
                .where(NodeRunRecord.executor_id == executor_id)
                .where(NodeRunRecord.attempt == task.attempt)
                .where(task_check.exists())
                .where(owner_check.exists())
                .values(**values)
            )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(NodeRunRecord, task.node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)

    def record_node_task_result_once(self, result: NodeTaskResultModel) -> bool:
        try:
            with self._session_factory.begin() as session:
                session.add(_node_task_result_to_record(result))
            return True
        except IntegrityError:
            return False

    def record_node_task_result_and_update_node_run_status(
        self,
        result: NodeTaskResultModel,
        status: NodeRunStatus,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        executor_id: str | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[NodeRunStatus | str] | None = None,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> NodeRun | None:
        try:
            with self._session_factory.begin() as session:
                session.add(_node_task_result_to_record(result))
                session.flush()
                source_statuses = (
                    _node_run_status_values(allowed_source_statuses)
                    if allowed_source_statuses is not None
                    else list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))
                )
                values: dict[str, Any] = {
                    "status": status.value,
                    "state_version": NodeRunRecord.state_version + 1,
                    "error_json": _json_dumps(error) if error is not None else None,
                }
                if progress is not None:
                    values["progress"] = progress
                if current_stage is not None:
                    values["current_stage"] = current_stage
                if finished_at is not None:
                    values["finished_at"] = _datetime_to_text(finished_at)
                if executor_id is not None:
                    values["executor_id"] = executor_id

                statement = (
                    update(NodeRunRecord)
                    .where(NodeRunRecord.node_run_id == result.node_run_id)
                    .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
                    .values(**values)
                )
                if expected_state_version is not None:
                    statement = statement.where(
                        NodeRunRecord.state_version == expected_state_version
                    )
                statement = statement.where(NodeRunRecord.status.in_(source_statuses))
                if owner_process_id is not None or process_generation is not None:
                    owner_check = select(WorkflowRunRecord.workflow_run_id).where(
                        WorkflowRunRecord.workflow_run_id
                        == NodeRunRecord.workflow_run_id
                    )
                    if owner_process_id is not None:
                        owner_check = owner_check.where(
                            WorkflowRunRecord.owner_process_id == owner_process_id
                        )
                    if process_generation is not None:
                        owner_check = owner_check.where(
                            WorkflowRunRecord.process_generation == process_generation
                        )
                    statement = statement.where(owner_check.exists())
                update_result = cast(CursorResult[Any], session.execute(statement))
                if update_result.rowcount != 1:
                    raise _AtomicNodeTaskResultUpdateRejected
                record = session.get(NodeRunRecord, result.node_run_id)
                if record is None:
                    raise _AtomicNodeTaskResultUpdateRejected
                return _node_run_from_record(record)
        except (IntegrityError, _AtomicNodeTaskResultUpdateRejected):
            return None

    def get_node_task_result(
        self,
        *,
        task_id: str,
        result_id: str,
    ) -> NodeTaskResultModel | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeTaskResultRecord)
                .where(NodeTaskResultRecord.task_id == task_id)
                .where(NodeTaskResultRecord.result_id == result_id)
            )
            if record is None:
                return None
            return _node_task_result_from_record(record)

    def get_latest_succeeded_node_task_result_for_node_run(
        self,
        node_run_id: str,
    ) -> NodeTaskResultModel | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(NodeTaskResultRecord)
                .where(NodeTaskResultRecord.node_run_id == node_run_id)
                .where(NodeTaskResultRecord.status == NodeResultStatus.SUCCEEDED.value)
                .order_by(
                    NodeTaskResultRecord.finished_at.desc(),
                    NodeTaskResultRecord.result_id.desc(),
                )
            )
            if record is None:
                return None
            return _node_task_result_from_record(record)

    def list_node_runs(self, workflow_run_id: str) -> list[NodeRun]:
        with self._session_factory() as session:
            records = session.scalars(
                select(NodeRunRecord)
                .where(NodeRunRecord.workflow_run_id == workflow_run_id)
                .order_by(NodeRunRecord.node_instance_id)
            ).all()
            return [_node_run_from_record(record) for record in records]

    def update_node_run_status(
        self,
        node_run_id: str,
        status: NodeRunStatus,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: dict[str, Any] | None = None,
        executor_id: str | None = None,
        expected_state_version: int | None = None,
        allowed_source_statuses: Iterable[NodeRunStatus | str] | None = None,
        owner_process_id: str | None = None,
        process_generation: int | None = None,
    ) -> NodeRun | None:
        with self._session_factory.begin() as session:
            source_statuses = (
                _node_run_status_values(allowed_source_statuses)
                if allowed_source_statuses is not None
                else list(_NODE_RUN_STATUS_SOURCES.get(status.value, ()))
            )
            values: dict[str, Any] = {
                "status": status.value,
                "state_version": NodeRunRecord.state_version + 1,
                "error_json": _json_dumps(error) if error is not None else None,
            }
            if progress is not None:
                values["progress"] = progress
            if current_stage is not None:
                values["current_stage"] = current_stage
            if started_at is not None:
                values["started_at"] = _datetime_to_text(started_at)
            if finished_at is not None:
                values["finished_at"] = _datetime_to_text(finished_at)
            if executor_id is not None:
                values["executor_id"] = executor_id

            statement = (
                update(NodeRunRecord)
                .where(NodeRunRecord.node_run_id == node_run_id)
                .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
                .values(**values)
            )
            if expected_state_version is not None:
                statement = statement.where(
                    NodeRunRecord.state_version == expected_state_version
                )
            statement = statement.where(NodeRunRecord.status.in_(source_statuses))
            if owner_process_id is not None or process_generation is not None:
                owner_check = select(WorkflowRunRecord.workflow_run_id).where(
                    WorkflowRunRecord.workflow_run_id == NodeRunRecord.workflow_run_id
                )
                if owner_process_id is not None:
                    owner_check = owner_check.where(
                        WorkflowRunRecord.owner_process_id == owner_process_id
                    )
                if process_generation is not None:
                    owner_check = owner_check.where(
                        WorkflowRunRecord.process_generation == process_generation
                    )
                statement = statement.where(owner_check.exists())
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)
