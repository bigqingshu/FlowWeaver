from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base as Base
from flowweaver.engine.db_loop_models import (
    LoopIterationNodeRunRecord as LoopIterationNodeRunRecord,
)
from flowweaver.engine.db_loop_models import (
    LoopIterationRunRecord as LoopIterationRunRecord,
)
from flowweaver.engine.db_loop_models import (
    LoopIterationTableRefRecord as LoopIterationTableRefRecord,
)
from flowweaver.engine.db_loop_models import LoopRunRecord as LoopRunRecord
from flowweaver.engine.db_node_task_models import NodeRunRecord as NodeRunRecord
from flowweaver.engine.db_node_task_models import NodeTaskRecord as NodeTaskRecord
from flowweaver.engine.db_node_task_models import (
    NodeTaskResultRecord as NodeTaskResultRecord,
)
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


