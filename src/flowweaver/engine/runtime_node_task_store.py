from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.engine import runtime_node_task_queries as _task_queries
from flowweaver.engine import runtime_node_task_result_update as _result_update
from flowweaver.engine import runtime_node_task_runtime_state as _runtime_state
from flowweaver.engine.db_models import NodeRunRecord, NodeTaskRecord
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_result_to_record,
    _node_task_to_record,
)
from flowweaver.engine.runtime_record_codecs import _json_dumps
from flowweaver.engine.runtime_status_guards import TERMINAL_NODE_STATUSES
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


class RuntimeNodeTaskStoreMixin:
    database_url: str
    engine: Engine
    _session_factory: sessionmaker[Session]

    def create_node_task(self, task: NodeTaskModel) -> NodeTaskModel:
        with self._session_factory.begin() as session:
            session.add(_node_task_to_record(task))
        return task

    def get_node_task(self, task_id: str) -> NodeTaskModel | None:
        with self._session_factory() as session:
            return _task_queries.get_node_task_from_session(session, task_id)

    def update_node_task_runtime_feedback_policy(
        self,
        task_id: str,
        *,
        runtime_options_version: int,
        runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel,
    ) -> bool:
        if runtime_options_version < 0:
            raise ValueError("runtime_options_version must be non-negative")
        with immediate_session(
            self.engine,
            database_url=self.database_url,
        ) as session:
            task = session.get(NodeTaskRecord, task_id)
            if task is None:
                return False
            if task.runtime_options_version == runtime_options_version:
                return True
            if task.runtime_options_version > runtime_options_version:
                return False
            node_run = session.get(NodeRunRecord, task.node_run_id)
            if (
                node_run is None
                or node_run.attempt != task.attempt
                or node_run.status in TERMINAL_NODE_STATUSES
            ):
                return False
            task.runtime_feedback_policy_json = _json_dumps(
                runtime_feedback_policy.model_dump(mode="json")
            )
            task.runtime_options_version = runtime_options_version
            session.flush()
            return True

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
            return _task_queries.get_node_task_result_from_session(
                session,
                task_id=task_id,
                result_id=result_id,
            )

    def get_latest_succeeded_node_task_result_for_node_run(
        self,
        node_run_id: str,
    ) -> NodeTaskResultModel | None:
        with self._session_factory() as session:
            return (
                _task_queries
                .get_latest_succeeded_node_task_result_for_node_run_from_session(
                    session,
                    node_run_id,
                )
            )
