from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flowweaver.protocols.runtime_feedback import RuntimeFeedbackPolicyOverlayModel
from flowweaver.protocols.table_ref import TableRefModel


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    revision_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkflowRevision:
    revision_id: str
    workflow_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    created_at: datetime
    created_by: str | None


@dataclass(frozen=True)
class WorkflowRevisionConflict:
    workflow_id: str
    expected_revision_id: str
    current_revision_id: str | None


@dataclass(frozen=True)
class WorkflowRun:
    workflow_run_id: str
    workflow_id: str
    revision_id: str | None
    workflow_version: int
    definition_hash: str | None
    status: str
    state_version: int
    owner_process_id: str | None
    process_generation: int
    fencing_token: str | None
    input_snapshot_id: str | None
    run_mode: str
    trigger_source: str
    target_node_instance_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    completion_reason: str | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class WorkflowRunRuntimeOptions:
    workflow_run_id: str
    requested_version: int
    applied_version: int
    overlay: RuntimeFeedbackPolicyOverlayModel
    requested_at: datetime | None
    applied_at: datetime | None


@dataclass(frozen=True)
class ActiveNodeTaskRuntimeOptionsVersion:
    task_id: str
    node_run_id: str
    node_instance_id: str
    node_run_status: str
    runtime_options_version: int


@dataclass(frozen=True)
class WorkflowProcess:
    process_id: str
    workflow_run_id: str
    os_pid: int | None
    process_generation: int
    fencing_token: str | None
    status: str
    started_at: datetime
    last_heartbeat_at: datetime | None
    cancel_requested_at: datetime | None
    exited_at: datetime | None
    exit_code: int | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class NodeRun:
    node_run_id: str
    workflow_run_id: str
    node_instance_id: str
    node_type: str
    status: str
    state_version: int
    executor_id: str | None
    progress: float | None
    current_stage: str | None
    attempt: int
    started_at: datetime | None
    finished_at: datetime | None
    last_heartbeat: datetime | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class LoopRun:
    loop_run_id: str
    workflow_run_id: str
    loop_id: str
    start_node_instance_id: str
    judge_node_instance_id: str
    status: str
    state_version: int
    current_iteration: int
    max_iterations: int
    exit_reason: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True)
class LoopIterationRun:
    loop_iteration_id: str
    loop_run_id: str
    iteration_index: int
    status: str
    state_version: int
    input_table_ref_id: str | None
    input_selector: dict[str, Any] | None
    output_table_ref_id: str | None
    failed_node_run_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True)
class LoopIterationTableRef:
    loop_iteration_id: str
    table_ref_id: str
    role: str
    created_at: datetime


@dataclass(frozen=True)
class LoopIterationNodeRun:
    loop_iteration_id: str
    node_run_id: str
    node_instance_id: str
    role: str
    created_at: datetime


@dataclass(frozen=True)
class RunTableDirectoryEntry:
    table_ref: TableRefModel
    source_node_instance_id: str | None


@dataclass(frozen=True)
class RuntimeEventLog:
    event_id: str
    sequence_number: int
    event_version: str
    event_type: str
    timestamp: datetime
    workflow_run_id: str | None
    node_run_id: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class SharedPublicationMember:
    publication_id: str
    export_name: str
    table_ref_id: str
    exact_table_version: int


@dataclass(frozen=True)
class SharedPublicationMemberSummary:
    publication_id: str
    export_name: str
    table_ref_id: str
    exact_table_version: int
    table_ref_lifecycle_status: str
    table_ref_storage_kind: str
    logical_table_id: str
    can_read_rows: bool


@dataclass(frozen=True)
class SharedPublication:
    publication_id: str
    share_name: str
    publication_version: int
    producer_workflow_id: str
    producer_run_id: str
    status: str
    input_snapshot_id: str | None
    retention_policy: dict[str, Any]
    created_at: datetime
    members: tuple[SharedPublicationMember, ...]


@dataclass(frozen=True)
class SharedPublicationCatalogEntry:
    share_name: str
    latest_published_version: int
    published_version_count: int
    latest_member_count: int
    latest_created_at: datetime


@dataclass(frozen=True)
class SharedPublicationSummary:
    publication_id: str
    share_name: str
    publication_version: int
    producer_workflow_id: str
    producer_run_id: str
    status: str
    input_snapshot_id: str | None
    retention_policy: dict[str, Any]
    created_at: datetime
    member_count: int
    is_latest_published: bool


@dataclass(frozen=True)
class InputSnapshotEntry:
    source_name: str
    publication_id: str
    publication_version: int
    selected_members: tuple[str, ...]


@dataclass(frozen=True)
class InputSnapshot:
    input_snapshot_id: str
    workflow_run_id: str
    inputs: tuple[InputSnapshotEntry, ...]
    created_at: datetime


@dataclass(frozen=True)
class ReadLease:
    lease_id: str
    publication_id: str
    publication_version: int
    selected_members: tuple[str, ...]
    consumer_workflow_run_id: str
    acquired_at: datetime
    expires_at: datetime
    released_at: datetime | None
