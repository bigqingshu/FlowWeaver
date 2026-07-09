from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.engine import runtime_node_task_result_update as _result_update
from flowweaver.engine import runtime_node_task_runtime_state as _runtime_state
from flowweaver.engine.db_models import (
    NodeTaskRecord,
    NodeTaskResultRecord,
)
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_from_record,
    _node_task_result_from_record,
    _node_task_result_to_record,
    _node_task_to_record,
)
from flowweaver.protocols.enums import NodeResultStatus, NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class RuntimeNodeTaskStoreMixin:
    _session_factory: sessionmaker[Session]

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
        with self._session_factory.begin() as session:
            return _runtime_state.update_node_task_runtime_state_in_session(
                session,
                task,
                executor_id=executor_id,
                heartbeat_at=heartbeat_at,
                progress=progress,
                current_stage=current_stage,
            )

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
                record_result = (
                    _result_update
                    .record_node_task_result_and_update_node_run_status_in_session
                )
                return record_result(
                    session,
                    result,
                    status,
                    progress=progress,
                    current_stage=current_stage,
                    finished_at=finished_at,
                    error=error,
                    executor_id=executor_id,
                    expected_state_version=expected_state_version,
                    allowed_source_statuses=allowed_source_statuses,
                    owner_process_id=owner_process_id,
                    process_generation=process_generation,
                )
        except (IntegrityError, _result_update.NodeTaskResultUpdateRejected):
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
