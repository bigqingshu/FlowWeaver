from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    workflow_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflows.workflow_id"),
        nullable=False,
        index=True,
    )
    revision_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("workflow_revisions.revision_id"),
        index=True,
    )
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_process_id: Mapped[str | None] = mapped_column(Text, index=True)
    process_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fencing_token: Mapped[str | None] = mapped_column(Text)
    input_snapshot_id: Mapped[str | None] = mapped_column(Text)
    run_mode: Mapped[str] = mapped_column(Text, nullable=False, default="full")
    trigger_source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="manual",
        index=True,
    )
    target_node_instance_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    completion_reason: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[str | None] = mapped_column(Text)


class WorkflowProcessRecord(Base):
    __tablename__ = "workflow_processes"

    process_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    os_pid: Mapped[int | None] = mapped_column(Integer)
    process_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fencing_token: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_heartbeat_at: Mapped[str | None] = mapped_column(Text)
    cancel_requested_at: Mapped[str | None] = mapped_column(Text)
    exited_at: Mapped[str | None] = mapped_column(Text)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    error_json: Mapped[str | None] = mapped_column(Text)
