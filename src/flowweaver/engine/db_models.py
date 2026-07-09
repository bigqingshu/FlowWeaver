from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base as Base
from flowweaver.engine.db_runtime_event_models import (
    RuntimeEventRecord as RuntimeEventRecord,
)
from flowweaver.engine.db_workflow_definition_models import (
    WorkflowDefinitionRecord as WorkflowDefinitionRecord,
)
from flowweaver.engine.db_workflow_definition_models import (
    WorkflowRecord as WorkflowRecord,
)
from flowweaver.engine.db_workflow_definition_models import (
    WorkflowRevisionRecord as WorkflowRevisionRecord,
)
from flowweaver.engine.db_workflow_runtime_models import (
    WorkflowProcessRecord as WorkflowProcessRecord,
)
from flowweaver.engine.db_workflow_runtime_models import (
    WorkflowRunRecord as WorkflowRunRecord,
)


class NodeRunRecord(Base):
    __tablename__ = "node_runs"

    node_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
    )
    node_instance_id: Mapped[str] = mapped_column(Text, nullable=False)
    node_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executor_id: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[float | None] = mapped_column(Float)
    current_stage: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    last_heartbeat: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[str | None] = mapped_column(Text)


class NodeTaskRecord(Base):
    __tablename__ = "node_tasks"

    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    workflow_process_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_processes.process_id"),
        nullable=False,
        index=True,
    )
    process_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    node_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("node_runs.node_run_id"),
        nullable=False,
        index=True,
    )
    node_instance_id: Mapped[str] = mapped_column(Text, nullable=False)
    node_type: Mapped[str] = mapped_column(Text, nullable=False)
    node_version: Mapped[str] = mapped_column(Text, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    input_refs_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_slot_bindings_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class NodeTaskResultRecord(Base):
    __tablename__ = "node_task_results"
    __table_args__ = (UniqueConstraint("task_id", "result_id"),)

    result_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("node_tasks.task_id"),
        nullable=False,
        index=True,
    )
    node_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("node_runs.node_run_id"),
        nullable=False,
        index=True,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    executor_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    process_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    output_refs_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_slot_bindings_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_json: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at: Mapped[str] = mapped_column(Text, nullable=False)


class LoopRunRecord(Base):
    __tablename__ = "loop_runs"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "loop_id"),
        Index("ix_loop_runs_workflow_status", "workflow_run_id", "status"),
    )

    loop_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    loop_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    start_node_instance_id: Mapped[str] = mapped_column(Text, nullable=False)
    judge_node_instance_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_reason: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LoopIterationRunRecord(Base):
    __tablename__ = "loop_iteration_runs"
    __table_args__ = (
        UniqueConstraint("loop_run_id", "iteration_index"),
        Index("ix_loop_iteration_runs_loop_status", "loop_run_id", "status"),
    )

    loop_iteration_id: Mapped[str] = mapped_column(Text, primary_key=True)
    loop_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("loop_runs.loop_run_id"),
        nullable=False,
        index=True,
    )
    iteration_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_table_ref_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        index=True,
    )
    input_selector_json: Mapped[str | None] = mapped_column(Text)
    output_table_ref_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        index=True,
    )
    failed_node_run_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("node_runs.node_run_id"),
        index=True,
    )
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LoopIterationTableRefRecord(Base):
    __tablename__ = "loop_iteration_table_refs"
    __table_args__ = (
        Index(
            "ix_loop_iteration_table_refs_iteration_role",
            "loop_iteration_id",
            "role",
        ),
        Index("ix_loop_iteration_table_refs_table_ref_id", "table_ref_id"),
    )

    loop_iteration_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("loop_iteration_runs.loop_iteration_id"),
        primary_key=True,
    )
    table_ref_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LoopIterationNodeRunRecord(Base):
    __tablename__ = "loop_iteration_node_runs"
    __table_args__ = (
        Index(
            "ix_loop_iteration_node_runs_iteration_instance",
            "loop_iteration_id",
            "node_instance_id",
        ),
        Index("ix_loop_iteration_node_runs_node_run_id", "node_run_id"),
    )

    loop_iteration_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("loop_iteration_runs.loop_iteration_id"),
        primary_key=True,
    )
    node_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("node_runs.node_run_id"),
        primary_key=True,
    )
    node_instance_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class DataRefRecord(Base):
    __tablename__ = "data_refs"

    table_ref_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    node_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    storage_kind: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    mutability: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)
    resource_profile_id: Mapped[str | None] = mapped_column(Text)
    mount_id: Mapped[str | None] = mapped_column(Text)
    logical_table_id: Mapped[str] = mapped_column(Text, nullable=False)
    opaque_handle_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    capabilities_json: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[str | None] = mapped_column(Text)


class SharedPublicationRecord(Base):
    __tablename__ = "shared_publications"
    __table_args__ = (UniqueConstraint("share_name", "publication_version"),)

    publication_id: Mapped[str] = mapped_column(Text, primary_key=True)
    share_name: Mapped[str] = mapped_column(Text, nullable=False)
    publication_version: Mapped[int] = mapped_column(Integer, nullable=False)
    producer_workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    producer_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot_id: Mapped[str | None] = mapped_column(Text)
    retention_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class SharedPublicationMemberRecord(Base):
    __tablename__ = "shared_publication_members"

    publication_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("shared_publications.publication_id"),
        primary_key=True,
    )
    export_name: Mapped[str] = mapped_column(Text, primary_key=True)
    table_ref_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        nullable=False,
    )
    exact_table_version: Mapped[int] = mapped_column(Integer, nullable=False)


class InputSnapshotRecord(Base):
    __tablename__ = "input_snapshots"

    input_snapshot_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ReadLeaseRecord(Base):
    __tablename__ = "read_leases"

    lease_id: Mapped[str] = mapped_column(Text, primary_key=True)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False)
    publication_version: Mapped[int] = mapped_column(Integer, nullable=False)
    consumer_workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    selected_members_json: Mapped[str] = mapped_column(Text, nullable=False)
    acquired_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    released_at: Mapped[str | None] = mapped_column(Text)


class TableLeaseRecord(Base):
    __tablename__ = "table_leases"

    lease_id: Mapped[str] = mapped_column(Text, primary_key=True)
    table_ref_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        nullable=False,
        index=True,
    )
    lease_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    acquired_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_heartbeat_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    released_at: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)


