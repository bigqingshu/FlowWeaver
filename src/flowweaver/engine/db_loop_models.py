from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


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
