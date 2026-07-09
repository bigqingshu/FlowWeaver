from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import (
    NodeRun,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)


def workflow_definition_to_jsonable(value: WorkflowDefinition) -> dict[str, Any]:
    return {
        "workflow_id": value.workflow_id,
        "name": value.name,
        "revision_id": value.revision_id,
        "version": value.version,
        "definition_hash": value.definition_hash,
        "definition": value.definition,
        "status": value.status,
        "created_at": value.created_at.isoformat(),
        "updated_at": value.updated_at.isoformat(),
    }


def workflow_revision_to_jsonable(value: WorkflowRevision) -> dict[str, Any]:
    return {
        "revision_id": value.revision_id,
        "workflow_id": value.workflow_id,
        "version": value.version,
        "definition_hash": value.definition_hash,
        "definition": value.definition,
        "created_at": value.created_at.isoformat(),
        "created_by": value.created_by,
    }


def workflow_run_to_jsonable(value: WorkflowRun) -> dict[str, Any]:
    return {
        "workflow_run_id": value.workflow_run_id,
        "workflow_id": value.workflow_id,
        "revision_id": value.revision_id,
        "workflow_version": value.workflow_version,
        "definition_hash": value.definition_hash,
        "status": value.status,
        "state_version": value.state_version,
        "owner_process_id": value.owner_process_id,
        "process_generation": value.process_generation,
        "fencing_token": value.fencing_token,
        "input_snapshot_id": value.input_snapshot_id,
        "run_mode": value.run_mode,
        "trigger_source": value.trigger_source,
        "target_node_instance_id": value.target_node_instance_id,
        "started_at": value.started_at.isoformat() if value.started_at else None,
        "finished_at": value.finished_at.isoformat() if value.finished_at else None,
        "completion_reason": value.completion_reason,
        "error": value.error,
    }


def workflow_process_to_jsonable(value: WorkflowProcess) -> dict[str, Any]:
    return {
        "process_id": value.process_id,
        "workflow_run_id": value.workflow_run_id,
        "os_pid": value.os_pid,
        "process_generation": value.process_generation,
        "fencing_token": value.fencing_token,
        "status": value.status,
        "started_at": value.started_at.isoformat(),
        "last_heartbeat_at": (
            value.last_heartbeat_at.isoformat() if value.last_heartbeat_at else None
        ),
        "cancel_requested_at": (
            value.cancel_requested_at.isoformat()
            if value.cancel_requested_at
            else None
        ),
        "exited_at": value.exited_at.isoformat() if value.exited_at else None,
        "exit_code": value.exit_code,
        "error": value.error,
    }


def node_run_to_jsonable(value: NodeRun) -> dict[str, Any]:
    return {
        "node_run_id": value.node_run_id,
        "workflow_run_id": value.workflow_run_id,
        "node_instance_id": value.node_instance_id,
        "node_type": value.node_type,
        "status": value.status,
        "state_version": value.state_version,
        "executor_id": value.executor_id,
        "progress": value.progress,
        "current_stage": value.current_stage,
        "attempt": value.attempt,
        "started_at": value.started_at.isoformat() if value.started_at else None,
        "finished_at": value.finished_at.isoformat() if value.finished_at else None,
        "last_heartbeat": (
            value.last_heartbeat.isoformat() if value.last_heartbeat else None
        ),
        "error": value.error,
    }
