from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class NodeRunRecord(Base):
    __tablename__ = "node_runs"
    __table_args__ = (
        Index(
            "idx_node_runs_run_status_directory",
            "workflow_run_id",
            "status",
            "node_instance_id",
            "node_run_id",
        ),
    )

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
    runtime_feedback_policy_json: Mapped[str | None] = mapped_column(Text)
    runtime_options_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
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
