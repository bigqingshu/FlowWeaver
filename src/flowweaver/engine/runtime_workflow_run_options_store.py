from __future__ import annotations

import json
from collections.abc import Mapping

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    NodeRunRecord,
    NodeTaskRecord,
    WorkflowProcessRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
    WorkflowRunRuntimeOptionsRecord,
)
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_models import (
    ActiveNodeTaskRuntimeOptionsVersion,
    WorkflowRunRuntimeOptions,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_to_text,
    _optional_datetime_from_text,
)
from flowweaver.protocols.enums import (
    NodeRunStatus,
    WorkflowProcessStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackPolicyOverlayModel

_EDITABLE_RUN_STATUSES = frozenset(
    {
        WorkflowRunStatus.PENDING.value,
        WorkflowRunStatus.RUNNING.value,
    }
)
_ACTIVE_NODE_RUN_STATUSES = frozenset(
    {
        NodeRunStatus.QUEUED.value,
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
        NodeRunStatus.SUSPECTED_HUNG.value,
    }
)


class WorkflowRunRuntimeOptionsNotFoundError(ValueError):
    pass


class WorkflowRunRuntimeOptionsInactiveError(ValueError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Workflow run runtime options are read-only: {status}")


class WorkflowRunRuntimeOptionsVersionConflictError(ValueError):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(
            f"Workflow run runtime options version conflict: {current_version}"
        )


class WorkflowRunRuntimeOptionsInvalidNodesError(ValueError):
    def __init__(self, node_instance_ids: list[str]) -> None:
        self.node_instance_ids = tuple(sorted(node_instance_ids))
        super().__init__(
            "Workflow run runtime options contain unknown node instance IDs: "
            + ", ".join(self.node_instance_ids)
        )


class RuntimeWorkflowRunOptionsStoreMixin:
    database_url: str
    engine: Engine
    _session_factory: sessionmaker[Session]

    def get_workflow_run_runtime_options(
        self,
        workflow_run_id: str,
    ) -> WorkflowRunRuntimeOptions | None:
        with self._session_factory() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                return None
            record = session.get(WorkflowRunRuntimeOptionsRecord, workflow_run_id)
            return (
                _workflow_run_runtime_options_from_record(record)
                if record is not None
                else _default_workflow_run_runtime_options(workflow_run_id)
            )

    def replace_workflow_run_runtime_options(
        self,
        workflow_run_id: str,
        *,
        expected_version: int,
        overlay: RuntimeFeedbackPolicyOverlayModel,
    ) -> WorkflowRunRuntimeOptions:
        if expected_version < 0:
            raise ValueError("expected_version must be non-negative")
        now = utc_now()
        with immediate_session(
            self.engine,
            database_url=self.database_url,
        ) as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise WorkflowRunRuntimeOptionsNotFoundError(workflow_run_id)
            _validate_runtime_options_run_is_editable(session, run)
            record = session.get(WorkflowRunRuntimeOptionsRecord, workflow_run_id)
            current_version = record.requested_version if record is not None else 0
            if current_version != expected_version:
                raise WorkflowRunRuntimeOptionsVersionConflictError(current_version)
            _validate_runtime_options_overlay_nodes(session, run, overlay)
            if record is None:
                record = WorkflowRunRuntimeOptionsRecord(
                    workflow_run_id=workflow_run_id,
                    requested_version=1,
                    applied_version=0,
                    overlay_json=_runtime_options_overlay_json(overlay),
                    requested_at=_datetime_to_text(now),
                    applied_at=None,
                )
                session.add(record)
            else:
                record.requested_version += 1
                record.overlay_json = _runtime_options_overlay_json(overlay)
                record.requested_at = _datetime_to_text(now)
            session.flush()
            return _workflow_run_runtime_options_from_record(record)

    def mark_workflow_run_runtime_options_applied(
        self,
        workflow_run_id: str,
        *,
        version: int,
    ) -> WorkflowRunRuntimeOptions | None:
        if version < 0:
            raise ValueError("version must be non-negative")
        with immediate_session(
            self.engine,
            database_url=self.database_url,
        ) as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                return None
            record = session.get(WorkflowRunRuntimeOptionsRecord, workflow_run_id)
            if record is None:
                if version != 0:
                    raise ValueError("Applied version exceeds requested version 0")
                return _default_workflow_run_runtime_options(workflow_run_id)
            if version > record.requested_version:
                raise ValueError(
                    "Applied version exceeds requested version "
                    f"{record.requested_version}"
                )
            if version <= record.applied_version:
                return _workflow_run_runtime_options_from_record(record)
            record.applied_version = version
            record.applied_at = _datetime_to_text(utc_now())
            session.flush()
            return _workflow_run_runtime_options_from_record(record)

    def list_active_node_task_runtime_options_versions(
        self,
        workflow_run_id: str,
    ) -> list[ActiveNodeTaskRuntimeOptionsVersion]:
        with self._session_factory() as session:
            rows = session.execute(
                select(NodeTaskRecord, NodeRunRecord.status)
                .join(
                    NodeRunRecord,
                    and_(
                        NodeRunRecord.node_run_id == NodeTaskRecord.node_run_id,
                        NodeRunRecord.attempt == NodeTaskRecord.attempt,
                    ),
                )
                .where(
                    NodeTaskRecord.workflow_run_id == workflow_run_id,
                    NodeRunRecord.status.in_(_ACTIVE_NODE_RUN_STATUSES),
                )
                .order_by(NodeTaskRecord.created_at, NodeTaskRecord.task_id)
            ).all()
            return [
                ActiveNodeTaskRuntimeOptionsVersion(
                    task_id=task.task_id,
                    node_run_id=task.node_run_id,
                    node_instance_id=task.node_instance_id,
                    node_run_status=node_run_status,
                    runtime_options_version=task.runtime_options_version,
                )
                for task, node_run_status in rows
            ]


def _validate_runtime_options_run_is_editable(
    session: Session,
    run: WorkflowRunRecord,
) -> None:
    if run.status not in _EDITABLE_RUN_STATUSES:
        raise WorkflowRunRuntimeOptionsInactiveError(run.status)
    process_status = session.scalar(
        select(WorkflowProcessRecord.status)
        .where(WorkflowProcessRecord.workflow_run_id == run.workflow_run_id)
        .order_by(
            WorkflowProcessRecord.process_generation.desc(),
            WorkflowProcessRecord.started_at.desc(),
        )
        .limit(1)
    )
    if process_status == WorkflowProcessStatus.CANCEL_REQUESTED.value:
        raise WorkflowRunRuntimeOptionsInactiveError(process_status)


def _validate_runtime_options_overlay_nodes(
    session: Session,
    run: WorkflowRunRecord,
    overlay: RuntimeFeedbackPolicyOverlayModel,
) -> None:
    if not overlay.node_overrides:
        return
    revision = session.get(WorkflowRevisionRecord, run.revision_id)
    if revision is None:
        raise WorkflowRunRuntimeOptionsNotFoundError(run.workflow_run_id)
    definition = json.loads(revision.definition_json)
    nodes = definition.get("nodes", []) if isinstance(definition, Mapping) else []
    known_node_ids = {
        node_instance_id
        for node in nodes
        if isinstance(node, Mapping)
        and isinstance(
            node_instance_id := node.get("node_instance_id"),
            str,
        )
    }
    invalid_node_ids = set(overlay.node_overrides).difference(known_node_ids)
    if invalid_node_ids:
        raise WorkflowRunRuntimeOptionsInvalidNodesError(list(invalid_node_ids))


def _workflow_run_runtime_options_from_record(
    record: WorkflowRunRuntimeOptionsRecord,
) -> WorkflowRunRuntimeOptions:
    return WorkflowRunRuntimeOptions(
        workflow_run_id=record.workflow_run_id,
        requested_version=record.requested_version,
        applied_version=record.applied_version,
        overlay=RuntimeFeedbackPolicyOverlayModel.model_validate_json(
            record.overlay_json
        ),
        requested_at=_optional_datetime_from_text(record.requested_at),
        applied_at=_optional_datetime_from_text(record.applied_at),
    )


def _default_workflow_run_runtime_options(
    workflow_run_id: str,
) -> WorkflowRunRuntimeOptions:
    return WorkflowRunRuntimeOptions(
        workflow_run_id=workflow_run_id,
        requested_version=0,
        applied_version=0,
        overlay=RuntimeFeedbackPolicyOverlayModel(),
        requested_at=None,
        applied_at=None,
    )


def _runtime_options_overlay_json(
    overlay: RuntimeFeedbackPolicyOverlayModel,
) -> str:
    return overlay.model_dump_json(
        exclude_none=True,
        exclude_defaults=True,
    )
