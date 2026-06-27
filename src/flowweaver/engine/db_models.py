from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WorkflowDefinitionRecord(Base):
    __tablename__ = "workflow_definitions"

    workflow_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class WorkflowRecord(Base):
    __tablename__ = "workflows"

    workflow_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class WorkflowRevisionRecord(Base):
    __tablename__ = "workflow_revisions"
    __table_args__ = (UniqueConstraint("workflow_id", "version"),)

    revision_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflows.workflow_id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    definition_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    workflow_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_definitions.workflow_id"),
        nullable=False,
        index=True,
    )
    revision_id: Mapped[str | None] = mapped_column(Text, index=True)
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_snapshot_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[str | None] = mapped_column(Text)


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


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(Text)
    node_run_id: Mapped[str | None] = mapped_column(Text)
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(Text)
    resource_id: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class RuntimeEventRecord(Base):
    __tablename__ = "runtime_events"

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    event_version: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(Text, index=True)
    node_run_id: Mapped[str | None] = mapped_column(Text, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
