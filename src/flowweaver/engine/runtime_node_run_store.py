from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.engine.db_models import (
    NodeRunRecord,
)
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_node_run_queries import (
    get_node_run_for_instance_from_session as _get_node_run_for_instance,
)
from flowweaver.engine.runtime_node_run_queries import (
    get_node_run_from_session as _get_node_run,
)
from flowweaver.engine.runtime_node_run_queries import (
    list_node_runs_from_session as _list_node_runs,
)
from flowweaver.engine.runtime_node_run_status_update import (
    apply_node_run_status_update_guards as _apply_node_run_status_update_guards,
)
from flowweaver.engine.runtime_node_run_status_update import (
    node_run_status_source_values as _node_run_status_source_values,
)
from flowweaver.engine.runtime_node_run_status_update import (
    node_run_status_update_values as _node_run_status_update_values,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_run_from_record,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_NODE_STATUSES as _TERMINAL_NODE_STATUSES,
)
from flowweaver.engine.runtime_status_guards import (
    workflow_run_matches_owner as _workflow_run_matches_owner,
)
from flowweaver.protocols.enums import NodeRunStatus


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
            return _get_node_run(session, node_run_id)

    def get_node_run_for_instance(
        self,
        *,
        workflow_run_id: str,
        node_instance_id: str,
    ) -> NodeRun | None:
        with self._session_factory() as session:
            return _get_node_run_for_instance(
                session,
                workflow_run_id=workflow_run_id,
                node_instance_id=node_instance_id,
            )

    def list_node_runs(self, workflow_run_id: str) -> list[NodeRun]:
        with self._session_factory() as session:
            return _list_node_runs(session, workflow_run_id)

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
            source_statuses = _node_run_status_source_values(
                status,
                allowed_source_statuses,
            )
            statement = (
                update(NodeRunRecord)
                .where(NodeRunRecord.node_run_id == node_run_id)
                .where(NodeRunRecord.status.notin_(_TERMINAL_NODE_STATUSES))
                .values(
                    **_node_run_status_update_values(
                        status,
                        progress=progress,
                        current_stage=current_stage,
                        started_at=started_at,
                        finished_at=finished_at,
                        error=error,
                        executor_id=executor_id,
                    )
                )
            )
            statement = _apply_node_run_status_update_guards(
                statement,
                expected_state_version=expected_state_version,
                source_statuses=source_statuses,
                owner_process_id=owner_process_id,
                process_generation=process_generation,
            )
            result = cast(CursorResult[Any], session.execute(statement))
            if result.rowcount != 1:
                return None
            record = session.get(NodeRunRecord, node_run_id)
            if record is None:
                return None
            return _node_run_from_record(record)
